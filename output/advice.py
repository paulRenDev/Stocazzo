"""
output/advice.py — Stocazzo v7
The cumulative advice engine.
Takes ALL signals from ALL sources, groups by theme, weights by credibility,
and produces ranked actionable advice cards with bull/bear scenarios.

This is the core of the system: not individual signals, but cumulated knowledge.
"""
from collections import defaultdict
from datetime import datetime, timezone

from config import SOURCE_CREDIBILITY, SITE_URL
from helpers import make_id, now_utc, now_be, urgency_color
from etf_mapper import get_etfs, ETF_MAP, etf_yahoo_url, etf_google_url

# ── SOURCE WEIGHTS FOR ADVICE ─────────────────────────────────────────────────
# Crony sources = higher weight (signal BEFORE the news)
# Macro sources = lower weight (signal AFTER the news)
ADVICE_WEIGHTS = {
    # Crony (pre-news) — highest weight
    "Polymarket":     5,
    "Kalshi":         5,
    "Truth Social":   4,  # fastest real-time signal
    "SEC EDGAR":      4,  # insider Form 3/4/5
    "Pelosi Tracker": 4,
    "Congress":       3,
    "Dark Pool":      3,
    "Gov Contracts":  3,  # defense contract wins
    "Options Flow":   2,
    "Lobbying":       2,
    # Macro (post-news) — lower weight, broader context
    "GDELT":          2,
    "Macro RSS":      2,
    "Fear & Greed":   2,
    "Social Signal":  1,
    # Convergence bonus
    "CONVERGENCE":    6,
}

# Urgency multipliers
URGENCY_MULT = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

# Theme → ETF mapping for advice (richer than signal-level ETFs)
THEME_ETF_MAP = {
    "energy":      [("XLE","Energy Select SPDR","NYSE"), ("IEO","Oil & Gas E&P","NYSE"), ("USO","US Oil Fund","NYSE")],
    "defense":     [("ITA","Aerospace & Defense","NYSE"), ("XAR","SPDR Defense","NYSE"), ("LMT","Lockheed Martin","NYSE")],
    "fed":         [("TLT","20yr Treasury","NASDAQ"), ("IEF","7-10yr Treasury","NASDAQ"), ("GLD","SPDR Gold","NYSE")],
    "trade":       [("IWDA","MSCI World","AMS"), ("EEM","Emerging Markets","NYSE"), ("GLD","SPDR Gold","NYSE")],
    "tech":        [("QQQ","Nasdaq-100","NASDAQ"), ("SOXX","Semiconductors","NASDAQ"), ("NVDA","NVIDIA","NASDAQ")],
    "crypto":      [("IBIT","Bitcoin Trust","NASDAQ"), ("COIN","Coinbase","NASDAQ")],
    "commodities": [("GLD","SPDR Gold","NYSE"), ("IGLN","Physical Gold","AMS"), ("GSG","Commodity Index","NYSE")],
    "macro":       [("SPY","S&P 500","NYSE"), ("IWDA","MSCI World","AMS"), ("TLT","20yr Treasury","NASDAQ")],
    "risk_on":     [("SPY","S&P 500","NYSE"), ("QQQ","Nasdaq-100","NASDAQ"), ("IWDA","MSCI World","AMS")],
    "risk_off":    [("GLD","SPDR Gold","NYSE"), ("TLT","20yr Treasury","NASDAQ"), ("IGLN","Physical Gold","AMS")],
}

# Bull/bear scenario templates per theme
SCENARIOS = {
    "energy": {
        "bull": "Oil supply disruption or geopolitical escalation → XLE/IEO up. Entry on dip before news confirmation.",
        "bear": "Ceasefire or demand destruction → oil oversupply. Reduce energy exposure.",
    },
    "defense": {
        "bull": "Conflict escalation or NATO spending increase → defense contractors surge. ITA historically +15-20% in escalation cycles.",
        "bear": "Peace deal or budget cuts → defense drawdown. Rotate out before announcement.",
    },
    "fed": {
        "bull": "Rate cut signal → TLT rallies. Bonds and gold benefit. Risk-on if economy healthy.",
        "bear": "Hawkish surprise or inflation data → TLT drops. Short duration, hold cash.",
    },
    "trade": {
        "bull": "Trade deal or tariff pause → broad market rally. IWDA/SPY immediate beneficiary.",
        "bear": "New tariffs or trade war escalation → EM and global trade hurt. Rotate to domestic.",
    },
    "tech": {
        "bull": "Chip demand surge or AI spending → SOXX/QQQ. NVDA often leads by 2-3 sessions.",
        "bear": "Export ban or China restrictions → semis hit hard. Reduce before policy announcement.",
    },
    "crypto": {
        "bull": "Regulatory clarity or ETF news → IBIT/COIN surge. Trump crypto-friendly = positive catalyst.",
        "bear": "Regulatory crackdown or exchange collapse → crypto -30%+. Exit before SEC action.",
    },
    "macro": {
        "bull": "Soft landing confirmed, inflation falling → broad market rally. Overweight equities.",
        "bear": "Recession signals or credit event → defensive positioning. Gold, bonds, cash.",
    },
    "commodities": {
        "bull": "Dollar weakness or inflation spike → gold outperforms. Safe haven in uncertainty.",
        "bear": "Strong dollar or risk-on rally → gold underperforms. Rotate to equities.",
    },
}


