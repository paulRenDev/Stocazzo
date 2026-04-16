"""
scoring.py — CronyPony v7
Manages predictions, backcheck and hit rate tracking.
Imports: config, helpers, state.
"""
import requests
from datetime import datetime, timezone

from config import (
    FINNHUB_KEY, TWELVEDATA_KEY,
    BACKCHECK_DAYS_DEFAULT, BACKCHECK_DAYS_FAST,
    HIT_THRESHOLD_PCT, SOURCE_CREDIBILITY, DEFAULT_STATS,
)
from helpers import now_utc, now_utc_iso


# ── PRICE FETCH ───────────────────────────────────────────────────────────────
def get_price(ticker):
    """
    Fetch current price. Tries Twelve Data first, then Finnhub.
    Returns float or 0.
    """
    if TWELVEDATA_KEY:
        try:
            r = requests.get(
                "https://api.twelvedata.com/price",
                params={"symbol": ticker, "apikey": TWELVEDATA_KEY},
                timeout=6,
            )
            if r.status_code == 200:
                price = float(r.json().get("price", 0))
                if price:
                    return price
        except Exception as e:
            print(f"Twelve Data price {ticker}: {e}")

    if FINNHUB_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}",
                timeout=6,
            )
            if r.status_code == 200:
                price = float(r.json().get("c", 0))
                if price:
                    return price
        except Exception as e:
            print(f"Finnhub price {ticker}: {e}")

    return 0


# ── HIT RATE ──────────────────────────────────────────────────────────────────
def get_source_hit_rate(source, seen_data):
    """
    Returns (hit_rate, n_verified) for a source.
    Falls back to historical baseline if no own data exists.
    """
    stats = seen_data.get("stats", DEFAULT_STATS).get(
        source, {"hits": 0, "misses": 0, "pending": 0}
    )
    total = stats["hits"] + stats["misses"]
    if total == 0:
        baseline = SOURCE_CREDIBILITY.get(source, {}).get("historical_hit_rate", 0.5)
        return (baseline or 0.5), 0
    return round(stats["hits"] / total, 2), total


def format_hit_rate(source, seen_data):
    """Returns readable hit rate string for email/HTML."""
    rate, n = get_source_hit_rate(source, seen_data)
    if n > 0:
        return f"{rate:.0%} ({n} verified signals)"
    return f"{rate:.0%} (historical baseline)"


# ── BACKCHECK QUEUE ───────────────────────────────────────────────────────────
def queue_for_backcheck(alert, seen_data):
    """
    Add a signal to the backcheck queue.
    Stores entry price as baseline for later verification.
    """
    etfs = alert.get("etfs", [])
    if not etfs:
        return

    ticker = etfs[0][0]
    price  = get_price(ticker)

    seen_data.setdefault("pending_checks", []).append({
        "uid":             alert.get("uid", ""),
        "source":          alert.get("source", ""),
        "ticker":          ticker,
        "direction":       alert.get("direction", ""),
        "date":            now_utc_iso(),
        "price_at_signal": price,
        "title":           alert.get("title", "")[:80],
    })

    if price:
        print(f"  Backcheck queued: {ticker} @ ${price:.2f} ({alert.get('source')})")
    else:
        print(f"  Backcheck queued: {ticker} (price unavailable)")


# ── RUN BACKCHECK ─────────────────────────────────────────────────────────────
def run_backcheck(seen_data):
    """
    Checks pending signals after BACKCHECK_DAYS_DEFAULT days.
    Polymarket/Kalshi are checked faster (BACKCHECK_DAYS_FAST).
    Updates hit/miss stats per source.
    Returns (updated seen_data, list of results).
    """
    pending = seen_data.get("pending_checks", [])
    if not pending:
        return seen_data, []

    now           = datetime.now(timezone.utc)
    still_pending = []
    results       = []

    for check in pending:
        try:
            signal_date = datetime.fromisoformat(check.get("date", now.isoformat()))
        except Exception:
            still_pending.append(check)
            continue

        days_ago = (now - signal_date).days
        source   = check.get("source", "")
        min_days = BACKCHECK_DAYS_FAST if source in ("Polymarket", "Kalshi") else BACKCHECK_DAYS_DEFAULT

        if days_ago < min_days:
            still_pending.append(check)
            continue

        ticker          = check.get("ticker", "")
        direction       = check.get("direction", "").upper()
        price_at_signal = check.get("price_at_signal", 0)

        if not ticker or not price_at_signal:
            still_pending.append(check)
            continue

        current_price = get_price(ticker)
        if not current_price:
            still_pending.append(check)
            continue

        pct_change = ((current_price - price_at_signal) / price_at_signal) * 100

        is_buy  = any(w in direction for w in ["BUY", "YES", "ACCUM", "BULLISH"])
        is_sell = any(w in direction for w in ["SELL", "NO", "REDUCE", "HEDGE", "BEARISH"])

        if is_buy:
            hit = pct_change > HIT_THRESHOLD_PCT
        elif is_sell:
            hit = pct_change < -HIT_THRESHOLD_PCT
        else:
            hit = None

        stats = seen_data.setdefault("stats", DEFAULT_STATS)
        if source not in stats:
            stats[source] = {"hits": 0, "misses": 0, "pending": 0}

        if hit is True:
            stats[source]["hits"] += 1
            result_str = f"HIT: {ticker} {direction} → {pct_change:+.1f}% in {days_ago}d"
        elif hit is False:
            stats[source]["misses"] += 1
            result_str = f"MISS: {ticker} {direction} → {pct_change:+.1f}% in {days_ago}d"
        else:
            result_str = f"WATCH: {ticker} → {pct_change:+.1f}% in {days_ago}d"

        print(f"Backcheck [{source}]: {result_str}")

        results.append({
            "source":      source,
            "ticker":      ticker,
            "direction":   direction,
            "pct_change":  round(pct_change, 1),
            "days":        days_ago,
            "hit":         hit,
            "result":      result_str,
            "price_entry": price_at_signal,
            "price_now":   current_price,
            "title":       check.get("title", ""),
            "uid":         check.get("uid", ""),
        })

    seen_data["pending_checks"] = still_pending
    return seen_data, results


# ── UPDATE HISTORY WITH BACKCHECK ─────────────────────────────────────────────
def update_history_backcheck(backcheck_results, seen_data):
    """Links backcheck results back to history entries via uid."""
    history = seen_data.get("history", [])
    uid_map = {h.get("uid"): h for h in history}

    for bc in backcheck_results:
        uid = bc.get("uid", "")
        if uid and uid in uid_map:
            entry = uid_map[uid]
            entry["verified"]      = bc.get("hit")
            entry["pct_change"]    = bc.get("pct_change")
            entry["verified_date"] = now_utc()
            entry["price_entry"]   = bc.get("price_entry")
            entry["price_now"]     = bc.get("price_now")
