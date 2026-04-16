"""
convergence.py — CronyPony v7
Multi-source scoring engine. Combines signals from different sources.
Transparent scoring: every point explained.
"""
from collections import defaultdict

from config import SOURCE_CREDIBILITY, CONVERGENCE_MIN_SCORE, CONVERGENCE_HIGH_SCORE, SITE_URL
from helpers import make_id, now_utc
from etf_mapper import get_etfs


def build_convergence(alerts, seen_data):
    """
    Compares signals from different sources.
    Returns a convergence alert if score >= CONVERGENCE_MIN_SCORE.

    Score per source = source_weight + urgency_weight + (hit_rate x 2)
    Convergence fires when 2+ sources point to the same ticker/theme.
    """
    if len(alerts) < 2:
        return None

    # Build ticker → signals map
    ticker_signals = defaultdict(list)
    for a in alerts:
        for t, n, e in a.get("etfs", []):
            ticker_signals[t].append(a)
        for kw in a.get("keywords", "").split(","):
            kw = kw.strip().upper()
            if 2 <= len(kw) <= 5 and kw.isalpha():
                ticker_signals[kw].append(a)

    best_ticker    = None
    best_score     = 0
    best_signals   = []
    best_breakdown = []

    for ticker, sigs in ticker_signals.items():
        # Deduplicate by source
        by_source = {}
        for s in sigs:
            src = s.get("source", "")
            if src not in by_source:
                by_source[src] = s
        unique = list(by_source.values())

        if len(unique) < 2:
            continue

        score      = 0
        breakdown  = []
        directions = []

        for s in unique:
            src       = s.get("source", "")
            urgency   = s.get("urgency", "LOW")
            sw        = SOURCE_CREDIBILITY.get(src, {}).get("weight", 1)
            uw        = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(urgency, 1)
            cr        = SOURCE_CREDIBILITY.get(src, {}).get("historical_hit_rate") or 0.5
            points    = sw + uw + round(cr * 2)
            score    += points

            d = s.get("direction", "").upper()
            if any(w in d for w in ["BUY", "YES", "ACCUM", "BULLISH"]):
                directions.append("BUY")
            elif any(w in d for w in ["SELL", "NO", "REDUCE", "HEDGE", "BEARISH"]):
                directions.append("SELL")

            breakdown.append({
                "source":    src,
                "direction": s.get("direction", ""),
                "urgency":   urgency,
                "points":    points,
                "reasoning": f"weight={sw} + urgency={uw} + hit_rate={cr:.0%}x2 = {points}pts",
                "signal":    s.get("title", "")[:60],
            })

        if score > best_score:
            best_score     = score
            best_ticker    = ticker
            best_signals   = unique
            best_breakdown = breakdown

    if best_score < CONVERGENCE_MIN_SCORE or not best_signals:
        return None

    buy_count  = directions.count("BUY")
    sell_count = directions.count("SELL")

    if buy_count > sell_count:
        conv_dir    = "BUY"
        conv_color  = "#007a5e"
        conv_action = "BUY"
        conv_advice = f"{buy_count}/{len(best_signals)} sources bullish on {best_ticker}"
    elif sell_count > buy_count:
        conv_dir    = "SELL"
        conv_color  = "#cc2222"
        conv_action = "REDUCE / HEDGE"
        conv_advice = f"{sell_count}/{len(best_signals)} sources bearish on {best_ticker}"
    else:
        conv_dir    = "MIXED"
        conv_color  = "#b06000"
        conv_action = "WATCH"
        conv_advice = f"Sources split on {best_ticker} — no clear direction"

    uid  = make_id(f"convergence-{best_ticker}-{now_utc()[:13]}")
    etfs = get_etfs(best_ticker.lower())
    if not etfs:
        for s in best_signals:
            if s.get("etfs"):
                etfs = s["etfs"]
                break

    confidence = min(95, best_score * 8)

    return {
        "source":    "CONVERGENCE",
        "type":      f"{len(best_signals)} sources · score {best_score}",
        "direction": conv_dir,
        "title":     f"[{len(best_signals)}x CONVERGENCE] {best_ticker} — {conv_dir}",
        "detail":    (
            f"Score: {best_score}pts across {len(best_signals)} independent sources: "
            f"{', '.join(s.get('source') for s in best_signals)}"
        ),
        "link":      SITE_URL,
        "keywords":  best_ticker,
        "etfs":      etfs,
        "urgency":   "HIGH" if best_score >= CONVERGENCE_HIGH_SCORE else "MEDIUM",
        "uid":       uid,
        "reasoning": {
            "why":           conv_advice,
            "signal_type":   "Multi-source convergence — strongest signal type",
            "confidence":    confidence,
            "source_weight": 5,
            "hit_rate":      "No historical data yet for convergence signals",
            "caveat":        "Convergence != certainty. Check macro context before acting.",
            "breakdown":     best_breakdown,
        },
        "_conv_action": conv_action,
        "_conv_advice": conv_advice,
        "_conv_color":  conv_color,
    }