def build_advice(all_alerts, seen_data):
    """
    Main function: takes all alerts from all sources,
    groups by theme, weights by source credibility,
    and returns ranked advice cards.
    """
    if not all_alerts:
        return []

    # Step 1: Group signals by theme
    theme_signals = defaultdict(list)
    for alert in all_alerts:
        themes = _detect_themes(alert)
        for theme in themes:
            theme_signals[theme].append(alert)

    # Step 2: Score each theme
    theme_scores = {}
    for theme, signals in theme_signals.items():
        score, direction, sources, confidence = _score_theme(theme, signals, seen_data)
        if score >= 3:  # minimum threshold to generate advice
            theme_scores[theme] = {
                "score":      score,
                "direction":  direction,
                "sources":    sources,
                "confidence": confidence,
                "signals":    signals,
            }

    if not theme_scores:
        return []

    # Step 3: Build advice cards, sorted by score
    advice_cards = []
    for theme, data in sorted(theme_scores.items(), key=lambda x: -x[1]["score"]):
        card = _build_advice_card(theme, data, seen_data)
        if card:
            advice_cards.append(card)

    return advice_cards[:6]  # top 6 advice cards


def _detect_themes(alert):
    """Detect which themes an alert belongs to."""
    themes = set()
    text = (
        alert.get("title", "") + " " +
        alert.get("detail", "") + " " +
        alert.get("keywords", "") + " " +
        " ".join(e[0] for e in alert.get("etfs", []))
    ).lower()

    theme_keywords = {
        "energy":      ["oil", "gas", "energy", "opec", "xle", "ieo", "uso", "crude", "lng"],
        "defense":     ["defense", "defence", "military", "war", "nato", "lmt", "rtx", "ita", "aerospace"],
        "fed":         ["fed", "rate", "interest", "tlt", "bonds", "ecb", "powell", "lagarde", "pivot"],
        "trade":       ["tariff", "trade", "china", "sanctions", "wto", "import", "export"],
        "tech":        ["semiconductor", "chip", "nvidia", "nvda", "soxx", "qqq", "ai", "tech", "tsm"],
        "crypto":      ["crypto", "bitcoin", "ibit", "coin", "btc", "ethereum"],
        "commodities": ["gold", "silver", "gld", "igln", "copper", "gdx"],
        "macro":       ["gdp", "inflation", "cpi", "recession", "jobs", "unemployment", "spy", "iwda"],
    }

    for theme, keywords in theme_keywords.items():
        if any(kw in text for kw in keywords):
            themes.add(theme)

    # Direction-based themes
    direction = alert.get("direction", "").upper()
    if any(w in direction for w in ["BUY", "YES", "BULLISH", "ACCUM"]):
        themes.add("risk_on")
    elif any(w in direction for w in ["SELL", "NO", "BEARISH", "REDUCE"]):
        themes.add("risk_off")

    return list(themes) if themes else ["macro"]


