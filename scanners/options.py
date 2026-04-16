"""
scanners/options.py — CronyPony v7
Unusual Whales news RSS — options flow and dark pool news.
Standalone test: python -m scanners.options
"""
from config import CONGRESS_KEYWORDS, OPTION_KEYWORDS, SOURCE_CREDIBILITY
from helpers import make_id
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

MARKET_KEYWORDS = CONGRESS_KEYWORDS + [
    "spy", "qqq", "iwm", "xle", "xlf", "gld", "tlt", "uso",
    "tariff", "trump", "fed", "rate", "iran", "crypto", "bitcoin",
]


def scan_unusual_whales(seen_data):
    alerts = []
    try:
        import feedparser
        feed = feedparser.parse("https://unusualwhales.com/news.rss")

        if not feed.entries:
            print("Unusual Whales RSS: no entries")
            return alerts

        print(f"Unusual Whales RSS: {len(feed.entries)} entries")

        for entry in feed.entries[:20]:
            uid = make_id(entry.get("id", entry.get("title", "")))
            if is_seen(uid, seen_data):
                continue

            title   = entry.get("title", "").lower()
            summary = entry.get("summary", "").lower()
            text    = title + " " + summary

            if not any(k in text for k in OPTION_KEYWORDS):
                continue

            matched = [k for k in MARKET_KEYWORDS if k in text]
            if not matched:
                continue

            is_bullish = any(w in text for w in ["call", "bullish", "buy", "long"])
            is_bearish = any(w in text for w in ["put", "bearish", "sell", "short"])
            direction  = "BULLISH" if is_bullish and not is_bearish else \
                         "BEARISH" if is_bearish and not is_bullish else "FLOW"

            urgency = "MEDIUM" if any(w in text for w in ["massive", "unusual", "sweep", "whale"]) else "LOW"

            alerts.append({
                "source":    "Options Flow",
                "type":      "Unusual Whales · Options/Dark Pool",
                "direction": direction,
                "title":     entry.get("title", "")[:120],
                "detail":    entry.get("summary", "")[:200],
                "link":      entry.get("link", "https://unusualwhales.com"),
                "keywords":  ", ".join(matched[:5]),
                "etfs":      get_etfs(" ".join(matched[:4]).lower()),
                "urgency":   urgency,
                "uid":       uid,
                "reasoning": {
                    "why":           f"Unusual Whales flagged {direction.lower()} options/dark pool on: {', '.join(matched[:4])}",
                    "signal_type":   "Options flow + dark pool news. Institutions leave footprints before news.",
                    "confidence":    55 if urgency == "MEDIUM" else 40,
                    "source_weight": SOURCE_CREDIBILITY["Options Flow"]["weight"],
                    "hit_rate":      format_hit_rate("Options Flow", seen_data),
                    "caveat":        "Direction unclear — could be hedge vs speculation. Combine with other sources.",
                },
            })
            mark_seen(uid, seen_data)

    except Exception as e:
        print(f"Unusual Whales RSS error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_unusual_whales(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
