"""
output/analysts.py — Stocazzo v7
The analyst panel: 5 virtual analysts, each with their own lens.
Each analyst aggregates signals from their assigned sources,
produces a verdict (BULLISH/BEARISH/NEUTRAL) with conviction level,
and votes on the final advice.

Replaces the abstract theme/score system with a human-readable panel.
"""
from collections import defaultdict
from helpers import now_utc, now_be, make_id, urgency_color
from config import SOURCE_CREDIBILITY
from etf_mapper import get_etfs, etf_yahoo_url

# ── ANALYST DEFINITIONS ───────────────────────────────────────────────────────
ANALYSTS = {
    "insider": {
        "name":        "The Insider",
        "emoji":       "🕵",
        "tagline":     "Follows the money before the news",
        "sources":     ["Polymarket", "Kalshi", "Dark Pool", "SEC EDGAR", "Options Flow", "Lobbying", "Gov Contracts"],
        "weight":      5,
        "description": "Watches prediction markets, dark pool flow and insider filings. If something is moving before the news — he sees it first.",
    },
    "trump":  {
        "name":        "The Trump Whisperer",
        "emoji":       "📢",
        "tagline":     "Reads the president's posts in real time",
        "sources":     ["Truth Social"],
        "weight":      4,
        "description": "Monitors Truth Social for market-moving language. Historically 15-30 min ahead of announcements.",
    },
    "congress": {
        "name":        "The Congresswatcher",
        "emoji":       "🏛",
        "tagline":     "Tracks political trades and lobbying",
        "sources":     ["Congress", "Pelosi Tracker"],
        "weight":      3,
        "description": "Follows STOCK Act disclosures and Pelosi trades. Always 45 days delayed but reveals sector conviction.",
    },
    "macro": {
        "name":        "The Macro Man",
        "emoji":       "🌍",
        "tagline":     "Geopolitics, rates and economic trends",
        "sources":     ["Macro RSS", "GDELT", "Social Signal"],
        "weight":      3,
        "description": "Aggregates Reuters, FT, ECB, Fed and geopolitical news. Slower but broader context.",
    },
    "sentiment": {
        "name":        "The Tape Reader",
        "emoji":       "📊",
        "tagline":     "Market mood and crowd psychology",
        "sources":     ["Fear & Greed", "Options Flow", "Social Signal"],
        "weight":      2,
        "description": "Reads market sentiment, options flow and Fear & Greed. Contrarian at extremes.",
    },
}

# Conviction thresholds
HIGH_CONVICTION   = 65   # score % to be HIGH conviction
MEDIUM_CONVICTION = 40   # score % to be MEDIUM conviction

# Verdict weights for final advice
VERDICT_WEIGHTS = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}


# ── BUILD ANALYST VERDICTS ────────────────────────────────────────────────────
def build_analyst_panel(all_alerts, seen_data):
    """
    Each analyst reviews signals from their sources and forms a verdict.
    Returns list of analyst verdict dicts + final panel advice.
    """
    verdicts = []

    for analyst_id, analyst in ANALYSTS.items():
        # Collect signals for this analyst
        my_signals = [
            a for a in all_alerts
            if a.get("source", "") in analyst["sources"]
        ]

        verdict = _analyst_verdict(analyst_id, analyst, my_signals, seen_data)
        verdicts.append(verdict)

    # Panel vote → final advice
    panel_advice = _panel_vote(verdicts, all_alerts)

    return verdicts, panel_advice