def _score_theme(theme, signals, seen_data):
    """
    Score a theme based on all signals pointing to it.
    Returns (score, direction, sources_list, confidence).
    """
    total_score  = 0
    bull_votes   = 0
    bear_votes   = 0
    sources_seen = {}

    for sig in signals:
        source  = sig.get("source", "")
        urgency = sig.get("urgency", "LOW")

        # Dedup by source — one vote per source
        if source in sources_seen:
            continue
        sources_seen[source] = sig

        weight = ADVICE_WEIGHTS.get(source, 1)
        mult   = URGENCY_MULT.get(urgency, 1)

        # Hit rate bonus
        from scoring import get_source_hit_rate
        hit_rate, n = get_source_hit_rate(source, {})
        hr_bonus = round(hit_rate * 2) if hit_rate else 0

        points = weight * mult + hr_bonus
        total_score += points

        # Direction vote
        direction = sig.get("direction", "").upper()
        if any(w in direction for w in ["BUY", "YES", "BULLISH", "ACCUM"]):
            bull_votes += weight
        elif any(w in direction for w in ["SELL", "NO", "BEARISH", "REDUCE", "HEDGE"]):
            bear_votes += weight

    # Determine overall direction
    if bull_votes > bear_votes:
        direction = "BUY"
    elif bear_votes > bull_votes:
        direction = "SELL / REDUCE"
    else:
        direction = "WATCH"

    # Confidence: capped at 90%, based on score and source diversity
    n_sources  = len(sources_seen)
    confidence = min(90, int(total_score * 6 + n_sources * 5))

    return total_score, direction, list(sources_seen.keys()), confidence


def _build_advice_card(theme, data, seen_data):
    """Build a single advice card for a theme."""
    score      = data["score"]
    direction  = data["direction"]
    sources    = data["sources"]
    confidence = data["confidence"]
    signals    = data["signals"]

    # Get ETFs for this theme
    etfs = THEME_ETF_MAP.get(theme, get_etfs(theme))
    if not etfs:
        etfs = get_etfs(theme)

    # Get scenarios
    scenario = SCENARIOS.get(theme, {
        "bull": f"Positive momentum in {theme} sector. Consider ETF exposure.",
        "bear": f"Negative signals in {theme} sector. Consider reducing exposure.",
    })

    # Determine action
    if "BUY" in direction:
        action       = "BUY / ACCUMULATE"
        action_color = "#007a5e"
        active_scenario = scenario["bull"]
    elif "SELL" in direction:
        action       = "REDUCE / HEDGE"
        action_color = "#cc2222"
        active_scenario = scenario["bear"]
    else:
        action       = "WATCH"
        action_color = "#b06000"
        active_scenario = f"Mixed signals on {theme}. Monitor before acting."

    # Build rationale from actual signals
    source_summaries = []
    for sig in signals[:4]:
        src = sig.get("source", "")
        ttl = sig.get("title", "")[:60]
        d   = sig.get("direction", "")
        source_summaries.append(f"{src} [{d}]: {ttl}")

    rationale = f"{len(sources)} independent sources aligned on {theme}. " + \
                " | ".join(source_summaries[:2])

    # Urgency based on score
    urgency = "HIGH" if score >= 15 else "MEDIUM" if score >= 7 else "LOW"

    uid = make_id(f"advice-{theme}-{now_utc()[:13]}")

    return {
        "theme":          theme,
        "action":         action,
        "action_color":   action_color,
        "direction":      direction,
        "score":          score,
        "confidence":     confidence,
        "urgency":        urgency,
        "sources":        sources,
        "n_sources":      len(sources),
        "etfs":           etfs[:3],
        "rationale":      rationale,
        "active_scenario": active_scenario,
        "bull_case":      scenario["bull"],
        "bear_case":      scenario["bear"],
        "uid":            uid,
        "generated_at":   now_utc(),
        "signals":        signals,
    }



