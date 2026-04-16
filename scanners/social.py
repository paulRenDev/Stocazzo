"""
scanners/social.py — CronyPony v7
Reddit top posts — heavily filtered, only fires on multiple strong keywords.
Standalone test: python -m scanners.social
"""
from config import REDDIT_STRONG_KEYWORDS, REDDIT_TICKER_KEYWORDS, SOURCE_CREDIBILITY
from helpers import make_id, clean_html
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

REDDIT_FEEDS = [
    ("https://www.reddit.com/r/wallstreetbets/top/.rss?t=day", "WSB"),
    ("https://www.reddit.com/r/stocks/top/.rss?t=day",         "r/stocks"),
    ("https://www.reddit.com/r/options/top/.rss?t=day",        "r/options"),
]


def scan_reddit(seen_data):
    alerts = []
    try:
        import feedparser

        for feed_url, label in REDDIT_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    continue

                print(f"Reddit {label}: {len(feed.entries)} posts")

                for entry in feed.entries[:10]:
                    uid = make_id(entry.get("id", entry.get("title", "")))
                    if is_seen(uid, seen_data):
                        continue

                    text        = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
                    strong_hits = [k for k in REDDIT_STRONG_KEYWORDS if k in text]
                    ticker_hits = [k for k in REDDIT_TICKER_KEYWORDS if k in text]

                    # Filter: at least 2 strong keywords, or 1 strong + 2 tickers
                    if len(strong_hits) < 2 and not (strong_hits and len(ticker_hits) >= 2):
                        continue

                    direction = "BULLISH" if any(w in text for w in ["buy", "calls", "long", "moon"]) else \
                                "BEARISH" if any(w in text for w in ["puts", "short", "crash", "dump"]) else "WATCH"

                    alerts.append({
                        "source":    "Social Signal",
                        "type":      f"Reddit · {label}",
                        "direction": direction,
                        "title":     entry.get("title", "")[:120],
                        "detail":    clean_html(entry.get("summary", ""))[:150],
                        "link":      entry.get("link", "https://reddit.com"),
                        "keywords":  ", ".join((strong_hits[:3] + ticker_hits[:2])),
                        "etfs":      get_etfs(" ".join(strong_hits + ticker_hits)),
                        "urgency":   "LOW",
                        "uid":       uid,
                        "reasoning": {
                            "why":           f"Top Reddit post ({label}) mentions: {', '.join(strong_hits[:3])}",
                            "signal_type":   "Social signal — noisy but sometimes early. Heavy filter applied.",
                            "confidence":    30,
                            "source_weight": SOURCE_CREDIBILITY["Social Signal"]["weight"],
                            "hit_rate":      format_hit_rate("Social Signal", seen_data),
                            "caveat":        "Extreme noise. Never act on Reddit alone.",
                        },
                    })
                    mark_seen(uid, seen_data)

            except Exception as e:
                print(f"Reddit {label} error: {e}")

    except Exception as e:
        print(f"Reddit scanner error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_reddit(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
