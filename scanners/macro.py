"""
scanners/macro.py — Stocazzo v7
Macro scanner: GDELT geopolitical news + RSS feeds (Reuters/FT/ECB/Fed) + Fear & Greed.
Detects market-relevant macro trends and generates directional signals.
Standalone test: python -m scanners.macro
"""
import re
import json
from datetime import datetime, timezone, timedelta

from config import SOURCE_CREDIBILITY
from helpers import safe_get, make_id, now_utc
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

# ── RSS FEEDS ─────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    ("https://feeds.reuters.com/reuters/businessNews",          "Reuters Business"),
    ("https://feeds.reuters.com/reuters/technologyNews",        "Reuters Tech"),
    ("https://www.ft.com/rss/home/uk",                          "Financial Times"),
    ("https://www.ecb.europa.eu/rss/press.html",                "ECB"),
    ("https://feeds.a.dj.com/rss/RSSMarketsMain.xml",          "WSJ Markets"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "CNBC Markets"),
]

# ── GDELT ─────────────────────────────────────────────────────────────────────
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&maxrecords=10&format=json&timespan=4h"

GDELT_QUERIES = [
    ("trump tariff trade", "tariff"),
    ("iran ceasefire oil", "oil"),
    ("fed interest rate decision", "fed"),
    ("china trade sanctions", "china"),
    ("ukraine russia war ceasefire", "ukraine"),
    ("opec oil production", "oil"),
    ("nvidia semiconductor chip ban", "semiconductor"),
    ("ecb rate decision europe", "ecb"),
]

# ── FEAR & GREED ──────────────────────────────────────────────────────────────
FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

# ── KEYWORDS ──────────────────────────────────────────────────────────────────
MACRO_BULLISH = [
    "rate cut", "stimulus", "deal signed", "ceasefire", "peace",
    "tariff pause", "tariff exemption", "trade deal", "recovery",
    "gdp beat", "jobs beat", "inflation falls", "soft landing",
    "fed pivot", "rate pause", "china deal", "sanctions lifted",
]

MACRO_BEARISH = [
    "rate hike", "tariff hike", "new tariffs", "sanctions imposed",
    "war escalation", "oil embargo", "recession fears", "gdp miss",
    "inflation surge", "bank failure", "default", "credit downgrade",
    "supply chain", "chip ban", "trade war escalates",
]

MACRO_THEMES = {
    "energy":       ["oil", "gas", "opec", "energy", "crude", "lng", "pipeline"],
    "defense":      ["war", "military", "nato", "ukraine", "russia", "iran", "strike", "missile"],
    "fed":          ["fed", "federal reserve", "interest rate", "rate cut", "rate hike", "powell", "ecb", "lagarde"],
    "trade":        ["tariff", "trade war", "sanctions", "china", "import", "export", "wto"],
    "tech":         ["semiconductor", "chip", "nvidia", "ai", "tech", "ban", "huawei", "tsmc"],
    "crypto":       ["bitcoin", "crypto", "sec", "etf approval", "coinbase"],
    "commodities":  ["gold", "silver", "copper", "wheat", "food prices"],
    "macro":        ["gdp", "inflation", "cpi", "jobs", "unemployment", "recession", "soft landing"],
}


def scan_macro(seen_data):
    alerts = []

    # 1. RSS feeds
    alerts += _scan_rss_feeds(seen_data)

    # 2. GDELT
    alerts += _scan_gdelt(seen_data)

    # 3. Fear & Greed index
    alerts += _scan_fear_greed(seen_data)

    return alerts


