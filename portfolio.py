"""
portfolio.py — Stocazzo v7
Virtual portfolio: every advice card opens a €1000 position.
Tracks P&L at 4h, 24h and 5d. Builds adaptive confidence score over time.
"""
import requests
from datetime import datetime, timezone, timedelta

from config import TWELVEDATA_KEY, FINNHUB_KEY
from helpers import now_utc, now_utc_iso, now_be

VIRTUAL_STAKE    = 1000.0   # euros per advice
HIT_THRESHOLD    = 2.0      # % needed to count as hit
ROLLING_WINDOW   = 20       # last N positions for platform score
CHECK_WINDOWS    = [4, 24, 120]  # hours: 4h, 24h, 5d


# ── PRICE FETCH ───────────────────────────────────────────────────────────────
def get_price(ticker):
    """Fetch current price via Twelve Data, fallback to Finnhub."""
    if TWELVEDATA_KEY:
        try:
            r = requests.get(
                "https://api.twelvedata.com/price",
                params={"symbol": ticker, "apikey": TWELVEDATA_KEY},
                timeout=6,
            )
            if r.status_code == 200:
                price = float(r.json().get("price", 0) or 0)
                if price:
                    return price
        except Exception:
            pass

    if FINNHUB_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}",
                timeout=5,
            )
            if r.status_code == 200:
                price = float(r.json().get("c", 0) or 0)
                if price:
                    return price
        except Exception:
            pass

    return 0.0


# ── OPEN POSITION ─────────────────────────────────────────────────────────────
def open_position(advice_card, seen_data):
    """
    Opens a virtual €1000 position for an advice card.
    Skips if already open for this uid.
    """
    positions = seen_data.setdefault("portfolio", [])
    existing  = {p["uid"] for p in positions}

    uid = advice_card.get("uid", "")
    if uid in existing:
        return

    # Only open for BUY or SELL/REDUCE — not WATCH
    direction = advice_card.get("direction", "WATCH")
    if "WATCH" in direction.upper():
        return

    etfs = advice_card.get("etfs", [])
    if not etfs:
        return

    ticker      = etfs[0][0]
    entry_price = get_price(ticker)
    if not entry_price:
        print(f"  Portfolio: could not get price for {ticker}, skipping")
        return

    is_buy  = "BUY" in direction.upper()
    side    = "BUY" if is_buy else "SELL"

    position = {
        "uid":          uid,
        "theme":        advice_card.get("theme", ""),
        "action":       advice_card.get("action", ""),
        "side":         side,
        "ticker":       ticker,
        "entry_price":  entry_price,
        "entry_date":   now_utc_iso(),
        "entry_be":     now_be(),
        "stake_eur":    VIRTUAL_STAKE,
        "confidence":   advice_card.get("confidence", 50),
        "sources":      advice_card.get("sources", []),
        "n_sources":    advice_card.get("n_sources", 0),
        # Check results — filled as time passes
        "check_4h":     None,
        "check_24h":    None,
        "check_5d":     None,
        # Status
        "status":       "open",
        "final_pnl":    None,
        "final_pct":    None,
        "closed_date":  None,
    }

    positions.append(position)
    print(f"  Portfolio: opened {side} {ticker} @ ${entry_price:.2f} (theme: {advice_card.get('theme')})")


# ── UPDATE POSITIONS ──────────────────────────────────────────────────────────
def _market_is_open():
    """Returns True if US markets are currently open (rough check)."""
    now_utc = datetime.now(timezone.utc)
    # Weekend
    if now_utc.weekday() >= 5:
        return False
    # Market hours: 13:30–20:00 UTC (09:30–16:00 EST)
    # Allow 30 min buffer each side for pre/after hours data
    hour_utc = now_utc.hour + now_utc.minute / 60
    return 13.0 <= hour_utc <= 20.5


