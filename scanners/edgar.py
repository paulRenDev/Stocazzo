"""
scanners/edgar.py — Stocazzo v7
Finnhub free tier endpoints:
  - /stock/insider-transactions  (Form 3/4/5 — global coverage)
  - /stock/lobbying               (Senate/House lobbying activities)
  - /stock/usa-spending           (Government contracts — defense/aerospace)
All three require FINNHUB_KEY but are NOT premium — they work from cloud IPs.
Standalone test: python -m scanners.edgar
"""
import requests
from datetime import datetime, timezone, timedelta

from config import FINNHUB_KEY, CONGRESS_KEYWORDS, SOURCE_CREDIBILITY
from helpers import make_id, now_utc
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate

FINNHUB_BASE = "https://finnhub.io/api/v1"

# Tickers to watch for insider transactions
WATCH_TICKERS = [
    # AI / Tech
    "NVDA", "MSFT", "AAPL", "AMZN", "META", "GOOGL", "TSLA", "PLTR", "AVGO", "AMD",
    # Defense
    "LMT", "RTX", "NOC", "GD", "BA", "HII", "LDOS",
    # Energy
    "XOM", "CVX", "COP", "OXY", "SLB",
    # Crypto / Finance
    "COIN", "MSTR", "JPM", "GS",
    # Semis
    "INTC", "TSM", "QCOM", "ASML",
]

# Defense + aerospace tickers for USA spending
DEFENSE_TICKERS = ["LMT", "RTX", "NOC", "GD", "BA", "HII", "LDOS", "SAIC", "CACI", "LEIDOS"]

# Min transaction value to care about (shares * price estimate)
MIN_SHARES = 5_000
LARGE_SHARES = 50_000


def scan_edgar(seen_data):
    alerts = []

    if not FINNHUB_KEY:
        print("SEC/Finnhub: no FINNHUB_KEY")
        return alerts

    alerts += _scan_insider_transactions(seen_data)
    alerts += _scan_lobbying(seen_data)
    alerts += _scan_usa_spending(seen_data)

    return alerts