def _analyst_verdict(analyst_id, analyst, signals, seen_data):
    """One analyst reviews their signals and forms a verdict."""
    if not signals:
        return {
            "id":         analyst_id,
            "name":       analyst["name"],
            "emoji":      analyst["emoji"],
            "tagline":    analyst["tagline"],
            "description": analyst["description"],
            "weight":     analyst["weight"],
            "verdict":    "NEUTRAL",
            "conviction": 0,
            "conviction_label": "No data",
            "top_signal": None,
            "signal_count": 0,
            "etfs":       [],
            "rationale":  "No signals from my sources in this run.",
            "sources_used": [],
        }

    # Score signals
    bull_score = 0
    bear_score = 0
    top_signal = None
    top_score  = 0
    sources_used = set()
    etf_votes  = defaultdict(int)

    for sig in signals:
        src      = sig.get("source", "")
        urgency  = sig.get("urgency", "LOW")
        direction = sig.get("direction", "").upper()
        cred     = SOURCE_CREDIBILITY.get(src, {})
        w        = cred.get("weight", 1)
        u        = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(urgency, 1)
        points   = w * u

        is_bull = any(x in direction for x in ["BUY","YES","BULLISH","ACCUM"])
        is_bear = any(x in direction for x in ["SELL","NO","BEARISH","REDUCE"])

        if is_bull:
            bull_score += points
        elif is_bear:
            bear_score += points

        sources_used.add(src)

        # Track top signal
        if points > top_score:
            top_score  = points
            top_signal = sig

        # ETF votes
        for t, n, e in sig.get("etfs", []):
            etf_votes[t] += points

    total = bull_score + bear_score
    if total == 0:
        net_pct = 0
    else:
        net_pct = int((bull_score - bear_score) / total * 100) if total else 0

    # Determine verdict
    if bull_score > bear_score * 1.5:
        verdict = "BULLISH"
    elif bear_score > bull_score * 1.5:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    # Conviction
    conviction = min(95, abs(net_pct))
    if conviction >= HIGH_CONVICTION:
        conviction_label = "HIGH conviction"
    elif conviction >= MEDIUM_CONVICTION:
        conviction_label = "MEDIUM conviction"
    else:
        conviction_label = "LOW conviction"

    # Top ETFs
    top_etfs = sorted(etf_votes.items(), key=lambda x: -x[1])[:3]

    # Rationale
    rationale = _build_rationale(analyst_id, signals, verdict, bull_score, bear_score, top_signal)

    return {
        "id":               analyst_id,
        "name":             analyst["name"],
        "emoji":            analyst["emoji"],
        "tagline":          analyst["tagline"],
        "description":      analyst["description"],
        "weight":           analyst["weight"],
        "verdict":          verdict,
        "conviction":       conviction,
        "conviction_label": conviction_label,
        "top_signal":       top_signal,
        "signal_count":     len(signals),
        "etfs":             [t for t, _ in top_etfs],
        "rationale":        rationale,
        "sources_used":     list(sources_used),
        "bull_score":       bull_score,
        "bear_score":       bear_score,
    }


def _build_rationale(analyst_id, signals, verdict, bull, bear, top):
    """
    Build a plain-English rationale for the analyst's verdict.
    Tells the user WHAT the signal is about, not just counts.
    """
    if not signals:
        return "No signals from my sources in this run."

    bull_sigs = [s for s in signals if any(x in s.get("direction","").upper() for x in ["BUY","YES","BULLISH"])]
    bear_sigs = [s for s in signals if any(x in s.get("direction","").upper() for x in ["SELL","NO","BEARISH"])]

    # Extract the meaningful content from the top signal
    top_title  = top.get("title", "")[:80] if top else ""
    top_src    = top.get("source", "") if top else ""
    top_etfs   = [t for t, _, _ in (top.get("etfs") or [])][:2] if top else []
    top_urgency = top.get("urgency", "") if top else ""
    etf_str    = ", ".join(top_etfs) if top_etfs else ""

    # Build direction sentence
    if verdict == "BULLISH":
        direction_str = f"{len(bull_sigs)} bullish signal{'s' if len(bull_sigs)!=1 else ''}"
        if bear_sigs:
            direction_str += f" vs {len(bear_sigs)} bearish"
    elif verdict == "BEARISH":
        direction_str = f"{len(bear_sigs)} bearish signal{'s' if len(bear_sigs)!=1 else ''}"
        if bull_sigs:
            direction_str += f" vs {len(bull_sigs)} bullish"
    else:
        direction_str = f"mixed signals ({len(bull_sigs)} up, {len(bear_sigs)} down)"

    base = direction_str + "."

    # Add meaningful content about what the signal is actually about
    if top_title and top_src:
        # Don't just quote the title — explain what it means
        urgency_note = f" [{top_urgency} urgency]" if top_urgency == "HIGH" else ""
        etf_note     = f" — watch {etf_str}" if etf_str else ""
        base += f" Strongest signal: {top_src}: \"{top_title}\"{urgency_note}{etf_note}."

    return base


