"""
scanners/polymarket.py — Stocazzo v7
Scans Polymarket prediction markets for financially relevant signals.

Filtering logic (three gates, all must pass):
  1. NOISE gate:    contract must NOT match any noise keyword (sports, entertainment)
  2. KEYWORD gate:  contract must match at least one financial keyword
  3. VOLUME gate:   contract must have sufficient 24h volume

Word-boundary matching prevents false positives like:
  "Oilers" matching "oil", "billion" matching "bill", "games" matching "game"

Standalone test: python -m scanners.polymarket
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


def _word_match(text, keywords):
    """
    Returns True if any keyword appears in text as a whole word or word prefix.
    - Multi-word keywords (e.g. 'rate cut'): exact substring match
    - Single-word keywords: must start at a word boundary to prevent false positives
      like 'oil' matching 'Oilers', but allows 'tariff' to match 'tariffs'

    Examples:
      'oil' matches 'oil price' and 'crude oil' but NOT 'Oilers'
      'tariff' matches 'tariff' and 'tariffs' but NOT 'atarriff'
      'bill' matches 'bill' and 'billing' but NOT 'abillion'
    """
    for kw in keywords:
        if " " in kw:
            # Multi-word: exact substring match is precise enough
            if kw in text:
                return True
        else:
            # Single-word: must begin at a word boundary (\b before keyword)
            # but allows word to continue (handles plurals, verb forms)
            if re.search(r'\b' + re.escape(kw), text):
                return True
    return False


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

            q_lower = question.lower()

            # Gate 1: noise filter — hard reject (checked first, cheapest)
            if _word_match(q_lower, POLYMARKET_NOISE_KEYWORDS):
                continue

            # Gate 2: financial relevance — must match at least one keyword
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

                # Derive market signal direction for portfolio
                # YES on a bullish event = BULLISH; YES on a bearish event = BEARISH
                bearish_events = ["recession", "crash", "war", "invasion", "sanction",
                                  "ban", "tariff", "cut", "crisis", "collapse", "fail"]
                event_is_bearish = any(b in question.lower() for b in bearish_events)
                if direction == "YES":
                    market_direction = "BEARISH" if event_is_bearish else "BULLISH"
                else:
                    market_direction = "BULLISH" if event_is_bearish else "BEARISH"

                alerts.append({
                    "source":    "Polymarket",
                    "type":      "Prediction Market",
                    "direction": market_direction,
                    "pm_direction": f"{direction} ({confidence}%)",
                    "title":     question,
                    "detail":    f"Market pricing {direction} at {confidence}% | 24h vol: ${volume:,.0f} | Signal: {market_direction}",
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
