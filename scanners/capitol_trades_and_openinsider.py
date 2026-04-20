"""
scanners/capitol_trades.py — Stocazzo v7.2
Congressional trading disclosures via Capitol Trades RSS feed.
Free, reliable, no API key needed.
Replaces the broken Pelosi Tracker + 403 Finnhub congress endpoint.
"""
import feedparser
import hashlib
import re
from helpers import now_utc_iso, now_be, make_id
from etf_mapper import get_etfs

FEED_URL = "https://www.capitoltrades.com/trades?pageSize=20&format=rss"

# Sector keywords → ETF mapping
SECTOR_MAP = {
    "defense":        ["ITA", "XAR"],
    "energy":         ["XLE", "IEO"],
    "tech":           ["QQQ", "SOXX"],
    "semiconductor":  ["SOXX", "NVDA"],
    "pharma":         ["XBI", "IBB"],
    "finance":        ["XLF", "GS"],
    "real estate":    ["VNQ"],
    "crypto":         ["IBIT", "COIN"],
    "gold":           ["GLD", "IGLN"],
    "oil":            ["XLE", "OIL"],
}

BULL_KEYWORDS = ["purchase", "buy", "bought", "acquired", "long"]
BEAR_KEYWORDS = ["sale", "sold", "sell", "disposed", "short"]


def _ticker_to_etfs(stock_ticker, title_text):
    """Map a stock ticker or title keywords to ETFs."""
    etfs = []
    text = title_text.lower()

    # Direct ticker match in etf_mapper
    direct = get_etfs(stock_ticker)
    if direct:
        return direct[:2]

    # Sector keyword fallback
    for sector, sector_etfs in SECTOR_MAP.items():
        if sector in text:
            for e in sector_etfs[:2]:
                etfs.append((e, e, None))
            break

    return etfs or [("SPY", "SPY", None)]


def scan_capitol_trades(seen_data):
    alerts = []
    seen_ids = set(seen_data.get("ids", []))

    try:
        feed = feedparser.parse(FEED_URL)
        entries = feed.entries[:30]
        print(f"Capitol Trades: {len(entries)} entries")
    except Exception as e:
        print(f"Capitol Trades: fetch failed — {e}")
        return []

    for entry in entries:
        title   = entry.get("title", "")
        link    = entry.get("link", "")
        summary = entry.get("summary", "")
        text    = (title + " " + summary).lower()

        uid = hashlib.md5(link.encode()).hexdigest()[:12]
        if uid in seen_ids:
            continue

        # Determine direction
        is_bull = any(k in text for k in BULL_KEYWORDS)
        is_bear = any(k in text for k in BEAR_KEYWORDS)
        if not is_bull and not is_bear:
            continue

        direction = "BUY — Congressional Purchase" if is_bull else "SELL — Congressional Sale"

        # Extract stock ticker from title (e.g. "NVDA", "$AAPL")
        tickers_found = re.findall(r'\$?([A-Z]{2,5})\b', title)
        stock_ticker  = tickers_found[0] if tickers_found else ""
        etfs          = _ticker_to_etfs(stock_ticker, title + " " + summary)

        # Urgency: purchases by senior members are medium, sales are low (may be routine)
        urgency = "MEDIUM" if is_bull else "LOW"

        alert = {
            "uid":       uid,
            "source":    "Capitol Trades",
            "title":     title[:120],
            "detail":    summary[:200],
            "direction": direction,
            "urgency":   urgency,
            "etfs":      etfs,
            "link":      link,
            "date_be":   now_be(),
            "reasoning": {
                "why":        f"Congressional trade disclosure: {title}",
                "caveat":     "STOCK Act trades are disclosed with up to 45-day delay.",
                "confidence": 45,
                "breakdown":  [],
            },
        }

        seen_ids.add(uid)
        seen_data.setdefault("ids", []).append(uid)
        alerts.append(alert)

    print(f"Capitol Trades: {len(alerts)} new trades")
    return alerts


"""
scanners/openinsider.py — Stocazzo v7.2
CEO/CFO insider buying via OpenInsider RSS feed.
Free, reliable, no API key needed.
Replaces Dark Pool (cloud-blocked) as the insider buy signal source.
"""
# ── openinsider scanner is in the same file for simplicity ──────────────────

import feedparser as _feedparser
import hashlib as _hashlib
import re as _re
from helpers import now_utc_iso as _now_utc_iso, now_be as _now_be
from etf_mapper import get_etfs as _get_etfs

# Cluster buys: CEO/CFO purchases above $100k are HIGH signal
OPENINSIDER_FEED = "http://openinsider.com/rss?type=buys-only&minval=100000"

def scan_openinsider(seen_data):
    alerts  = []
    seen_ids = set(seen_data.get("ids", []))

    try:
        feed    = _feedparser.parse(OPENINSIDER_FEED)
        entries = feed.entries[:20]
        print(f"OpenInsider: {len(entries)} entries")
    except Exception as e:
        print(f"OpenInsider: fetch failed — {e}")
        return []

    for entry in entries:
        title   = entry.get("title", "")
        link    = entry.get("link", "")
        summary = entry.get("summary", "")

        uid = _hashlib.md5(link.encode()).hexdigest()[:12]
        if uid in seen_ids:
            continue

        # Only interested in C-suite buys (CEO, CFO, COO, President, Director)
        text_upper = (title + " " + summary).upper()
        is_csuite  = any(role in text_upper for role in ["CEO", "CFO", "COO", "PRESIDENT", "DIRECTOR", "CHAIRMAN"])
        if not is_csuite:
            continue

        # Extract ticker
        tickers = _re.findall(r'\b([A-Z]{2,5})\b', title)
        ticker  = tickers[0] if tickers else ""
        etfs    = _get_etfs(ticker)[:2] if ticker else [("SPY", "SPY", None)]

        # Size-based urgency
        amounts = _re.findall(r'\$?([\d,]+)', summary)
        amount  = 0
        for a in amounts:
            try:
                v = int(a.replace(",", ""))
                if v > amount:
                    amount = v
            except Exception:
                pass

        urgency = "HIGH" if amount >= 1_000_000 else "MEDIUM" if amount >= 250_000 else "LOW"

        alert = {
            "uid":       uid,
            "source":    "OpenInsider",
            "title":     title[:120],
            "detail":    summary[:200],
            "direction": f"BUY — C-suite insider purchase ({ticker})",
            "urgency":   urgency,
            "etfs":      etfs,
            "link":      link,
            "date_be":   _now_be(),
            "reasoning": {
                "why":        f"C-suite insider buy: {title}. Amount: ${amount:,}" if amount else f"C-suite insider buy: {title}",
                "caveat":     "Insider buys are strong signals but can be routine compensation-related. Size matters.",
                "confidence": 60 if amount >= 500_000 else 45,
                "breakdown":  [],
            },
        }

        seen_ids.add(uid)
        seen_data.setdefault("ids", []).append(uid)
        alerts.append(alert)

    print(f"OpenInsider: {len(alerts)} new C-suite buys")
    return alerts