# ── PANEL VOTE ────────────────────────────────────────────────────────────────
def _panel_vote(verdicts, all_alerts):
    """
    Weighted vote across all analysts.
    Returns final panel advice dict.
    """
    bull_weight = 0
    bear_weight = 0
    voting      = []

    for v in verdicts:
        if v["verdict"] == "BULLISH" and v["conviction"] >= MEDIUM_CONVICTION:
            bull_weight += v["weight"] * (v["conviction"] / 100)
            voting.append((v["name"], "BULLISH", v["conviction"]))
        elif v["verdict"] == "BEARISH" and v["conviction"] >= MEDIUM_CONVICTION:
            bear_weight += v["weight"] * (v["conviction"] / 100)
            voting.append((v["name"], "BEARISH", v["conviction"]))

    total_weight = bull_weight + bear_weight
    if total_weight == 0:
        direction   = "NEUTRAL"
        confidence  = 0
        action      = "WATCH"
        action_color = "#b06000"
    elif bull_weight > bear_weight:
        direction    = "BULLISH"
        confidence   = min(90, int(bull_weight / total_weight * 100))
        action       = "BUY / ACCUMULATE"
        action_color = "#007a5e"
    else:
        direction    = "BEARISH"
        confidence   = min(90, int(bear_weight / total_weight * 100))
        action       = "REDUCE / HEDGE"
        action_color = "#cc2222"

    # Collect top ETFs from bullish analysts
    etf_votes = defaultdict(int)
    for v in verdicts:
        if v["verdict"] == direction or direction == "NEUTRAL":
            for t in v["etfs"]:
                etf_votes[t] += v["weight"]
    top_etfs = [t for t, _ in sorted(etf_votes.items(), key=lambda x: -x[1])[:4]]

    # Build panel summary — explicit: WHAT, WHY, ACTION, RISK
    active_analysts  = [v for v in verdicts if v["verdict"] in ("BULLISH","BEARISH") and v["conviction"] >= MEDIUM_CONVICTION]
    abstained        = [v["name"] for v in verdicts if v["verdict"] == "NEUTRAL" and v["signal_count"] == 0]
    active_count     = len(active_analysts)
    total_count      = len(verdicts)

    # Collect thesis signals from active analysts — the real content
    thesis_signals = []
    for v in verdicts:
        if v["verdict"] == direction and v.get("top_signal"):
            t     = v["top_signal"]
            src   = t.get("source", "")
            title = t.get("title", "")[:70]
            if title:
                thesis_signals.append(f"{src}: {title}")

    # Sector focus from ETFs
    etf_to_sector = {
        "XLE": "energy", "IEO": "energy", "XOM": "energy", "CVX": "energy",
        "ITA": "defense", "LMT": "defense", "RTX": "defense",
        "GLD": "gold/safe-haven", "IGLN": "gold/safe-haven",
        "QQQ": "tech", "SOXX": "semiconductors",
        "TLT": "bonds/rates", "LIT": "critical minerals",
        "COPX": "critical minerals", "IBIT": "crypto",
        "SPY": "broad market", "EEM": "emerging markets",
    }
    sectors = list(dict.fromkeys(
        etf_to_sector.get(e, e) for e in top_etfs if e in etf_to_sector
    ))
    sector_str   = " + ".join(sectors[:2]) if sectors else "mixed"
    etf_str      = ", ".join(top_etfs[:3]) if top_etfs else "no specific ETF"
    bull_names   = [n for n, d, _ in voting if d == "BULLISH"]
    bear_names   = [n for n, d, _ in voting if d == "BEARISH"]

    # Confidence correction: penalise low panel participation
    active_voting = len(active_analysts)
    if active_voting < 2:
        confidence = min(confidence, 40)
    elif active_voting < 3:
        confidence = min(confidence, 65)

    # Build structured summary
    all_quiet = active_count == 0

    if all_quiet:
        # Nothing firing — keep it short
        summary = "All sources quiet this scan. No position changes."
    elif direction == "BULLISH":
        who_line    = f"{len(bull_names)} analyst{'s' if len(bull_names)!=1 else ''} bullish: {', '.join(bull_names)}."
        action_line = f"Consider: BUY {etf_str} ({sector_str})."
        why_line    = ("Driven by: " + " · ".join(thesis_signals[:2]) + ".") if thesis_signals else ""
        parts = [who_line, action_line]
        if why_line: parts.append(why_line)
        if abstained: parts.append(f"{active_count}/{total_count} analysts active — {', '.join(abstained[:2])} had no data.")
        summary = " ".join(parts)
    elif direction == "BEARISH":
        who_line    = f"{len(bear_names)} analyst{'s' if len(bear_names)!=1 else ''} bearish: {', '.join(bear_names)}."
        action_line = f"Consider: REDUCE / hedge {sector_str}. Watch: {etf_str}."
        why_line    = ("Driven by: " + " · ".join(thesis_signals[:2]) + ".") if thesis_signals else ""
        parts = [who_line, action_line]
        if why_line: parts.append(why_line)
        if abstained: parts.append(f"{active_count}/{total_count} analysts active — {', '.join(abstained[:2])} had no data.")
        summary = " ".join(parts)
    else:
        # NEUTRAL with some data but no conviction
        if abstained and active_count < 3:
            summary = f"Conflicting signals — no clear direction. {active_count}/{total_count} analysts had data."
        else:
            summary = "Mixed signals across sources — no actionable conviction. Monitor for confirmation."

    return {
        "direction":    direction,
        "action":       action,
        "action_color": action_color,
        "confidence":   confidence,
        "summary":      summary,
        "top_etfs":     top_etfs,
        "bull_weight":  round(bull_weight, 1),
        "bear_weight":  round(bear_weight, 1),
        "voting":       voting,
        "generated_be": now_be(),
    }


