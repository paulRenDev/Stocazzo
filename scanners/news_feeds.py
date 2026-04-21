"""
scanners/news_feeds.py — Stocazzo v7.2
High-volume financial news scanner. Feeds The Macro Man and The Tape Reader.

Status per feed (verified against actual GitHub Actions runs 21/04/2026):
  ✅ ACTIVE:   MarketWatch, Motley Fool, Yahoo S&P500, Google News (10 queries)
  ❌ BLOCKED:  Reuters (timeout), AP (403), Yahoo Finance top (403),
               Seeking Alpha (403), Investing.com (403), Barrons (403),
               Benzinga (403), Capitol Trades (403), OpenInsider (403)
  ➡ ALREADY IN macro.py: FT, ECB, WSJ Markets, CNBC Markets (keep there, no dupe)
"""

import re
import hashlib
import feedparser
from datetime import datetime, timezone
from helpers import now_be
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

# ── ACTIVE FEEDS (confirmed working on GitHub Actions) ────────────────────────
FEEDS = [
    # MarketWatch — confirmed working
    ("https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines", "MarketWatch Headlines",  "MarketWatch RSS", 15),
    ("https://feeds.content.dowjones.io/public/rss/mw_bulletins",         "MarketWatch Bulletins",  "MarketWatch RSS", 10),

    # Yahoo Finance S&P500 feed — confirmed working
    ("https://finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US", "Yahoo S&P500", "Yahoo Finance RSS", 10),

    # Motley Fool — confirmed working
    ("https://www.fool.com/feeds/index.aspx", "Motley Fool", "Motley Fool RSS", 10),

    # Google News — confirmed working, 10 targeted financial queries
    ("https://news.google.com/rss/search?q=federal+reserve+interest+rate+FOMC&hl=en-US&gl=US&ceid=US:en",     "Google News Fed",     "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=stock+market+earnings+beat+miss&hl=en-US&gl=US&ceid=US:en",         "Google News Earnings","Google News RSS", 10),
    ("https://news.google.com/rss/search?q=trump+tariff+trade+war+sanctions&hl=en-US&gl=US&ceid=US:en",        "Google News Tariffs", "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=oil+price+OPEC+energy+crude&hl=en-US&gl=US&ceid=US:en",             "Google News Energy",  "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=bitcoin+cryptocurrency+SEC+ETF&hl=en-US&gl=US&ceid=US:en",          "Google News Crypto",  "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=semiconductor+nvidia+chip+export+ban&hl=en-US&gl=US&ceid=US:en",    "Google News Semis",   "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=china+economy+yuan+trade+export&hl=en-US&gl=US&ceid=US:en",         "Google News China",   "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=defense+military+spending+NATO+weapons&hl=en-US&gl=US&ceid=US:en",  "Google News Defense", "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=gold+inflation+recession+commodity+forecast&hl=en-US&gl=US&ceid=US:en", "Google News Macro","Google News RSS", 10),
    ("https://news.google.com/rss/search?q=interest+rate+cut+hike+central+bank&hl=en-US&gl=US&ceid=US:en",     "Google News Rates",   "Google News RSS", 10),
    ("https://news.google.com/rss/search?q=merger+acquisition+deal+buyout+billion&hl=en-US&gl=US&ceid=US:en",  "Google News M&A",     "Google News RSS", 10),
]