# ── INSIDER TRANSACTIONS ──────────────────────────────────────────────────────
def _scan_insider_transactions(seen_data):
    """
    Form 3/4/5 insider transactions via Finnhub.
    Leave symbol blank = get latest transactions across all companies.
    """
    alerts = []
    try:
        # Fetch latest transactions (no symbol = all recent)
        r = requests.get(
            f"{FINNHUB_BASE}/stock/insider-transactions",
            params={"token": FINNHUB_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"Insider transactions: HTTP {r.status_code}")
            return alerts

        data   = r.json().get("data", [])
        print(f"Insider transactions: {len(data)} transactions")

        for tx in data[:40]:
            symbol = str(tx.get("symbol", "")).upper()
            if symbol not in WATCH_TICKERS:
                continue

            name        = tx.get("name", "Unknown")
            change      = tx.get("change", 0)      # positive = BUY, negative = SELL
            shares_held = tx.get("share", 0)
            filing_date = tx.get("filingDate", "")
            tx_date     = tx.get("transactionDate", filing_date)

            if abs(change or 0) < MIN_SHARES:
                continue

            uid = make_id(f"insider-{symbol}-{name}-{filing_date}-{change}")
            if is_seen(uid, seen_data):
                continue

            direction  = "BUY" if (change or 0) > 0 else "SELL"
            is_large   = abs(change or 0) >= LARGE_SHARES
            urgency    = "MEDIUM" if is_large else "LOW"

            # Try to determine if this is a C-suite exec
            name_lower = name.lower()
            is_officer = any(t in name_lower for t in ["ceo","cfo","coo","president","chairman","director","chief"])

            if is_officer and is_large:
                urgency = "HIGH"

            alerts.append({
                "source":    "SEC EDGAR",
                "type":      f"Form 4 · {'Officer' if is_officer else 'Insider'}{' · LARGE' if is_large else ''}",
                "direction": direction,
                "title":     f"{name} — {direction} {abs(change or 0):,} shares of {symbol}",
                "detail":    (
                    f"{symbol} insider {direction}. "
                    f"Shares changed: {change:+,} | "
                    f"Total held: {shares_held:,} | "
                    f"Filed: {filing_date}"
                ),
                "link":      f"https://finnhub.io/stock-insider-transactions/{symbol}",
                "keywords":  f"{symbol}, insider, {direction.lower()}",
                "etfs":      get_etfs(symbol.lower()),
                "urgency":   urgency,
                "uid":       uid,
                "reasoning": {
                    "why":           f"{name} filed {direction} of {abs(change or 0):,} {symbol} shares. {'Officer = higher conviction signal.' if is_officer else ''} {'Large position.' if is_large else ''}",
                    "signal_type":   "SEC Form 4 mandatory disclosure — 2 business days reporting lag (much faster than STOCK Act).",
                    "confidence":    65 if (is_officer and is_large) else 50 if is_large else 35,
                    "source_weight": 3,
                    "hit_rate":      format_hit_rate("SEC EDGAR", seen_data),
                    "caveat":        "Sells often = tax/diversification, not conviction. Buys by CEOs/CFOs = stronger signal.",
                },
            })
            mark_seen(uid, seen_data)

    except Exception as e:
        print(f"Insider transactions error: {e}")

    return alerts


# ── LOBBYING ──────────────────────────────────────────────────────────────────
def _scan_lobbying(seen_data):
    """
    Senate/House lobbying activities — large lobbying spend = upcoming regulation or contract.
    """
    alerts = []
    try:
        from_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        to_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Check a focused list of high-value lobbying sectors
        lobby_tickers = ["LMT", "RTX", "NVDA", "MSFT", "COIN", "AMZN", "META", "XOM"]

        for symbol in lobby_tickers:
            try:
                r = requests.get(
                    f"{FINNHUB_BASE}/stock/lobbying",
                    params={"symbol": symbol, "from": from_date, "to": to_date, "token": FINNHUB_KEY},
                    timeout=8,
                )
                if r.status_code != 200:
                    continue

                data     = r.json().get("data", [])
                if not data:
                    continue

                # Sum lobbying spend
                total_spend = sum(
                    float(d.get("expenses", 0) or d.get("income", 0) or 0)
                    for d in data
                )

                if total_spend < 500_000:  # only care about >$500k lobbying
                    continue

                uid = make_id(f"lobbying-{symbol}-{from_date}")
                if is_seen(uid, seen_data):
                    continue

                # Get most recent activity description
                latest      = data[0]
                description = latest.get("description", "")[:100]
                period      = latest.get("period", "")

                print(f"Lobbying: {symbol} spent ${total_spend:,.0f} ({len(data)} filings)")

                alerts.append({
                    "source":    "Lobbying",
                    "type":      f"Senate/House · {symbol}",
                    "direction": "WATCH",
                    "title":     f"{symbol} lobbying: ${total_spend:,.0f} in last 90 days",
                    "detail":    f"{len(data)} lobbying filings. Latest: {description}. Period: {period}",
                    "link":      f"https://finnhub.io/stock-lobbying/{symbol}",
                    "keywords":  f"{symbol}, lobbying, regulation",
                    "etfs":      get_etfs(symbol.lower()),
                    "urgency":   "LOW",
                    "uid":       uid,
                    "reasoning": {
                        "why":           f"{symbol} spent ${total_spend:,.0f} lobbying in 90 days — {len(data)} filings. Large lobbying spend precedes regulatory changes or contract wins.",
                        "signal_type":   "Senate/House lobbying disclosure. High spend = anticipating regulation or government contract.",
                        "confidence":    35,
                        "source_weight": 2,
                        "hit_rate":      format_hit_rate("Lobbying", seen_data),
                        "caveat":        "Lobbying is routine for large companies. Only valuable as sector context, not directional signal.",
                    },
                })
                mark_seen(uid, seen_data)

            except Exception as e:
                print(f"Lobbying {symbol} error: {e}")
                continue

    except Exception as e:
        print(f"Lobbying scanner error: {e}")

    return alerts


# ── USA SPENDING (GOVERNMENT CONTRACTS) ──────────────────────────────────────
def _scan_usa_spending(seen_data):
    """
    Government contracts from USASpending dataset.
    Defense companies winning large contracts = sector catalyst.
    """
    alerts = []
    try:
        from_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for symbol in DEFENSE_TICKERS[:6]:  # limit API calls
            try:
                r = requests.get(
                    f"{FINNHUB_BASE}/stock/usa-spending",
                    params={"symbol": symbol, "from": from_date, "to": to_date, "token": FINNHUB_KEY},
                    timeout=8,
                )
                if r.status_code != 200:
                    continue

                data = r.json().get("data", [])
                if not data:
                    continue

                # Sum contract values
                total_contracts = sum(
                    float(d.get("awardAmount", 0) or 0)
                    for d in data
                )

                if total_contracts < 100_000_000:  # only care about >$100M
                    continue

                uid = make_id(f"spending-{symbol}-{from_date}")
                if is_seen(uid, seen_data):
                    continue

                latest      = data[0]
                description = latest.get("awardDescription", "")[:80]
                agency      = latest.get("agencyName", "")[:60]

                print(f"USA Spending: {symbol} won ${total_contracts/1e6:.0f}M in contracts")

                alerts.append({
                    "source":    "Gov Contracts",
                    "type":      f"USASpending · Defense",
                    "direction": "BULLISH",
                    "title":     f"{symbol} won ${total_contracts/1e6:.0f}M in government contracts",
                    "detail":    f"{len(data)} contracts in last 30 days. Agency: {agency}. Latest: {description}",
                    "link":      f"https://finnhub.io/stock-usa-spending/{symbol}",
                    "keywords":  f"{symbol}, defense, government contract",
                    "etfs":      get_etfs(f"defense aerospace {symbol.lower()}"),
                    "urgency":   "MEDIUM" if total_contracts > 500_000_000 else "LOW",
                    "uid":       uid,
                    "reasoning": {
                        "why":           f"{symbol} received ${total_contracts/1e6:.0f}M in government contracts in 30 days. Agency: {agency}. Large contract = revenue visibility.",
                        "signal_type":   "USASpending government contract disclosure. Defense contracts = recurring revenue catalyst.",
                        "confidence":    55 if total_contracts > 500_000_000 else 40,
                        "source_weight": 2,
                        "hit_rate":      format_hit_rate("Gov Contracts", seen_data),
                        "caveat":        "Contract awards are public but stock reaction depends on whether market already priced it in.",
                    },
                })
                mark_seen(uid, seen_data)

            except Exception as e:
                print(f"USA Spending {symbol} error: {e}")
                continue

    except Exception as e:
        print(f"USA Spending scanner error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_edgar(seen)
    print(f"\nTotal: {len(alerts)} alerts")
    for a in alerts:
        print(f"[{a['urgency']}] [{a['source']}] {a['title'][:80]} — {a['direction']}")