def _scenarios_html(card):
    """Show bull+bear for WATCH, only relevant scenario for BUY/SELL."""
    direction = card.get("direction", "WATCH")
    is_buy    = "BUY" in direction
    is_sell   = "SELL" in direction or "REDUCE" in direction
    is_watch  = not is_buy and not is_sell

    if is_watch:
        # Show both — no clear direction
        return (
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;'>"
            f"<div style='background:#e8f4f0;border-radius:4px;padding:8px 10px;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#007a5e;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;'>Bull case</div>"
            f"<div style='font-size:11px;color:#1a5e4a;line-height:1.5;'>{card['bull_case']}</div></div>"
            f"<div style='background:#fce8e8;border-radius:4px;padding:8px 10px;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#cc2222;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;'>Bear case</div>"
            f"<div style='font-size:11px;color:#8b1a1a;line-height:1.5;'>{card['bear_case']}</div></div>"
            f"</div>"
        )
    elif is_buy:
        # Show bull case + bear case as risk only
        return (
            f"<div style='display:grid;grid-template-columns:2fr 1fr;gap:8px;margin-bottom:10px;'>"
            f"<div style='background:#e8f4f0;border-radius:4px;padding:8px 10px;"
            f"border-left:3px solid #007a5e;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#007a5e;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;'>Bull case (active)</div>"
            f"<div style='font-size:11px;color:#1a5e4a;line-height:1.5;font-weight:500;'>{card['bull_case']}</div></div>"
            f"<div style='background:#f8f8f4;border-radius:4px;padding:8px 10px;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#9a9a9a;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;'>Risk / bear</div>"
            f"<div style='font-size:11px;color:#9a9a9a;line-height:1.5;'>{card['bear_case']}</div></div>"
            f"</div>"
        )
    else:
        # Show bear case + bull case as risk only
        return (
            f"<div style='display:grid;grid-template-columns:2fr 1fr;gap:8px;margin-bottom:10px;'>"
            f"<div style='background:#fce8e8;border-radius:4px;padding:8px 10px;"
            f"border-left:3px solid #cc2222;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#cc2222;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;'>Bear case (active)</div>"
            f"<div style='font-size:11px;color:#8b1a1a;line-height:1.5;font-weight:500;'>{card['bear_case']}</div></div>"
            f"<div style='background:#f8f8f4;border-radius:4px;padding:8px 10px;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#9a9a9a;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;'>Risk / bull</div>"
            f"<div style='font-size:11px;color:#9a9a9a;line-height:1.5;'>{card['bull_case']}</div></div>"
            f"</div>"
        )


