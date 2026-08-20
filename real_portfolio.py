"""
real_portfolio.py — Paul's actual ME-DIRECT holdings.

Source of truth: real_holdings.json (repo root), pushed automatically from the
"Aandelen" Google Sheet by a Google Apps Script (see docs/portfolio_sync.gs).
Falls back to a hand-entered snapshot (taken 20/08/2026) if that file is
missing, so the tool still runs before the sheet sync is set up.

Theme tags are a judgment call the sheet can't make, so they live here,
keyed by ticker, and get merged onto whatever holdings the JSON feed reports.
No scan logic, no state.
"""
import json
import os

REAL_HOLDINGS_FILE = os.path.join(os.path.dirname(__file__), "real_holdings.json")

# ── FALLBACK SNAPSHOT (20/08/2026, from "PORTEFEUILLE" table) ────────────────
# Used only if real_holdings.json doesn't exist yet.
_FALLBACK_HOLDINGS = [
    {"ticker": "HLTW", "name": "Amundi MSCI World Health Care UCITS ETF", "exchange": "EPA", "currency": "EUR", "shares": 1},
    {"ticker": "COSW", "name": "Amundi S&P World Consumer Staples Screened UCITS ETF", "exchange": "EPA", "currency": "EUR", "shares": 45},
    {"ticker": "NUCL", "name": "VanEck Uranium and Nuclear Technologies UCITS ETF", "exchange": "EPA", "currency": "EUR", "shares": 10},
    {"ticker": "IWVL", "name": "iShares Edge MSCI World Value Factor UCITS ETF", "exchange": "LON", "currency": "USD", "shares": 12},
    {"ticker": "IWDA", "name": "iShares Core MSCI World UCITS ETF", "exchange": "AMS", "currency": "EUR", "shares": 21},
]

# ── THEME TAGS PER TICKER ──────────────────────────────────────────────────────
# Vocabulary matches the theme buckets used by scanners/macro.py and
# scanners/news_feeds.py: energy, defense, fed, trade, tech, crypto,
# commodities, macro, finance, merger. A few extra tags (healthcare,
# consumer_staples, aerospace, infrastructure) are included for completeness
# even though no scanner currently produces signals in those buckets.
THEME_TAGS_BY_TICKER = {
    "IWDA":   ["macro", "trade", "fed", "tech", "finance"],   # broad MSCI World — exposed to everything
    "IWVL":   ["macro", "fed", "finance"],                     # value factor tilt
    "HLTW":   ["healthcare"],
    "COSW":   ["consumer_staples"],
    "NUCL":   ["energy", "commodities"],                       # uranium/nuclear
    "TWEKA":  ["tech", "infrastructure"],                      # TKH Group
    "EVS":    ["tech"],                                        # EVS Broadcast Equipment
    "HO":     ["defense"],                                     # Thales
    "SPCX":   ["aerospace", "tech"],                           # SpaceX
    "IOGP":   ["energy"],
}
DEFAULT_THEME_TAGS = ["macro"]

# Individual stock positions bought in 2026 that don't appear in the sheet's
# auto-updating "PORTEFEUILLE DETAIL" ETF table — verify these are still held
# before trusting the advice on them. Only used in the fallback snapshot;
# once real_holdings.json exists it should reflect these correctly.
_UNVERIFIED_STOCK_HOLDINGS = [
    {"ticker": "TWEKA", "name": "TKH Group NV", "exchange": "AMS", "currency": "EUR", "shares": 1},
    {"ticker": "EVS", "name": "EVS Broadcast Equipment SA", "exchange": "EBR", "currency": "EUR", "shares": 1},
    {"ticker": "HO", "name": "Thales SA", "exchange": "EPA", "currency": "EUR", "shares": 1},
    {"ticker": "SPCX", "name": "Space Exploration Technologies Corp (SpaceX)", "exchange": "NASDAQ", "currency": "USD", "shares": 1},
]

YAHOO_SUFFIX = {"AMS": ".AS", "EPA": ".PA", "EBR": ".BR", "LON": ".L", "PAR": ".PA", "BRU": ".BR", "LSE": ".L"}


def yahoo_symbol(holding):
    """Yahoo Finance-compatible symbol for live price lookups."""
    suffix = YAHOO_SUFFIX.get(holding.get("exchange", ""), "")
    return f"{holding['ticker']}{suffix}"


def load_holdings():
    """
    Returns the current holdings list: [{ticker, name, exchange, currency,
    shares, theme_tags}, ...]. Reads real_holdings.json if present, else
    falls back to the hand-entered snapshot + unverified stock positions.
    """
    holdings = None
    if os.path.exists(REAL_HOLDINGS_FILE):
        try:
            with open(REAL_HOLDINGS_FILE) as f:
                data = json.load(f)
            holdings = data.get("holdings", [])
        except Exception as e:
            print(f"real_portfolio: could not read {REAL_HOLDINGS_FILE}: {e}")

    if not holdings:
        holdings = _FALLBACK_HOLDINGS + _UNVERIFIED_STOCK_HOLDINGS

    for h in holdings:
        h["theme_tags"] = THEME_TAGS_BY_TICKER.get(h["ticker"], DEFAULT_THEME_TAGS)

    return holdings


MY_HOLDINGS = load_holdings()
