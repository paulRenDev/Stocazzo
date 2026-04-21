"""
scanners/benzinga_rss.py — Stocazzo v7.2

STATUS: Blocked — 403 on GitHub Actions cloud IPs.
Kept in codebase for when access opens up.
scan_benzinga() returns [] silently for now.

Benzinga RSS: https://feeds.benzinga.com/benzinga/news
              https://www.benzinga.com/feed
"""

# ── GREYED OUT — 403 on GitHub Actions cloud IPs ─────────────────────────────
#
# import feedparser, hashlib, re
# from helpers import now_be
# from etf_mapper import get_etfs
#
# FEEDS = [
#     ("https://feeds.benzinga.com/benzinga/news", "Benzinga RSS"),
#     ("https://www.benzinga.com/feed",             "Benzinga Alt"),
# ]
# BULL_PATTERNS = ["surge", "rally", "breakout", "beat", "record high", "upgrade", ...]
# BEAR_PATTERNS = ["crash", "plunge", "decline", "miss", "downgrade", "layoffs", ...]
#
# def scan_benzinga(seen_data):
#     ... full implementation ready, re-enable when access available


def scan_benzinga(seen_data):
    """Blocked — 403 on GitHub Actions cloud IPs. Returns empty list."""
    return []
