"""
scanners/polymarket.py — CronyPony v7
Scans Polymarket prediction markets for unusual probabilities + volume.
Standalone test: python -m scanners.polymarket
"""
import json

from config import (
    POLYMARKET_KEYWORDS, POLYMARKET_MIN_VOLUME, POLYMARKET_HIGH_VOLUME,
    POLYMARKET_MIN_PROB, POLYMARKET_MAX_PROB, SOURCE_CREDIBILITY,
)
from helpers import safe_get, make_id
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate


def scan_polymarket(seen_data):
    alerts = []
    try:
        r = safe_get("https://gamma-api.polymarket.com/markets?closed=false&limit=50&tag=politics")
        if not r:
            print("Polymarket: unreachable")
            return alerts

        markets = r.json()
        print(f"Polymarket: {len(markets)} markets")

        for m in markets:
            question = m.get("question", "")
            uid      = make_id(question)

            if is_seen(uid, seen_data):
                continue
            if not any(k in question.lower() for k in POLYMARKET_KEYWORDS):
                continue

            try:
                outcomes = json.loads(m.get("outcomePrices", "[]"))
                if not outcomes:
                    continue

                price  = float(outcomes[0])
                volume = float(m.get("volume24hr", 0))

                significant = (
                    (price > POLYMARKET_MIN_PROB or price < POLYMARKET_MAX_PROB)
                    and volume > POLYMARKET_MIN_VOLUME
                ) or volume > POLYMARKET_HIGH_VOLUME

                if not significant:
                    continue

                direction  = "YES" if price > 0.5 else "NO"
                confidence = round(price * 100 if price > 0.5 else (1 - price) * 100)

                alerts.append({
                    "source":    "Polymarket",
                    "type":      "Prediction Market",
                    "direction": f"{direction} ({confidence}%)",
                    "title":     question,
                    "detail":    f"Probability {direction}: {confidence}% | 24h volume: ${volume:,.0f}",
                    "link":      f"https://polymarket.com/event/{m.get('slug', '')}",
                    "keywords":  f"p={confidence}%, vol=${volume:,.0f}",
                    "etfs":      get_etfs(question),
                    "urgency":   "HIGH" if volume > POLYMARKET_HIGH_VOLUME else "MEDIUM",
                    "uid":       uid,
                    "reasoning": {
                        "why":           f"Market probability {direction} at {confidence}% with ${volume:,.0f} 24h volume — statistically significant",
                        "signal_type":   "Crowd wisdom + possible insider positioning",
                        "confidence":    confidence,
                        "source_weight": SOURCE_CREDIBILITY["Polymarket"]["weight"],
                        "hit_rate":      format_hit_rate("Polymarket", seen_data),
                        "caveat":        "Anonymous accounts — cannot verify insider vs retail",
                    },
                })
                mark_seen(uid, seen_data)

            except Exception:
                continue

    except Exception as e:
        print(f"Polymarket error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_polymarket(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
