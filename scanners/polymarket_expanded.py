"""
scanners/polymarket_expanded.py — Stocazzo v7.2
Expanded Polymarket scanner — pulls from ALL financially relevant categories.

Fix v7.2.1: Removed cross-tag deduplication that was collapsing 350 markets
back to 50. Markets are now deduplicated only against seen_signals.json,
not against each other within a run. This gives 350 unique market checks
instead of 50.
"""
import re
import json

from config import (
    POLYMARKET_KEYWORDS, POLYMARKET_NOISE_KEYWORDS,
    POLYMARKET_MIN_VOLUME, POLYMARKET_HIGH_VOLUME,
    POLYMARKET_MIN_PROB, POLYMARKET_MAX_PROB, SOURCE_CREDIBILITY,
)
from helpers import safe_get, make_id
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

POLYMARKET_TAGS = [
    "politics",
    "economics",
    "crypto",
    "financials",
    "commodities",
    "geopolitics",
    "science",
]

BASE_URL = "https://gamma-api.polymarket.com/markets?closed=false&limit=50&tag={tag}"

BEARISH_EVENTS = [
    "recession", "crash", "war", "invasion", "sanction", "ban",
    "tariff", "cut", "crisis", "collapse", "fail", "default",
    "downgrade", "embargo", "attack",
]


def _word_match(text, keywords):
    for kw in keywords:
        if " " in kw:
            if kw in text:
                return True
        else:
            if re.search(r'\b' + re.escape(kw), text):
                return True
    return False


def scan_polymarket_expanded(seen_data):
    """
    Scans Polymarket across all financial categories.
    Each tag is processed independently — no cross-tag dedup.
    Only deduplicates against seen_signals.json (already-processed markets).
    """
    alerts   = []
    seen_ids = set(seen_data.get("ids", []))

    # Track slugs seen THIS run to avoid processing the exact same market
    # twice if it appears in multiple tags — but use question text not slug
    # since the same question may have different slugs
    seen_questions_this_run = set()
    total_markets = 0

    for tag in POLYMARKET_TAGS:
        try:
            r = safe_get(BASE_URL.format(tag=tag))
            if not r:
                print(f"Polymarket [{tag}]: unreachable")
                continue

            markets = r.json()
            if not isinstance(markets, list):
                print(f"Polymarket [{tag}]: unexpected response")
                continue

            print(f"Polymarket [{tag}]: {len(markets)} markets")
            total_markets += len(markets)

            for m in markets:
                question = m.get("question", "")
                if not question:
                    continue

                # Skip if same question already processed this run
                q_key = question.lower().strip()[:80]
                if q_key in seen_questions_this_run:
                    continue
                seen_questions_this_run.add(q_key)

                try:
                    _op     = json.loads(m.get("outcomePrices", "[]") or "[]")
                    _p      = float(_op[0]) if _op else 0.5
                    _bucket = int(_p * 10)
                except Exception:
                    _bucket = 5

                uid = make_id(f"{question}|{_bucket}")
                if uid in seen_ids:
                    continue

                q_lower = question.lower()

                # Gate 1: noise filter
                if _word_match(q_lower, POLYMARKET_NOISE_KEYWORDS):
                    continue

                # Gate 2: financial relevance
                if not _word_match(q_lower, POLYMARKET_KEYWORDS):
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

                    event_is_bearish = any(b in q_lower for b in BEARISH_EVENTS)
                    if direction == "YES":
                        market_direction = "BEARISH" if event_is_bearish else "BULLISH"
                    else:
                        market_direction = "BULLISH" if event_is_bearish else "BEARISH"

                    slug = m.get("slug", "")

                    alerts.append({
                        "source":       "Polymarket",
                        "type":         f"Prediction Market · {tag}",
                        "direction":    market_direction,
                        "pm_direction": f"{direction} ({confidence}%)",
                        "title":        question,
                        "detail":       f"Market pricing {direction} at {confidence}% | 24h vol: ${volume:,.0f} | Signal: {market_direction}",
                        "link":         f"https://polymarket.com/event/{slug}",
                        "keywords":     f"p={confidence}%, vol=${volume:,.0f}, tag={tag}",
                        "etfs":         get_etfs(question),
                        "urgency":      "HIGH" if volume > POLYMARKET_HIGH_VOLUME else "MEDIUM",
                        "uid":          uid,
                        "date_be":      "",
                        "reasoning": {
                            "why":           f"Market probability {direction} at {confidence}% with ${volume:,.0f} 24h volume",
                            "signal_type":   f"Prediction market — {tag} category",
                            "confidence":    confidence,
                            "source_weight": SOURCE_CREDIBILITY.get("Polymarket", {}).get("weight", 5),
                            "hit_rate":      format_hit_rate("Polymarket", seen_data),
                            "caveat":        "Anonymous accounts — cannot verify insider vs retail",
                            "breakdown":     [],
                        },
                    })

                    seen_ids.add(uid)
                    seen_data.setdefault("ids", []).append(uid)
                    mark_seen(uid, seen_data)

                except Exception:
                    continue

        except Exception as e:
            print(f"Polymarket [{tag}] error: {e}")
            continue

    print(f"Polymarket expanded: {len(alerts)} new signals from {total_markets} markets across {len(POLYMARKET_TAGS)} categories")
    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen   = load_seen()
    alerts = scan_polymarket_expanded(seen)
    print(f"\nTotal: {len(alerts)}")
    for a in alerts[:10]:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