# ── HTML RENDERING ────────────────────────────────────────────────────────────
def format_panel_html(verdicts, panel_advice):
    """Renders the full analyst panel as HTML for live.html."""

    # ── PANEL VERDICT ─────────────────────────────────────────────────────────
    ac   = panel_advice["action_color"]
    conf = panel_advice["confidence"]
    cc   = "#007a5e" if conf >= 65 else "#b06000" if conf >= 45 else "#888"
    bar  = conf

    etf_badges = "".join(
        f'<a href="https://finance.yahoo.com/quote/{t}" target="_blank" '
        f'style="background:#e8f4f0;color:#007a5e;font-family:monospace;font-size:11px;'
        f'font-weight:700;padding:2px 8px;border-radius:3px;text-decoration:none;margin-right:4px;">{t}</a>'
        for t in panel_advice["top_etfs"]
    )

    panel_html = (
        f"<div style='background:var(--surface);border:2px solid {ac};border-radius:6px;"
        f"padding:16px;margin-bottom:16px;'>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;'>"
        f"<span style='background:{ac};color:#fff;font-family:monospace;font-size:12px;"
        f"font-weight:700;padding:4px 14px;border-radius:4px;'>{panel_advice['action']}</span>"
        f"<span style='font-size:15px;font-weight:500;color:var(--text);'>Panel verdict</span>"
        f"<span style='font-family:monospace;font-size:11px;color:var(--muted);margin-left:auto;'>"
        f"{panel_advice['generated_be'][:16]}</span>"
        f"</div>"
        f"<div style='font-size:13px;color:var(--text);margin-bottom:10px;line-height:1.7;"
        f"border-left:3px solid {ac};padding-left:10px;'>"
        f"{panel_advice['summary']}</div>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>"
        f"<div style='background:#e0e0d8;border-radius:2px;height:6px;flex:1;'>"
        f"<div style='background:{cc};height:6px;border-radius:2px;width:{bar}%;'></div></div>"
        f"<span style='font-family:monospace;font-size:12px;color:{cc};font-weight:600;'>{conf}%</span>"
        f"</div>"
        f"<div>{etf_badges}</div>"
        f"</div>"
    )

    # ── ANALYST CARDS ──────────────────────────────────────────────────────────
    cards_html = "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:0;'>"

    for v in verdicts:
        verdict   = v["verdict"]
        conv      = v["conviction"]
        vc        = "#007a5e" if verdict == "BULLISH" else "#cc2222" if verdict == "BEARISH" else "#888"
        vbg       = "#e8f4f0" if verdict == "BULLISH" else "#fce8e8" if verdict == "BEARISH" else "#f5f5f0"
        conv_bar  = conv
        conv_c    = "#007a5e" if conv >= HIGH_CONVICTION else "#b06000" if conv >= MEDIUM_CONVICTION else "#aaa"

        # ETF badges for this analyst
        analyst_etfs = "".join(
            f'<a href="https://finance.yahoo.com/quote/{t}" target="_blank" '
            f'style="background:#f0f0eb;color:#444;font-family:monospace;font-size:10px;'
            f'font-weight:700;padding:1px 6px;border-radius:3px;text-decoration:none;margin-right:3px;">{t}</a>'
            for t in v["etfs"][:3]
        ) if v["etfs"] else ""

        top = v.get("top_signal")
        top_snippet = ""
        if top:
            src   = top.get("source","")
            title = top.get("title","")[:70]
            top_snippet = (
                f"<div style='font-size:11px;color:var(--muted);border-left:2px solid var(--border2);"
                f"padding-left:8px;margin-top:6px;line-height:1.5;font-style:italic;'>"
                f"[{src}] {title}</div>"
            )

        cards_html += (
            f"<div style='background:var(--surface);border:1px solid var(--border);"
            f"border-radius:4px;padding:12px;border-top:3px solid {vc};'>"
            f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:6px;'>"
            f"<span style='font-size:16px;'>{v['emoji']}</span>"
            f"<div>"
            f"<div style='font-size:13px;font-weight:600;color:var(--text);'>{v['name']}</div>"
            f"<div style='font-size:10px;color:var(--muted);font-style:italic;'>{v['tagline']}</div>"
            f"</div>"
            f"<span style='margin-left:auto;background:{vbg};color:{vc};font-family:monospace;"
            f"font-size:11px;font-weight:700;padding:2px 8px;border-radius:3px;'>{verdict}</span>"
            f"</div>"
            f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:6px;'>"
            f"<div style='background:#e0e0d8;border-radius:2px;height:3px;flex:1;'>"
            f"<div style='background:{conv_c};height:3px;border-radius:2px;width:{conv_bar}%;'></div></div>"
            f"<span style='font-family:monospace;font-size:10px;color:{conv_c};'>{v['conviction_label']}</span>"
            f"</div>"
            f"<div style='font-size:13px;color:var(--muted);margin-bottom:10px;line-height:1.6;'>{v['rationale']}</div>"
            f"{top_snippet}"
            f"<div style='margin-top:6px;'>{analyst_etfs}</div>"
            f"<div style='font-size:10px;color:var(--dim);font-family:monospace;margin-top:6px;'>"
            f"{v['signal_count']} signals · {', '.join(v['sources_used'][:3])}</div>"
            f"</div>"
        )

    cards_html += "</div>"

    return panel_html + cards_html
