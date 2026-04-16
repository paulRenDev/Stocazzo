"""
scanners/congress.py — CronyPony v7
STOCK Act disclosures via Finnhub + Pelosi Tracker.
Standalone test: python -m scanners.congress
"""
import re
import requests

from config import FINNHUB_KEY, GOVGREED_KEY, CONGRESS_KEYWORDS, SOURCE_CREDIBILITY
from helpers import safe_get, make_id
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate


# ── FINNHUB CONGRESSIONAL TRADES ─────────────────────────────────────────────
def scan_congress(seen_data):
    alerts = []
    if not FINNHUB_KEY:
        print("Congress: no FINNHUB_KEY")
        return alerts

    try:
        r = safe_get(f"https://finnhub.io/api/v1/stock/congressional-trading?token={FINNHUB_KEY}")
        if not r:
            print("Congress: unreachable")
            return alerts

        trades = r.json().get("data", [])
        print(f"Congress (Finnhub): {len(trades)} trades")

        for trade in trades[:30]:
            symbol = str(trade.get("symbol", "")).upper()
            name   = str(trade.get("name", "")).lower()
            uid    = make_id(str(trade.get("filingDate", "")) + symbol + str(trade.get("amount", "")))

            if is_seen(uid, seen_data):
                continue

            text    = f"{symbol} {name}".lower()
            matched = [k for k in CONGRESS_KEYWORDS if k in text]
            if not matched:
                continue

            tx_type   = str(trade.get("transactionType", "")).upper()
            direction = "BUY" if "PURCHASE" in tx_type or "BUY" in tx_type else \
                        "SELL" if "SALE" in tx_type else "WATCH"
            senator   = trade.get("name", "Unknown")
            amount    = trade.get("amount", "")

            alerts.append({
                "source":    "Congress",
                "type":      "STOCK Act Disclosure",
                "direction": direction,
                "title":     f"{senator} — {direction} {symbol}",
                "detail":    f"{name[:80]} | Amount: {amount} | Filed: {trade.get('filingDate', '')}",
                "link":      f"https://finnhub.io/stock-congressional-trading/{symbol}",
                "keywords":  ", ".join(matched[:4]),
                "etfs":      get_etfs(text),
                "urgency":   "LOW",
                "uid":       uid,
                "reasoning": {
                    "why":           f"{senator} filed a {direction} of {symbol} ({amount}). STOCK Act requires disclosure within 45 days.",
                    "signal_type":   "STOCK Act mandatory disclosure — 45-day lag",
                    "confidence":    50,
                    "source_weight": SOURCE_CREDIBILITY["Congress"]["weight"],
                    "hit_rate":      format_hit_rate("Congress", seen_data),
                    "caveat":        "45-day lag. Use for sector trend, not for timing.",
                },
            })
            mark_seen(uid, seen_data)

    except Exception as e:
        print(f"Congress Finnhub error: {e}")

    return alerts