def update_positions(seen_data):
    """
    Checks all open positions against current prices.
    Records P&L at 4h, 24h and 5d checkpoints.
    Closes positions after 5d final check.
    Returns list of newly completed checks.
    """
    positions = seen_data.get("portfolio", [])
    if not positions:
        return []

    if not _market_is_open():
        print("  Portfolio: market closed — skipping price checks")
        return []

    now       = datetime.now(timezone.utc)
    new_checks = []

    for pos in positions:
        if pos.get("status") == "closed":
            continue

        try:
            entry_date = datetime.fromisoformat(pos["entry_date"])
        except Exception:
            continue

        hours_elapsed = (now - entry_date).total_seconds() / 3600
        ticker        = pos["ticker"]
        entry_price   = pos["entry_price"]
        side          = pos["side"]

        current_price = get_price(ticker)
        if not current_price:
            continue

        # Calculate P&L
        if side == "BUY":
            pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SELL
            pct = ((entry_price - current_price) / entry_price) * 100

        pnl_eur = (pct / 100) * VIRTUAL_STAKE
        hit     = pct >= HIT_THRESHOLD

        # 4h check
        if hours_elapsed >= 4 and pos.get("check_4h") is None:
            pos["check_4h"] = {
                "price": current_price,
                "pct":   round(pct, 2),
                "pnl":   round(pnl_eur, 2),
                "hit":   hit,
                "date":  now_utc_iso(),
            }
            new_checks.append({**pos, "window": "4h", "pct": round(pct, 2), "pnl": round(pnl_eur, 2), "hit": hit})
            print(f"  Portfolio 4h: {ticker} {side} {pct:+.1f}% (€{pnl_eur:+.0f}) {'HIT' if hit else 'MISS'}")

        # 24h check
        if hours_elapsed >= 24 and pos.get("check_24h") is None:
            pos["check_24h"] = {
                "price": current_price,
                "pct":   round(pct, 2),
                "pnl":   round(pnl_eur, 2),
                "hit":   hit,
                "date":  now_utc_iso(),
            }
            new_checks.append({**pos, "window": "24h", "pct": round(pct, 2), "pnl": round(pnl_eur, 2), "hit": hit})
            print(f"  Portfolio 24h: {ticker} {side} {pct:+.1f}% (€{pnl_eur:+.0f}) {'HIT' if hit else 'MISS'}")

        # 5d (120h) check — final, close position
        if hours_elapsed >= 120 and pos.get("check_5d") is None:
            pos["check_5d"] = {
                "price": current_price,
                "pct":   round(pct, 2),
                "pnl":   round(pnl_eur, 2),
                "hit":   hit,
                "date":  now_utc_iso(),
            }
            pos["status"]      = "closed"
            pos["final_pnl"]   = round(pnl_eur, 2)
            pos["final_pct"]   = round(pct, 2)
            pos["closed_date"] = now_utc_iso()
            new_checks.append({**pos, "window": "5d", "pct": round(pct, 2), "pnl": round(pnl_eur, 2), "hit": hit})
            print(f"  Portfolio 5d (closed): {ticker} {side} {pct:+.1f}% (€{pnl_eur:+.0f}) {'HIT' if hit else 'MISS'}")

    # Update platform score
    _update_platform_score(seen_data, new_checks)

    # Keep last 100 positions
    seen_data["portfolio"] = positions[-100:]

    return new_checks


# ── PLATFORM SCORE ────────────────────────────────────────────────────────────
def _update_platform_score(seen_data, new_checks):
    """Maintains adaptive confidence score based on rolling hit rate."""
    # Defensive init — merge missing keys in case schema evolved
    score = _ensure_score(seen_data)

    for chk in new_checks:
        window  = chk.get("window", "5d")
        hit     = chk.get("hit", False)
        pnl     = chk.get("pnl", 0.0)
        theme   = chk.get("theme", "unknown")

        # Overall
        if hit:
            score["total_hits"]   += 1
        else:
            score["total_misses"] += 1
        score["total_pnl"] += pnl

        # By window
        if window in score["by_window"]:
            if hit:
                score["by_window"][window]["hits"]   += 1
            else:
                score["by_window"][window]["misses"] += 1
            score["by_window"][window]["pnl"] = score["by_window"][window].get("pnl", 0.0) + pnl

        # By theme
        if theme not in score["by_theme"]:
            score["by_theme"][theme] = {"hits": 0, "misses": 0, "pnl": 0.0}
        if hit:
            score["by_theme"][theme]["hits"]   += 1
        else:
            score["by_theme"][theme]["misses"] += 1
        score["by_theme"][theme]["pnl"] += pnl

        # Rolling window (only 5d = final result)
        if window == "5d":
            score["rolling"].append({
                "hit":    hit,
                "pnl":    pnl,
                "theme":  theme,
                "ticker": chk.get("ticker", ""),
                "pct":    chk.get("pct", 0),
                "date":   now_utc_iso(),
            })
            score["rolling"] = score["rolling"][-ROLLING_WINDOW:]