# ── RSS ───────────────────────────────────────────────────────────────────────
def _scan_rss_feeds(seen_data):
    alerts = []
    try:
        import feedparser

        for feed_url, label in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    continue

                print(f"RSS {label}: {len(feed.entries)} entries")

                for entry in feed.entries[:10]:
                    uid = make_id(f"rss-{entry.get('id', entry.get('title', ''))}")
                    if is_seen(uid, seen_data):
                        continue

                    title   = entry.get("title", "")
                    summary = entry.get("summary", "")
                    text    = (title + " " + summary).lower()
                    text    = re.sub(r'<[^>]+>', ' ', text)

                    # Find matching themes
                    themes = [theme for theme, keywords in MACRO_THEMES.items()
                              if any(kw in text for kw in keywords)]

                    if not themes:
                        continue

                    # Determine direction
                    bull = sum(1 for w in MACRO_BULLISH if w in text)
                    bear = sum(1 for w in MACRO_BEARISH if w in text)
                    direction = "BULLISH" if bull > bear else \
                                "BEARISH" if bear > bull else "NEUTRAL"

                    # Only fire on directional signals or high-value neutral
                    if direction == "NEUTRAL" and bull == 0 and bear == 0:
                        continue

                    urgency = "HIGH" if (bull >= 2 or bear >= 2) else "MEDIUM" if (bull + bear >= 1) else "LOW"

                    alerts.append({
                        "source":    "Macro RSS",
                        "type":      f"{label} · {', '.join(themes[:2])}",
                        "direction": direction,
                        "title":     title[:120],
                        "detail":    re.sub(r'<[^>]+>', '', summary)[:200],
                        "link":      entry.get("link", feed_url),
                        "keywords":  ", ".join(themes[:4]),
                        "etfs":      get_etfs(" ".join(themes)),
                        "urgency":   urgency,
                        "uid":       uid,
                        "reasoning": {
                            "why":           f"{label} reports on {', '.join(themes[:2])}. {bull} bullish / {bear} bearish signals in text.",
                            "signal_type":   f"News RSS — {label}. Macro context signal.",
                            "confidence":    55 if urgency == "HIGH" else 40 if urgency == "MEDIUM" else 25,
                            "source_weight": 2,
                            "hit_rate":      format_hit_rate("Macro RSS", seen_data),
                            "caveat":        "News follows events — not predictive. Use to confirm crony signals or set macro context.",
                        },
                    })
                    mark_seen(uid, seen_data)

            except Exception as e:
                print(f"RSS {label} error: {e}")

    except Exception as e:
        print(f"RSS scanner error: {e}")

    return alerts


# ── GDELT ─────────────────────────────────────────────────────────────────────
def _scan_gdelt(seen_data):
    import time
    alerts = []
    try:
        for i, (query, theme) in enumerate(GDELT_QUERIES):
            if i >= 1:  # max 1 GDELT query per run to avoid 429
                break
            try:
                time.sleep(3)
                url = GDELT_URL.format(query=query.replace(" ", "%20"))
                r   = safe_get(url, timeout=8)
                if not r:
                    print("GDELT: skipping remaining queries")
                    break

                data     = r.json()
                articles = data.get("articles", [])
                if not articles:
                    continue

                print(f"GDELT '{query}': {len(articles)} articles")

                # Aggregate tone across articles
                tones = []
                titles = []
                for art in articles[:5]:
                    tone = art.get("tone", 0)
                    if isinstance(tone, (int, float)):
                        tones.append(float(tone))
                    titles.append(art.get("title", ""))

                if not tones:
                    continue

                avg_tone   = sum(tones) / len(tones)
                uid        = make_id(f"gdelt-{theme}-{now_utc()[:13]}")  # hourly dedup

                if is_seen(uid, seen_data):
                    continue

                # GDELT tone: positive = good news, negative = bad news
                direction = "BULLISH" if avg_tone > 2 else "BEARISH" if avg_tone < -2 else "NEUTRAL"
                if direction == "NEUTRAL":
                    continue

                urgency   = "HIGH" if abs(avg_tone) > 5 else "MEDIUM" if abs(avg_tone) > 2 else "LOW"
                top_title = titles[0][:100] if titles else query

                alerts.append({
                    "source":    "GDELT",
                    "type":      f"Geopolitical · {theme}",
                    "direction": direction,
                    "title":     f"GDELT {theme}: {top_title}",
                    "detail":    f"Avg tone: {avg_tone:+.1f} across {len(articles)} articles. Theme: {theme}. Top: {top_title}",
                    "link":      f"https://gdeltproject.org/",
                    "keywords":  theme,
                    "etfs":      get_etfs(theme + " " + query),
                    "urgency":   urgency,
                    "uid":       uid,
                    "reasoning": {
                        "why":           f"GDELT scored {len(articles)} articles on '{query}' at avg tone {avg_tone:+.1f}. Strongly {'positive' if avg_tone > 0 else 'negative'} geopolitical sentiment.",
                        "signal_type":   "GDELT geopolitical news tone analysis — aggregates thousands of news sources globally.",
                        "confidence":    50 if urgency == "HIGH" else 35,
                        "source_weight": 2,
                        "hit_rate":      format_hit_rate("GDELT", seen_data),
                        "caveat":        "GDELT measures sentiment, not specific events. Best used as trend confirmation.",
                    },
                })
                mark_seen(uid, seen_data)

            except Exception as e:
                print(f"GDELT '{query}' error: {e}")

    except Exception as e:
        print(f"GDELT scanner error: {e}")

    return alerts


