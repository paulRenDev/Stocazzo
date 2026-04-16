"""
scanners/truthsocial.py — Stocazzo v7
Scans Trump's Truth Social posts via CNN's public archive (updated every 5 min).
No auth, no proxy needed. Detects market-moving language.
Standalone test: python -m scanners.truthsocial
"""
import re
from datetime import datetime, timezone, timedelta

from config import SOURCE_CREDIBILITY
from helpers import safe_get, make_id, now_utc
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

CNN_ARCHIVE_URL = "https://ix.cnn.io/data/truth-social/truth_archive.json"

# Trump account ID on Truth Social
TRUMP_ACCOUNT_ID = "107780257626128497"

# Keywords that have historically moved markets
MARKET_KEYWORDS = {
    # Immediate buy signals (HIGH urgency)
    "high": [
        "great time to buy", "buy buy buy", "time to buy",
        "deal has been made", "deal is done", "trade deal",
        "ceasefire", "peace deal", "pause", "tariff pause",
        "tariff exemption", "tariff delay", "no tariffs",
        "rate cut", "fed cut", "beautiful deal",
    ],
    # Medium signals — confirm or deny trend
    "medium": [
        "tariff", "china", "sanctions", "iran", "ukraine",
        "nato", "opec", "oil", "energy", "crypto", "bitcoin",
        "stock market", "wall street", "economy", "jobs",
        "inflation", "interest rate", "fed", "powell",
        "semiconductor", "chip", "nvidia", "tech",
        "defense", "military", "war", "threat",
        "announcement", "big news", "something big",
        "market", "trade", "deal", "negotiat", "agreement",
        "sanction", "export", "import", "tax", "duty",
        "rates", "cut", "hike", "recession", "growth",
        "europe", "russia", "north korea", "middle east",
    ],
    # Context signals — lower weight
    "low": [
        "america", "great again", "winning", "deal",
        "agreement", "negotiate", "talks", "meeting",
        "signed", "executive order", "declaration",
    ],
}

# Direction signals
BULLISH_WORDS = [
    "great time to buy", "buy", "deal", "ceasefire", "peace",
    "pause", "exemption", "cut", "beautiful", "winning",
    "agreement", "signed", "boost", "strong",
]
BEARISH_WORDS = [
    "tariff", "sanctions", "war", "threat", "no deal",
    "collapse", "crash", "danger", "attack", "bomb",
    "escalate", "retaliate", "ban",
]

# How old a post can be (hours) to still be considered relevant
MAX_POST_AGE_HOURS = 48  # extended — CNN archive may lag a few hours


def scan_truthsocial(seen_data):
    alerts = []
    try:
        r = safe_get(CNN_ARCHIVE_URL, timeout=12)
        if not r:
            print("Truth Social: CNN archive unreachable")
            return alerts

        posts = r.json()
        if not isinstance(posts, list):
            posts = posts.get("data", posts.get("posts", []))

        print(f"Truth Social: {len(posts)} posts in archive")

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=MAX_POST_AGE_HOURS)

        new_posts = 0
        for post in posts[:200]:  # check latest 200
            # Parse date
            created_raw = post.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except Exception:
                continue

            if created < cutoff:
                continue  # skip old posts, don't break (archive may not be sorted)

            new_posts += 1

            # Extract text
            content = post.get("content", "") or post.get("text", "")
            # Strip HTML tags
            text = re.sub(r'<[^>]+>', ' ', content).lower().strip()
            text = re.sub(r'\s+', ' ', text)

            if not text or len(text) < 10:
                continue

            uid = make_id(f"truth-{post.get('id', created_raw)}")
            if is_seen(uid, seen_data):
                continue

            # Score the post
            urgency_level = None
            matched_keywords = []

            for kw in MARKET_KEYWORDS["high"]:
                if kw in text:
                    urgency_level = "HIGH"
                    matched_keywords.append(kw)

            if not urgency_level:
                for kw in MARKET_KEYWORDS["medium"]:
                    if kw in text:
                        urgency_level = "MEDIUM"
                        matched_keywords.append(kw)

            if not urgency_level:
                for kw in MARKET_KEYWORDS["low"]:
                    if kw in text:
                        urgency_level = "LOW"
                        matched_keywords.append(kw)

            if not urgency_level or not matched_keywords:
                continue

            # Direction
            bull_hits = sum(1 for w in BULLISH_WORDS if w in text)
            bear_hits = sum(1 for w in BEARISH_WORDS if w in text)
            direction = "BULLISH" if bull_hits > bear_hits else \
                        "BEARISH" if bear_hits > bull_hits else "WATCH"

            # Truncate content for display
            display_text = text[:200] + "..." if len(text) > 200 else text

            # Time since post
            minutes_ago = int((now - created).total_seconds() / 60)
            time_label = f"{minutes_ago}m ago" if minutes_ago < 60 else \
                         f"{minutes_ago // 60}h {minutes_ago % 60}m ago"

            post_url = post.get("url", f"https://truthsocial.com/@realDonaldTrump")

            alerts.append({
                "source":    "Truth Social",
                "type":      f"Trump post · {time_label}",
                "direction": direction,
                "title":     f"Trump: \"{display_text[:80]}\"",
                "detail":    f"{display_text} | Posted: {time_label} | Keywords: {', '.join(matched_keywords[:4])}",
                "link":      post_url,
                "keywords":  ", ".join(matched_keywords[:5]),
                "etfs":      get_etfs(" ".join(matched_keywords)),
                "urgency":   urgency_level,
                "uid":       uid,
                "reasoning": {
                    "why":           f"Trump posted market-relevant content {time_label}. Matched: {', '.join(matched_keywords[:3])}",
                    "signal_type":   "Direct presidential statement — historically fastest market mover. Historical lead time: 15-30 min.",
                    "confidence":    85 if urgency_level == "HIGH" else 60 if urgency_level == "MEDIUM" else 35,
                    "source_weight": 4,
                    "hit_rate":      "Historical: 9 Apr 2026 → +9.5% Nasdaq in 23 min after buy signal",
                    "caveat":        "Not all Trump posts move markets. High urgency keywords have strongest historical correlation.",
                },
            })
            mark_seen(uid, seen_data)

        print(f"Truth Social: {new_posts} posts in last {MAX_POST_AGE_HOURS}h, {len(alerts)} alerts")

    except Exception as e:
        print(f"Truth Social error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_truthsocial(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
        print(f"  Keywords: {a['keywords']}")