def format_advice_html_section(advice_cards):
    """
    Renders advice cards as HTML for embedding in live.html.
    Returns HTML string.
    """
    if not advice_cards:
        return (
            "<div style='text-align:center;color:var(--muted);font-family:var(--mono);"
            "font-size:12px;padding:2rem;background:var(--surface);border:1px solid var(--border);"
            "border-radius:4px;'>No actionable advice at this time — "
            "signals present but below confidence threshold</div>"
        )

    cards_html = ""
    for card in advice_cards:
        ac    = card["action_color"]
        conf  = card["confidence"]
        cc    = "#007a5e" if conf >= 65 else "#b06000" if conf >= 45 else "#cc2222"
        c     = urgency_color(card["urgency"])

        etf_badges = "".join(
            f'<a href="{etf_yahoo_url(t,e)}" style="background:#e8f4f0;color:#007a5e;'
            f'font-family:monospace;font-size:11px;font-weight:700;padding:2px 8px;'
            f'border-radius:3px;text-decoration:none;margin-right:4px;" target="_blank">{t}</a>'
            for t, n, e in card["etfs"]
        )

        source_pills = "".join(
            f'<span style="font-family:monospace;font-size:10px;background:#f0f0eb;'
            f'color:#6b6b6b;padding:2px 7px;border-radius:3px;margin-right:3px;">{s}</span>'
            for s in card["sources"][:5]
        )

        cards_html += f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:4px;
          padding:16px;margin-bottom:12px;border-left:3px solid {ac};">

          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <span style="background:{ac};color:#fff;font-family:monospace;font-size:11px;
              font-weight:700;padding:3px 10px;border-radius:3px;">{card['action']}</span>
            <span style="font-size:13px;font-weight:600;color:var(--text);text-transform:capitalize;">
              {card['theme'].replace('_',' ')}</span>
            <span style="font-size:10px;font-family:monospace;padding:2px 8px;border-radius:10px;
              background:{c}20;color:{c};font-weight:600;">{card['urgency']}</span>
            <span style="font-size:10px;font-family:monospace;color:var(--muted);margin-left:auto;">
              {card['n_sources']} sources · score {card['score']}</span>
          </div>

          <div style="font-size:13px;color:var(--muted);margin-bottom:10px;line-height:1.6;
            border-left:2px solid var(--border2);padding-left:10px;">
            {card['active_scenario']}
          </div>

          {_scenarios_html(card)}

          <div style="margin-bottom:8px;">{etf_badges}</div>

          <div style="display:flex;align-items:center;justify-content:space-between;
            padding-top:8px;border-top:1px solid var(--border2);flex-wrap:wrap;gap:6px;">
            <div>{source_pills}</div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="background:#e8e8e0;border-radius:2px;height:4px;width:60px;">
                <div style="background:{cc};height:4px;border-radius:2px;width:{conf}%;"></div>
              </div>
              <span style="font-family:monospace;font-size:11px;color:{cc};">{conf}%</span>
            </div>
          </div>
        </div>"""

    return cards_html


def log_advice_for_scoring(advice_cards, seen_data):
    """
    Logs advice cards to pending_checks for backcheck.
    Uses first ETF as the tracked instrument.
    """
    from scoring import get_price, now_utc_iso
    from helpers import now_utc_iso

    pending = seen_data.setdefault("advice_checks", [])
    existing = {p["uid"] for p in pending}

    for card in advice_cards:
        if card["uid"] in existing:
            continue
        if not card["etfs"]:
            continue

        ticker = card["etfs"][0][0]
        price  = get_price(ticker)

        pending.append({
            "uid":             card["uid"],
            "theme":           card["theme"],
            "action":          card["action"],
            "direction":       card["direction"],
            "ticker":          ticker,
            "score":           card["score"],
            "confidence":      card["confidence"],
            "sources":         card["sources"],
            "date":            now_utc_iso(),
            "price_at_signal": price,
            # Backcheck timestamps
            "check_4h":        None,
            "check_24h":       None,
            "check_5d":        None,
            "result_4h":       None,
            "result_24h":      None,
            "result_5d":       None,
        })

    seen_data["advice_checks"] = pending[-200:]  # keep last 200


def run_advice_backcheck(seen_data):
    """
    Runs backcheck on logged advice cards at 4h, 24h and 5d intervals.
    Updates platform score.
    """
    from scoring import get_price
    from helpers import now_utc_iso

    pending = seen_data.get("advice_checks", [])
    if not pending:
        return seen_data, []

    now     = datetime.now(timezone.utc)
    results = []

    for check in pending:
        try:
            signal_date = datetime.fromisoformat(check.get("date", now.isoformat()))
        except Exception:
            continue

        hours_ago = (now - signal_date).total_seconds() / 3600
        ticker    = check.get("ticker", "")
        if not ticker:
            continue

        direction = check.get("direction", "").upper()
        is_buy    = "BUY" in direction
        is_sell   = "SELL" in direction or "REDUCE" in direction

        price_now = get_price(ticker)
        if not price_now:
            continue

        entry = check.get("price_at_signal", 0)
        if not entry:
            continue

        pct = ((price_now - entry) / entry) * 100
        hit = (pct > 2) if is_buy else (pct < -2) if is_sell else None

        # 4h check
        if hours_ago >= 4 and check.get("result_4h") is None:
            check["check_4h"]  = now_utc_iso()
            check["result_4h"] = {"pct": round(pct, 2), "hit": hit, "price": price_now}
            results.append({**check, "window": "4h", "pct": round(pct, 2), "hit": hit})

        # 24h check
        if hours_ago >= 24 and check.get("result_24h") is None:
            check["check_24h"]  = now_utc_iso()
            check["result_24h"] = {"pct": round(pct, 2), "hit": hit, "price": price_now}
            results.append({**check, "window": "24h", "pct": round(pct, 2), "hit": hit})

        # 5d check
        if hours_ago >= 120 and check.get("result_5d") is None:
            check["check_5d"]  = now_utc_iso()
            check["result_5d"] = {"pct": round(pct, 2), "hit": hit, "price": price_now}
            results.append({**check, "window": "5d", "pct": round(pct, 2), "hit": hit})

    # Update platform score
    _update_platform_score(seen_data, results)

    return seen_data, results


def _update_platform_score(seen_data, results):
    """Maintains a running platform accuracy score."""
    score = seen_data.setdefault("platform_score", {
        "hits": 0, "misses": 0, "watches": 0,
        "by_window": {"4h": {"hits":0,"misses":0}, "24h": {"hits":0,"misses":0}, "5d": {"hits":0,"misses":0}},
        "by_theme":  {},
    })

    for r in results:
        hit    = r.get("hit")
        window = r.get("window", "5d")
        theme  = r.get("theme", "unknown")

        if hit is True:
            score["hits"] += 1
            score["by_window"][window]["hits"] += 1
        elif hit is False:
            score["misses"] += 1
            score["by_window"][window]["misses"] += 1
        else:
            score["watches"] += 1

        if theme not in score["by_theme"]:
            score["by_theme"][theme] = {"hits": 0, "misses": 0}
        if hit is True:
            score["by_theme"][theme]["hits"] += 1
        elif hit is False:
            score["by_theme"][theme]["misses"] += 1