# ── BLOCKED FEEDS (403 or timeout on GitHub Actions cloud IPs) ───────────────
# Re-enable if using a proxy, self-hosted runner, or if access opens up.
#
# BLOCKED_FEEDS = [
#     # Reuters — connection timeout from GitHub Actions IPs
#     ("https://feeds.reuters.com/reuters/businessNews",    "Reuters Business", "Reuters RSS", 15),
#     ("https://feeds.reuters.com/reuters/technologyNews",  "Reuters Tech",     "Reuters RSS", 10),
#     ("https://feeds.reuters.com/reuters/worldNews",       "Reuters World",    "Reuters RSS", 10),
#
#     # AP News — 403
#     ("https://rsshub.app/apnews/topics/business-news",   "AP Business",      "AP RSS", 15),
#     ("https://feeds.apnews.com/rss/apf-business",         "AP Business (2)",  "AP RSS", 15),
#
#     # Yahoo Finance top stories — 403 (S&P500 feed above works, this one doesn't)
#     ("https://finance.yahoo.com/rss/topstories",          "Yahoo Finance",    "Yahoo Finance RSS", 15),
#
#     # Seeking Alpha — 403
#     ("https://seekingalpha.com/market_currents.xml",      "Seeking Alpha",    "Seeking Alpha RSS", 10),
#
#     # Investing.com — 403
#     ("https://www.investing.com/rss/news.rss",            "Investing.com",    "Investing.com RSS", 15),
#     ("https://www.investing.com/rss/market_overview.rss", "Investing.com Macro","Investing.com RSS", 10),
#
#     # Barron's — 403
#     ("https://www.barrons.com/xml/rss/3_7510.xml",        "Barron's",         "Barrons RSS", 10),
#
#     # Benzinga — 403 from cloud IPs
#     ("https://feeds.benzinga.com/benzinga/news",           "Benzinga",         "Benzinga RSS", 10),
#     ("https://www.benzinga.com/feed",                      "Benzinga Alt",     "Benzinga RSS", 10),
#
#     # Capitol Trades RSS — 403
#     ("https://www.capitoltrades.com/trades?pageSize=20&format=rss", "Capitol Trades", "Capitol Trades", 20),
#
#     # OpenInsider RSS — 403
#     ("http://openinsider.com/rss?type=buys-only&minval=100000", "OpenInsider", "OpenInsider", 20),
# ]


# ── KEYWORD SCORING ───────────────────────────────────────────────────────────
BULLISH_KEYWORDS = [
    "rate cut", "fed pivot", "stimulus", "bailout", "deal signed", "ceasefire",
    "peace deal", "tariff pause", "tariff exemption", "trade deal", "recovery",
    "gdp beat", "jobs beat", "inflation falls", "soft landing", "rate pause",
    "china deal", "sanctions lifted", "earnings beat", "revenue beat",
    "raised guidance", "upgrade", "strong buy", "buy rating", "outperform",
    "record high", "rally", "surge", "breakout", "approval", "partnership",
    "acquisition", "merger", "buyback", "dividend increase", "beat estimates",
    "above expectations", "positive outlook", "growth acceleration",
    "easing", "dovish", "stimulus package", "rate reduction",
]

BEARISH_KEYWORDS = [
    "rate hike", "tightening", "tariff hike", "new tariffs", "sanctions imposed",
    "war escalation", "oil embargo", "recession fears", "gdp miss",
    "inflation surge", "bank failure", "default", "credit downgrade",
    "supply chain disruption", "chip ban", "trade war escalates",
    "earnings miss", "revenue miss", "lowered guidance", "downgrade",
    "sell rating", "underperform", "crash", "plunge", "collapse",
    "layoffs", "bankruptcy", "investigation", "fine", "penalty",
    "below expectations", "miss estimates", "profit warning", "writedown",
    "debt crisis", "currency crisis", "market selloff", "hawkish",
    "rate increase", "tightening policy", "contraction",
]

THEME_MAP = {
    "energy":      ["oil", "gas", "opec", "energy", "crude", "lng", "pipeline", "exxon", "chevron"],
    "defense":     ["war", "military", "nato", "ukraine", "russia", "iran", "strike", "missile", "defense", "lockheed", "raytheon"],
    "fed":         ["fed", "federal reserve", "interest rate", "rate cut", "rate hike", "powell", "ecb", "lagarde", "monetary policy", "fomc"],
    "trade":       ["tariff", "trade war", "sanctions", "china", "import", "export", "wto", "customs", "trade deal"],
    "tech":        ["semiconductor", "chip", "nvidia", "ai", "artificial intelligence", "tech", "ban", "huawei", "tsmc", "microsoft", "apple", "google", "meta"],
    "crypto":      ["bitcoin", "crypto", "btc", "ethereum", "coinbase", "binance", "stablecoin"],
    "commodities": ["gold", "silver", "copper", "wheat", "food prices", "commodity", "lithium"],
    "macro":       ["gdp", "inflation", "cpi", "pce", "jobs", "unemployment", "recession", "soft landing", "earnings", "revenue"],
    "finance":     ["bank", "jpmorgan", "goldman", "morgan stanley", "treasury", "bond yield", "credit", "debt"],
    "merger":      ["merger", "acquisition", "takeover", "buyout", "billion deal"],
}