def _ensure_score(seen_data):
    """Ensure platform_score has all required keys — safe to call anywhere."""
    defaults = {
        "total_hits": 0, "total_misses": 0, "total_pnl": 0.0,
        "by_window": {"4h": {"hits":0,"misses":0,"pnl":0.0},
                      "24h":{"hits":0,"misses":0,"pnl":0.0},
                      "5d": {"hits":0,"misses":0,"pnl":0.0}},
        "by_theme": {}, "rolling": [],
    }
    score = seen_data.setdefault("platform_score", {})
    for k, v in defaults.items():
        score.setdefault(k, v)
    # Deep-merge by_window — existing entries may be missing keys (e.g. "pnl")
    window_default = {"hits": 0, "misses": 0, "pnl": 0.0}
    for w in ["4h", "24h", "5d"]:
        if w not in score["by_window"]:
            score["by_window"][w] = dict(window_default)
        else:
            for wk, wv in window_default.items():
                score["by_window"][w].setdefault(wk, wv)
    return score


def get_platform_score(seen_data):
    """
    Returns current platform performance metrics.
    Rolling hit rate = last ROLLING_WINDOW 5d results.
    """
    score    = _ensure_score(seen_data)
    rolling  = score.get("rolling", [])
    total    = score.get("total_hits", 0) + score.get("total_misses", 0)

    # Rolling hit rate
    if rolling:
        roll_hits = sum(1 for r in rolling if r.get("hit"))
        roll_rate = roll_hits / len(rolling)
    else:
        roll_hits = 0
        roll_rate = None

    # Overall hit rate
    overall_rate = score.get("total_hits", 0) / total if total else None

    # Best performing theme
    best_theme = None
    best_rate  = 0
    for theme, ts in score.get("by_theme", {}).items():
        t = ts["hits"] + ts["misses"]
        if t >= 3:  # need at least 3 results to be meaningful
            r = ts["hits"] / t
            if r > best_rate:
                best_rate  = r
                best_theme = theme

    # Best window
    best_window = None
    best_wrate  = 0
    for window, ws in score.get("by_window", {}).items():
        t = ws["hits"] + ws["misses"]
        if t >= 3:
            r = ws["hits"] / t
            if r > best_wrate:
                best_wrate  = r
                best_window = window

    return {
        "rolling_rate":   roll_rate,
        "rolling_hits":   roll_hits,
        "rolling_total":  len(rolling),
        "overall_rate":   overall_rate,
        "overall_hits":   score.get("total_hits", 0),
        "overall_total":  total,
        "total_pnl":      score.get("total_pnl", 0.0),
        "best_theme":     best_theme,
        "best_theme_rate": best_rate,
        "best_window":    best_window,
        "best_window_rate": best_wrate,
        "by_theme":       score.get("by_theme", {}),
        "by_window":      score.get("by_window", {}),
    }


# ── PORTFOLIO SUMMARY ─────────────────────────────────────────────────────────
def get_open_positions(seen_data):
    """Returns all currently open positions with current P&L."""
    positions = seen_data.get("portfolio", [])
    open_pos  = []

    for pos in positions:
        if pos.get("status") != "open":
            continue

        ticker      = pos["ticker"]
        entry_price = pos["entry_price"]
        side        = pos["side"]
        current     = get_price(ticker)

        if current and entry_price:
            if side == "BUY":
                pct = ((current - entry_price) / entry_price) * 100
            else:
                pct = ((entry_price - current) / entry_price) * 100
            pnl = (pct / 100) * VIRTUAL_STAKE
        else:
            pct = 0.0
            pnl = 0.0
            current = entry_price

        # Age
        try:
            entry_dt  = datetime.fromisoformat(pos["entry_date"])
            hours_old = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 3600
            if hours_old < 24:
                age_str = f"{hours_old:.0f}h ago"
            else:
                age_str = f"{hours_old/24:.0f}d ago"
        except Exception:
            age_str = "?"

        open_pos.append({
            **pos,
            "current_price": current,
            "current_pct":   round(pct, 2),
            "current_pnl":   round(pnl, 2),
            "age":           age_str,
        })

    return open_pos


def get_closed_positions(seen_data, limit=20):
    """Returns recently closed positions."""
    positions = seen_data.get("portfolio", [])
    closed    = [p for p in positions if p.get("status") == "closed"]
    return list(reversed(closed[-limit:]))