# ── PELOSI TRACKER ────────────────────────────────────────────────────────────
def scan_pelosi(seen_data):
    alerts = []

    # Attempt 1: GovGreed API (if key available)
    if GOVGREED_KEY:
        alerts = _scan_govgreed(seen_data)
        if alerts:
            return alerts

    # Attempt 2: Pelosi Tracker public site
    try:
        from bs4 import BeautifulSoup
        r = safe_get("https://pelositracker.app/")
        if not r:
            print("Pelosi Tracker: unreachable")
            return alerts

        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ")
        print(f"Pelosi Tracker: fetched ({len(text)} chars)")

        trade_pattern = re.findall(
            r'Politician:\s*([^|]+)\|Type:\s*([^|]+)\|Action:\s*(Purchase|Sale)[^|]*\|Amount Range:\s*([^|]+)\|Filed/Traded:\s*([\d-]+)\s*/\s*([\d-]+)',
            text
        )
        print(f"Pelosi Tracker: {len(trade_pattern)} trades found")

        KNOWN_TICKERS = [
            "NVDA", "MSFT", "AAPL", "TSLA", "AMZN", "META", "GOOGL",
            "PLTR", "LMT", "RTX", "COIN", "XOM", "CVX", "AVGO", "VST", "TEM",
        ]

        for pol, trade_type, action, amount, filed_date, trade_date in trade_pattern[:20]:
            pol    = pol.strip()
            action = action.strip()
            amount = amount.strip()

            entry_pos = text.find(filed_date)
            snippet   = text[max(0, entry_pos - 200):entry_pos + 200]
            tickers   = re.findall(r'([A-Z]{2,5})', snippet)
            ticker    = next((t for t in tickers if t in KNOWN_TICKERS), "")

            uid = make_id(f"pelosi-{pol[:20]}-{ticker}-{action}-{trade_date}-{amount[:10]}")
            if is_seen(uid, seen_data):
                continue

            direction = "BUY" if action == "Purchase" else "SELL"
            is_option = "Option" in trade_type or "option" in trade_type
            is_large  = any(x in amount for x in ["500,001", "1,000,000", "5,000,000"])
            urgency   = "MEDIUM" if (is_large or is_option) else "LOW"

            title  = f"{pol} — {direction} {ticker or trade_type} {amount}"
            detail = f"Type: {trade_type} | Amount: {amount} | Traded: {trade_date} | Filed: {filed_date}"
            if is_option:
                detail += " | OPTIONS trade — typically deep-in-money (Pelosi signature)"

            alerts.append({
                "source":    "Pelosi Tracker",
                "type":      f"STOCK Act · {'Options' if is_option else 'Stock'}{' · LARGE' if is_large else ''}",
                "direction": direction,
                "title":     title,
                "detail":    detail,
                "link":      "https://pelositracker.app/",
                "keywords":  f"{ticker or 'unknown'}, {pol[:15]}",
                "etfs":      get_etfs((ticker + " " + trade_type).lower()),
                "urgency":   urgency,
                "uid":       uid,
                "reasoning": {
                    "why":           f"{pol} filed {direction} of {ticker or trade_type} ({amount}). Traded {trade_date}, filed {filed_date}.",
                    "signal_type":   f"STOCK Act official disclosure. {'Options = leveraged conviction.' if is_option else 'Stock trade.'} {'Large position (>$500k).' if is_large else ''}",
                    "confidence":    65 if (is_large and is_option) else 55 if is_large else 45,
                    "source_weight": SOURCE_CREDIBILITY["Pelosi Tracker"]["weight"],
                    "hit_rate":      format_hit_rate("Pelosi Tracker", seen_data),
                    "caveat":        f"STOCK Act lag: traded {trade_date}, filed {filed_date}. Always delayed.",
                },
            })
            mark_seen(uid, seen_data)

        if not alerts:
            print("Pelosi Tracker: no new notable trades found")

    except Exception as e:
        print(f"Pelosi Tracker error: {e}")

    return alerts


def _scan_govgreed(seen_data):
    """GovGreed API if GOVGREED_KEY is available."""
    alerts = []
    GOVGREED_API = "https://tsubgvnlqpkcmklfftav.supabase.co/functions/v1/api-gateway"
    try:
        r = requests.get(
            f"{GOVGREED_API}/v1/signals",
            params={"min_score": 50, "limit": 10},
            headers={"X-API-Key": GOVGREED_KEY, "User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if r.status_code != 200:
            return alerts

        data = r.json().get("data", [])
        print(f"GovGreed API: {len(data)} signals")

        for s in data:
            ticker    = s.get("ticker", "")
            uid       = make_id(f"govgreed-{ticker}-{s.get('opportunity_score', '')}")
            if is_seen(uid, seen_data):
                continue

            score     = s.get("opportunity_score", 0)
            tier      = s.get("master_tier", "")
            action    = s.get("recommendation_action", "MONITOR")
            reasons   = s.get("why_now_reasons", [])
            pol       = s.get("politician_name", "Unknown")
            layers    = s.get("active_signals", [])
            direction = "BUY" if "BUY" in action.upper() else "SELL" if "SELL" in action.upper() else "WATCH"
            urgency   = "HIGH" if score >= 72 else "MEDIUM" if score >= 50 else "LOW"

            alerts.append({
                "source":    "Pelosi Tracker",
                "type":      f"GovGreed AI · Tier {tier}",
                "direction": direction,
                "title":     f"{pol} — {direction} {ticker} (score {score:.0f}/100)",
                "detail":    " · ".join(reasons[:3]) if reasons else "Multi-layer congressional AI signal",
                "link":      f"https://www.govgreed.com/tickers/{ticker}",
                "keywords":  f"{ticker}, score={score:.0f}",
                "etfs":      get_etfs(ticker.lower()),
                "urgency":   urgency,
                "uid":       uid,
                "reasoning": {
                    "why":           " | ".join(reasons[:2]) if reasons else f"GovGreed AI score {score:.0f}/100",
                    "signal_type":   f"7-layer AI model, {len(layers)} layers active: {', '.join(layers[:3])}",
                    "confidence":    int(score),
                    "source_weight": 3,
                    "hit_rate":      "No verified data yet (GovGreed API)",
                    "caveat":        f"Tier {tier} — AI scoring, validate before acting. 45-day STOCK Act lag.",
                },
            })
            mark_seen(uid, seen_data)

    except Exception as e:
        print(f"GovGreed API error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_congress(seen) + scan_pelosi(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
