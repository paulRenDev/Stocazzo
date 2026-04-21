"""
scanners/polymarket_expanded.py — Stocazzo v7.3
Fixed Polymarket scanner.

Root cause of 0 signals (diagnosed via debug counters 21/04/2026):
- Polymarket API ignores tag= parameter, returns same 50 markets for all tags
- Those 50 markets: 33 sports/noise, 13 no financial keyword, 4 no volume = 0 pass
- Multi-tag loop was fetching the same 50 markets 7 times, all deduped away

Fix:
- Single call with limit=200 sorted by volume descending
- Gets more diverse markets past the sports-heavy top-50
- Removed the multi-tag loop entirely
- All filter logic identical — just wider net
"""
import re
import json
from datetime import datetime, timezone

from config import (
    POLYMARKET_KEYWORDS, POLYMARKET_NOISE_KEYWORDS,
    POLYMARKET_MIN_VOLUME, POLYMARKET_HIGH_VOLUME,
    POLYMARKET_MIN_PROB, POLYMARKET_MAX_PROB, SOURCE_CREDIBILITY,
)
from helpers import safe_get, make_id
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

# Single endpoint, high limit, sorted by volume — gets diverse markets
POLYMARKET_URL = "https://gamma-api.polymarket.com/markets?closed=false&limit=200&order=volume24hr&ascending=false"

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
    Fetches top-200 most active Polymarket markets sorted by 24h volume.
    Applies noise filter → keyword filter → volume/probability filter.
    UIDs include today's date so markets re-alert daily.
    """
    alerts   = []
    seen_ids = set(seen_data.get("ids", []))
    _today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    r = safe_get(POLYMARKET_URL)
    if not r:
        print("Polymarket expanded: unreachable — falling back to original scanner")
        return []

    markets = r.json()
    if not isinstance(markets, list):
        print("Polymarket expanded: unexpected response format")
        return []

    print(f"Polymarket expanded: {len(markets)} markets fetched")
    _dbg = {"noise": 0, "no_kw": 0, "no_vol": 0, "seen": 0, "pass": 0}

    for m in markets:
        question = m.get("question", "")
        if not question:
            continue

        q_lower = question.lower()

        # Gate 1: noise filter — hard reject sports/entertainment
        if _word_match(q_lower, POLYMARKET_NOISE_KEYWORDS):
            _dbg["noise"] += 1
            continue

        # Gate 2: financial relevance — must match at least one keyword
        if not _word_match(q_lower, POLYMARKET_KEYWORDS):
            _dbg["no_kw"] += 1
            continue

        # Gate 3: volume + probability significance
        try:
            outcomes = json.loads(m.get("outcomePrices", "[]") or "[]")
            if not outcomes:
                continue

            price  = float(outcomes[0])
            volume = float(m.get("volume24hr", 0))

            significant = (
                (price > POLYMARKET_MIN_PROB or price < POLYMARKET_MAX_PROB)
                and volume > POLYMARKET_MIN_VOLUME
            ) or volume > POLYMARKET_HIGH_VOLUME

            if not significant:
                _dbg["no_vol"] += 1
                continue

        except Exception:
            continue

        # UID: question + probability bucket + date → re-alerts daily and on 10% price move
        _bucket = int(price * 10)
        uid = make_id(f"{question}|{_bucket}|{_today}")
        if uid in seen_ids:
            _dbg["seen"] += 1
            continue

        direction  = "YES" if price > 0.5 else "NO"
        confidence = round(price * 100 if price > 0.5 else (1 - price) * 100)

        event_is_bearish = any(b in q_lower for b in BEARISH_EVENTS)
        if direction == "YES":
            market_direction = "BEARISH" if event_is_bearish else "BULLISH"
        else:
            market_direction = "BULLISH" if event_is_bearish else "BEARISH"

        slug = m.get("slug", "")
        _dbg["pass"] += 1

        alerts.append({
            "source":       "Polymarket",
            "type":         "Prediction Market",
            "direction":    market_direction,
            "pm_direction": f"{direction} ({confidence}%)",
            "title":        question,
            "detail":       f"Market pricing {direction} at {confidence}% | 24h vol: ${volume:,.0f} | Signal: {market_direction}",
            "link":         f"https://polymarket.com/event/{slug}",
            "keywords":     f"p={confidence}%, vol=${volume:,.0f}",
            "etfs":         get_etfs(question),
            "urgency":      "HIGH" if volume > POLYMARKET_HIGH_VOLUME else "MEDIUM",
            "uid":          uid,
            "date_be":      "",
            "reasoning": {
                "why":           f"Market probability {direction} at {confidence}% with ${volume:,.0f} 24h volume",
                "signal_type":   "Prediction market — top 200 by volume",
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

    print(f"Polymarket expanded: {_dbg['pass']} new signals | "
          f"noise={_dbg['noise']} no_kw={_dbg['no_kw']} no_vol={_dbg['no_vol']} seen={_dbg['seen']}")
    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen   = load_seen()
    alerts = scan_polymarket_expanded(seen)
    print(f"\nTotal: {len(alerts)}")
    for a in alerts[:10]:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
