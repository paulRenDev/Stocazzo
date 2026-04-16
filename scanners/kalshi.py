"""
scanners/kalshi.py — CronyPony v7
Scans Kalshi CFTC-regulated prediction markets.
Standalone test: python -m scanners.kalshi
"""
from config import (
    POLYMARKET_KEYWORDS, KALSHI_MIN_VOLUME, KALSHI_HIGH_VOLUME,
    KALSHI_MIN_PROB, KALSHI_MAX_PROB, SOURCE_CREDIBILITY,
)
from helpers import safe_get, make_id
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

KALSHI_KEYWORDS = POLYMARKET_KEYWORDS + ["recession", "inflation", "gdp", "debt"]

KALSHI_URLS = [
    "https://api.elections.kalshi.com/trade-api/v2/markets?status=open&limit=50",
    "https://trading-api.kalshi.com/trade-api/v2/markets?status=open&limit=50",
]


def scan_kalshi(seen_data):
    alerts = []
    try:
        r = None
        for url in KALSHI_URLS:
            r = safe_get(url)
            if r:
                break

        if not r:
            print("Kalshi: unreachable")
            return alerts

        markets = r.json().get("markets", [])
        print(f"Kalshi: {len(markets)} markets")

        for m in markets:
            title    = m.get("title", "")
            subtitle = m.get("subtitle", "")
            uid      = make_id(m.get("ticker_name", title))

            if is_seen(uid, seen_data):
                continue

            text = (title + " " + subtitle).lower()
            if not any(k in text for k in KALSHI_KEYWORDS):
                continue

            yes_bid  = float(m.get("yes_bid", 0) or 0) / 100
            yes_ask  = float(m.get("yes_ask", 0) or 0) / 100
            volume   = float(m.get("volume", 0) or 0)
            price    = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else yes_bid or yes_ask

            significant = (
                (price > KALSHI_MIN_PROB or price < KALSHI_MAX_PROB) and volume > KALSHI_MIN_VOLUME
            ) or volume > KALSHI_HIGH_VOLUME

            if not significant:
                continue

            direction  = "YES" if price > 0.5 else "NO"
            confidence = round(price * 100 if price > 0.5 else (1 - price) * 100)
            ticker     = m.get("ticker_name", "")

            alerts.append({
                "source":    "Kalshi",
                "type":      "Prediction Market (regulated)",
                "direction": f"{direction} ({confidence}%)",
                "title":     title,
                "detail":    f"{subtitle} | {direction}: {confidence}% | Vol: {volume:,.0f} contracts",
                "link":      f"https://kalshi.com/markets/{ticker}" if ticker else "https://kalshi.com",
                "keywords":  f"p={confidence}%, vol={volume:,.0f}",
                "etfs":      get_etfs(text),
                "urgency":   "HIGH" if volume > KALSHI_HIGH_VOLUME else "MEDIUM",
                "uid":       uid,
                "reasoning": {
                    "why":           f"CFTC-regulated market at {confidence}% confidence, {volume:,.0f} contracts traded",
                    "signal_type":   "Regulated prediction market — harder to manipulate than offshore",
                    "confidence":    confidence,
                    "source_weight": SOURCE_CREDIBILITY["Kalshi"]["weight"],
                    "hit_rate":      format_hit_rate("Kalshi", seen_data),
                    "caveat":        "Regulated = less insider activity but also less alpha",
                },
            })
            mark_seen(uid, seen_data)

    except Exception as e:
        print(f"Kalshi error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_kalshi(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
