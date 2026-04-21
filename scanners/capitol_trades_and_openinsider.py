"""
scanners/capitol_trades_and_openinsider.py — Stocazzo v7.2

STATUS: Both sources return 403 from GitHub Actions cloud IPs.
Kept in codebase for when access opens up (proxy, self-hosted runner, etc).
scan_capitol_trades() and scan_openinsider() return [] silently for now.

Capitol Trades RSS: https://www.capitoltrades.com/trades?pageSize=20&format=rss
OpenInsider RSS:    http://openinsider.com/rss?type=buys-only&minval=100000
"""

# ── GREYED OUT — 403 on GitHub Actions cloud IPs ─────────────────────────────
#
# import feedparser
# import hashlib
# import re
# from helpers import now_be
# from etf_mapper import get_etfs
#
# CAPITOL_TRADES_URL = "https://www.capitoltrades.com/trades?pageSize=20&format=rss"
# OPENINSIDER_URL    = "http://openinsider.com/rss?type=buys-only&minval=100000"
#
# SECTOR_MAP = {
#     "defense":    ["ITA", "XAR"],
#     "energy":     ["XLE", "IEO"],
#     "tech":       ["QQQ", "SOXX"],
#     ...
# }
#
# def scan_capitol_trades(seen_data):
#     ... (full implementation ready, re-enable when access available)
#
# def scan_openinsider(seen_data):
#     ... (full implementation ready, re-enable when access available)


def scan_capitol_trades(seen_data):
    """Blocked — 403 on GitHub Actions cloud IPs. Returns empty list."""
    # print("Capitol Trades: blocked (403) — skipping")
    return []


def scan_openinsider(seen_data):
    """Blocked — 403 on GitHub Actions cloud IPs. Returns empty list."""
    # print("OpenInsider: blocked (403) — skipping")
    return []