ETF_THEME_MAP = {
    "energy":      "oil energy",
    "defense":     "defense military",
    "fed":         "bonds rates",
    "trade":       "trade tariff",
    "tech":        "tech semiconductor",
    "crypto":      "crypto bitcoin",
    "commodities": "gold commodities",
    "macro":       "market broad",
    "finance":     "finance banking",
    "merger":      "market broad",
}


def _clean(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip().lower()


def _title_uid(title: str) -> str:
    """
    Dedup by title + date — same story on multiple feeds gets same hash today,
    but re-surfaces tomorrow if still relevant. Prevents permanent dedup of
    ongoing stories (e.g. tariff negotiations that run for weeks).
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    normalized = re.sub(r'[^a-z0-9 ]', '', title.lower().strip())
    normalized = re.sub(r'\s+', ' ', normalized)[:80]
    return hashlib.md5(f"{normalized}|{today}".encode()).hexdigest()[:12]


def _score(text: str):
    bull = sum(1 for kw in BULLISH_KEYWORDS if kw in text)
    bear = sum(1 for kw in BEARISH_KEYWORDS if kw in text)
    return bull, bear


def _themes(text: str) -> list:
    return [theme for theme, keywords in THEME_MAP.items()
            if any(kw in text for kw in keywords)]


def scan_news_feeds(seen_data) -> list:
    alerts   = []
    seen_ids = set(seen_data.get("ids", []))
    hit_rate = format_hit_rate("Macro RSS", seen_data)

    for feed_url, feed_label, source_tag, max_entries in FEEDS:
        try:
            feed    = feedparser.parse(feed_url)
            entries = feed.entries[:max_entries]
            if not entries:
                continue

            print(f"  {feed_label}: {len(entries)} entries")
            feed_count = 0

            for entry in entries:
                title   = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                link    = entry.get("link", feed_url)

                if not title:
                    continue

                uid = _title_uid(title)
                if uid in seen_ids:
                    continue

                text   = _clean(title + " " + summary)
                themes = _themes(text)

                if not themes:
                    continue

                bull, bear = _score(text)

                if bull == 0 and bear == 0:
                    continue

                direction = "BULLISH" if bull > bear else "BEARISH" if bear > bull else "NEUTRAL"
                if direction == "NEUTRAL":
                    continue

                urgency = "HIGH"   if (bull >= 3 or bear >= 3) else \
                          "MEDIUM" if (bull + bear >= 2)        else "LOW"
                conf    = min(60, 25 + (bull + bear) * 8)

                primary_theme = themes[0]
                etf_query     = ETF_THEME_MAP.get(primary_theme, primary_theme)
                etfs          = get_etfs(etf_query)

                alerts.append({
                    "source":    source_tag,
                    "type":      f"{feed_label} · {', '.join(themes[:2])}",
                    "direction": direction,
                    "title":     title[:120],
                    "detail":    _clean(summary)[:200] if summary else title[:200],
                    "link":      link,
                    "keywords":  ", ".join(themes[:4]),
                    "etfs":      etfs,
                    "urgency":   urgency,
                    "uid":       uid,
                    "date_be":   now_be(),
                    "reasoning": {
                        "why":           f"{feed_label}: {title[:80]}. {bull} bullish / {bear} bearish signals.",
                        "signal_type":   f"News RSS — {feed_label}",
                        "confidence":    conf,
                        "source_weight": 2,
                        "hit_rate":      hit_rate,
                        "caveat":        "News follows events — use to confirm crony signals or set macro context.",
                        "breakdown":     [],
                    },
                })

                seen_ids.add(uid)
                seen_data.setdefault("ids", []).append(uid)
                feed_count += 1

            if feed_count:
                print(f"    → {feed_count} new signals from {feed_label}")

        except Exception as e:
            print(f"  {feed_label}: failed — {e}")
            continue

    print(f"News feeds total: {len(alerts)} new signals")
    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen   = load_seen()
    alerts = scan_news_feeds(seen)
    print(f"\nTotal: {len(alerts)} signals")
    for a in alerts[:20]:
        print(f"[{a['urgency']}] [{a['source']}] {a['title'][:80]} — {a['direction']}")