# ── FEAR & GREED ──────────────────────────────────────────────────────────────
def _scan_fear_greed(seen_data):
    alerts = []
    try:
        r = safe_get(FEAR_GREED_URL, timeout=8)
        if not r:
            print("Fear & Greed: unreachable")
            return alerts

        data  = r.json()
        score = None
        label = ""

        # Navigate the CNN response structure
        fg = data.get("fear_and_greed", data.get("fng_value", {}))
        if isinstance(fg, dict):
            score = float(fg.get("score", fg.get("value", 0)))
            label = fg.get("rating", fg.get("value_classification", ""))
        elif isinstance(data, dict):
            for key in ["score", "value", "current_value"]:
                if key in data:
                    score = float(data[key])
                    break

        if score is None:
            print("Fear & Greed: could not parse score")
            return alerts

        print(f"Fear & Greed: {score:.0f} ({label})")

        # Only fire on extremes — extreme fear or extreme greed
        uid = make_id(f"feargreed-{now_utc()[:10]}-{int(score//10)*10}")
        if is_seen(uid, seen_data):
            return alerts

        if score <= 20:  # Extreme fear = potential buy opportunity
            direction = "BULLISH"
            urgency   = "MEDIUM"
            why       = f"Extreme Fear ({score:.0f}/100) — historically a buy signal. Market oversold."
            etf_text  = "buy risk on"
        elif score >= 80:  # Extreme greed = potential sell signal
            direction = "BEARISH"
            urgency   = "LOW"
            why       = f"Extreme Greed ({score:.0f}/100) — market may be overextended. Consider reducing risk."
            etf_text  = "risk off gold bonds"
        else:
            return alerts  # Middle range — not actionable

        alerts.append({
            "source":    "Fear & Greed",
            "type":      f"CNN Sentiment · {label or ('Extreme Fear' if score <= 20 else 'Extreme Greed')}",
            "direction": direction,
            "title":     f"Fear & Greed Index: {score:.0f}/100 — {label or ('Extreme Fear' if score <= 20 else 'Extreme Greed')}",
            "detail":    why,
            "link":      "https://edition.cnn.com/markets/fear-and-greed",
            "keywords":  "sentiment, fear, greed, market",
            "etfs":      get_etfs(etf_text),
            "urgency":   urgency,
            "uid":       uid,
            "reasoning": {
                "why":           why,
                "signal_type":   "CNN Fear & Greed Index — composite of 7 market indicators.",
                "confidence":    50,
                "source_weight": 2,
                "hit_rate":      format_hit_rate("Fear & Greed", seen_data),
                "caveat":        "Contrarian indicator. Extreme fear = buy opportunity historically, but timing is uncertain.",
            },
        })
        mark_seen(uid, seen_data)

    except Exception as e:
        print(f"Fear & Greed error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_macro(seen)
    print(f"\nTotal macro alerts: {len(alerts)}")
    for a in alerts:
        print(f"[{a['urgency']}] [{a['source']}] {a['title'][:80]} — {a['direction']}")
