"""
output/portfolio_advice.py — Stocazzo v8 (post-crony pivot)
Maps geopolitical/macro signals onto Paul's real ME-DIRECT holdings and
produces per-position advice (ACCUMULATE / REDUCE / MONITOR).

Replaces the generic theme-ETF advice (output/advice.py) as the primary
output: instead of "energy theme is bullish, consider XLE", this says
"NUCL (10 shares, your uranium exposure) is bullish on 3 geopolitical
signals" — advice tied to positions Paul actually holds.
"""
from collections import defaultdict

from helpers import make_id, now_utc
from real_portfolio import MY_HOLDINGS, yahoo_symbol
from portfolio import get_price

# GDELT alerts carry a single raw query keyword (e.g. "oil", "china") rather
# than a theme bucket name — normalise those onto the same buckets that
# macro.py / news_feeds.py use in their `keywords` field.
GDELT_THEME_ALIASES = {
    "tariff": "trade", "oil": "energy", "china": "trade",
    "ukraine": "defense", "semiconductor": "tech", "ecb": "fed", "fed": "fed",
}

ACTION_COLORS = {
    "ACCUMULATE":     "#007a5e",
    "REDUCE / HEDGE": "#cc2222",
    "MONITOR":        "#b06000",
}
ACTION_ORDER = {"REDUCE / HEDGE": 0, "ACCUMULATE": 1, "MONITOR": 2}
URGENCY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _alert_themes(alert):
    themes = set()
    for part in alert.get("keywords", "").split(","):
        t = part.strip().lower()
        if t:
            themes.add(GDELT_THEME_ALIASES.get(t, t))
    return themes


def build_portfolio_advice(all_alerts, seen_data):
    """
    Returns advice cards for holdings with at least one matching geopolitical
    signal this run. Holdings with no active signal are omitted — silence on
    a position means nothing geopolitically relevant happened to it.
    """
    signals_by_ticker = defaultdict(list)
    for alert in all_alerts:
        themes = _alert_themes(alert)
        if not themes:
            continue
        for h in MY_HOLDINGS:
            if themes & set(h.get("theme_tags", [])):
                signals_by_ticker[h["ticker"]].append(alert)

    cards = []
    for h in MY_HOLDINGS:
        alerts = signals_by_ticker.get(h["ticker"], [])
        if not alerts:
            continue

        bull = sum(1 for a in alerts if a.get("direction", "").upper() == "BULLISH")
        bear = sum(1 for a in alerts if a.get("direction", "").upper() == "BEARISH")

        if bull > bear:
            action, direction = "ACCUMULATE", "BULLISH"
        elif bear > bull:
            action, direction = "REDUCE / HEDGE", "BEARISH"
        else:
            action, direction = "MONITOR", "MIXED"

        price = get_price(yahoo_symbol(h)) or get_price(h["ticker"]) or 0
        value_eur = round(price * h["shares"], 2) if price else h.get("value_eur")

        top_alerts = sorted(alerts, key=lambda a: URGENCY_ORDER.get(a.get("urgency", "LOW"), 2))[:3]

        cards.append({
            "ticker":        h["ticker"],
            "name":          h["name"],
            "shares":        h["shares"],
            "current_price": price,
            "value_eur":     value_eur,
            "action":        action,
            "action_color":  ACTION_COLORS[action],
            "direction":     direction,
            "n_signals":     len(alerts),
            "bull":          bull,
            "bear":          bear,
            "signals": [
                {
                    "source":    a.get("source", ""),
                    "title":     a.get("title", ""),
                    "direction": a.get("direction", ""),
                    "urgency":   a.get("urgency", ""),
                    "link":      a.get("link", ""),
                }
                for a in top_alerts
            ],
            "uid":          make_id(f"portadvice-{h['ticker']}-{now_utc()[:13]}"),
            "generated_at": now_utc(),
        })

    total_value = sum(c["value_eur"] for c in cards if c["value_eur"]) or None
    for c in cards:
        c["weight_pct"] = round(c["value_eur"] / total_value * 100, 1) if total_value and c["value_eur"] else None

    cards.sort(key=lambda c: (ACTION_ORDER.get(c["action"], 3), -c["n_signals"]))
    return cards


def format_portfolio_advice_html(cards):
    """Renders portfolio advice cards as HTML for the email."""
    if not cards:
        return (
            "<div style='text-align:center;color:#9a9a9a;font-family:monospace;"
            "font-size:12px;padding:24px;'>Geen van je posities heeft deze run een "
            "relevant geopolitiek signaal.</div>"
        )

    rows = ""
    for c in cards:
        ac = c["action_color"]
        weight = f" · {c['weight_pct']}% van portefeuille" if c["weight_pct"] else ""
        value = f"€{c['value_eur']:,.0f}".replace(",", ".") if c["value_eur"] else "onbekend"

        signal_rows = ""
        for s in c["signals"]:
            d_color = "#007a5e" if s["direction"].upper() == "BULLISH" else \
                      "#cc2222" if s["direction"].upper() == "BEARISH" else "#b06000"
            signal_rows += (
                f"<div style='font-size:11px;color:#6b6b6b;margin:3px 0;padding-left:8px;"
                f"border-left:2px solid {d_color};'>"
                f"<span style='font-family:monospace;font-weight:700;color:{d_color};'>{s['source']}</span> "
                f"{s['title'][:90]}</div>"
            )

        rows += (
            f"<tr><td style='padding:14px 16px;border-bottom:1px solid #f0f0eb;'>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;'>"
            f"<span style='background:{ac};color:#fff;font-family:monospace;font-size:11px;"
            f"font-weight:700;padding:2px 10px;border-radius:3px;'>{c['action']}</span>"
            f"<span style='font-size:13px;font-weight:600;color:#1a1a1a;'>{c['ticker']}</span>"
            f"<span style='font-size:12px;color:#6b6b6b;'>{c['name']}</span>"
            f"<span style='font-size:10px;font-family:monospace;color:#9a9a9a;margin-left:auto;'>"
            f"{c['shares']} sh · {value}{weight}</span></div>"
            f"{signal_rows}</td></tr>"
        )

    return f"<table style='width:100%;border-collapse:collapse;'>{rows}</table>"
