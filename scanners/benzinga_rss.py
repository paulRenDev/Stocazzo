"""
scanners/benzinga_rss.py — Stocazzo v7.2
Fast market-moving news via Benzinga RSS (free tier).
Feeds into The Tape Reader analyst (sentiment layer).
Replaces Options Flow (Unusual Whales blocked from cloud IPs).
"""
import feedparser
import hashlib
import re
from helpers import now_be
from etf_mapper import get_etfs

# Benzinga free RSS feeds — no API key needed
FEEDS = [
    ("https://www.benzinga.com/feed", "Benzinga RSS"),
    ("https://feeds.benzinga.com/benzinga/news", "Benzinga RSS"),
]

BULL_PATTERNS = [
    "surge", "rally", "breakout", "beat", "beats", "record high", "upgrade",
    "buy rating", "raised target", "strong buy", "bullish", "outperform",
    "earnings beat", "revenue beat", "raised guidance", "partnership", "deal",
]
BEAR_PATTERNS = [
    "crash", "plunge", "decline", "miss", "misses", "downgrade", "sell rating",
    "cut target", "bearish", "underperform", "earnings miss", "revenue miss",
    "lowered guidance", "layoffs", "bankruptcy", "investigation", "fine",
]

SECTOR_ETF_MAP = {
    "nvidia": [("NVDA", "NVDA", None), ("SOXX", "SOXX", None)],
    "semiconductor": [("SOXX", "SOXX", None)],
    "defense": [("ITA", "ITA", None)],
    "oil": [("XLE", "XLE", None)],
    "crypto": [("IBIT", "IBIT", None), ("COIN", "COIN", None)],
    "gold": [("GLD", "GLD", None)],
    "tech": [("QQQ", "QQQ", None)],
    "rate": [("TLT", "TLT", None)],
    "fed": [("TLT", "TLT", None), ("SPY", "SPY", None)],
    "tariff": [("SPY", "SPY", None), ("EEM", "EEM", None)],
}


def _score_title(title: str):
    text  = title.lower()
    bull  = sum(1 for p in BULL_PATTERNS if p in text)
    bear  = sum(1 for p in BEAR_PATTERNS if p in text)
    return bull, bear


def _map_etfs(title: str, ticker: str):
    text = title.lower()
    # Direct ticker first
    if ticker:
        direct = get_etfs(ticker)
        if direct:
            return direct[:2]
    # Sector keyword
    for keyword, etfs in SECTOR_ETF_MAP.items():
        if keyword in text:
            return etfs[:2]
    return [("SPY", "SPY", None)]


def scan_benzinga(seen_data):
    alerts   = []
    seen_ids = set(seen_data.get("ids", []))
    entries  = []

    for url, label in FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                entries = feed.entries[:25]
                print(f"{label}: {len(entries)} entries")
                break
        except Exception as e:
            print(f"{label}: fetch failed — {e}")
            continue

    if not entries:
        print("Benzinga RSS: no entries")
        return []

    for entry in entries:
        title   = entry.get("title", "")
        link    = entry.get("link", "")
        summary = entry.get("summary", "")

        if not title:
            continue

        uid = hashlib.md5(link.encode()).hexdigest()[:12]
        if uid in seen_ids:
            continue

        bull, bear = _score_title(title)
        if bull == 0 and bear == 0:
            continue  # no sentiment signal

        # Extract stock ticker
        tickers_found = re.findall(r'\b([A-Z]{2,5})\b', title + " " + summary)
        ticker        = tickers_found[0] if tickers_found else ""
        etfs          = _map_etfs(title, ticker)

        direction = "BUY — Bullish news" if bull > bear else "SELL — Bearish news"
        urgency   = "MEDIUM" if (bull + bear) >= 2 else "LOW"
        conf      = min(55, 30 + (bull + bear) * 5)

        alert = {
            "uid":       uid,
            "source":    "Benzinga RSS",
            "title":     title[:120],
            "detail":    summary[:200] if summary else title,
            "direction": direction,
            "urgency":   urgency,
            "etfs":      etfs,
            "link":      link,
            "date_be":   now_be(),
            "reasoning": {
                "why":        f"Benzinga: {title[:80]}",
                "caveat":     "News-based signal — confirm with price action before acting.",
                "confidence": conf,
                "breakdown":  [],
            },
        }

        seen_ids.add(uid)
        seen_data.setdefault("ids", []).append(uid)
        alerts.append(alert)

    print(f"Benzinga RSS: {len(alerts)} new signals")
    return alerts
