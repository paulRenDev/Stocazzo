"""
scanners/darkpool.py — CronyPony v7
Institutional dark pool flow via Whalestream.
Standalone test: python -m scanners.darkpool
"""
import re

from config import DARK_POOL_TICKERS, SOURCE_CREDIBILITY
from helpers import safe_get, make_id, now_utc
from etf_mapper import get_etfs
from state import is_seen, mark_seen
from scoring import format_hit_rate


def scan_dark_pool(seen_data):
    alerts = []
    try:
        from bs4 import BeautifulSoup
        r = safe_get("https://www.whalestream.com/market-data/top-dark-pool-flow")
        if not r or len(r.text) < 500:
            print("Dark Pool: unreachable")
            return alerts

        soup    = BeautifulSoup(r.text, "html.parser")
        text    = soup.get_text(" ").upper()
        matched = [t for t in DARK_POOL_TICKERS if re.search(r'\b' + re.escape(t) + r'\b', text)]

        if not matched:
            print("Dark Pool: no watchlist tickers found")
            return alerts

        volumes       = re.findall(r'\$([0-9.]+[BM])', text)
        total_vol_str = volumes[0] if volumes else "unknown"

        print(f"Dark Pool: {len(matched)} tickers — {', '.join(matched[:6])}")

        # UID per day to prevent same-day duplicates
        uid = make_id(f"darkpool-{now_utc()[:10]}-{'-'.join(sorted(matched[:5]))}")
        if is_seen(uid, seen_data):
            print("Dark Pool: same tickers as before — skipping")
            return alerts

        broad     = [t for t in matched if t in ["SPY", "QQQ", "IWM"]]
        sector    = [t for t in matched if t not in ["SPY", "QQQ", "IWM", "TLT", "HYG"]]
        direction = "ACCUMULATION" if broad else "SECTOR FLOW"

        why = (
            f"Broad market tickers ({', '.join(broad)}) in dark pool = institutions buying ahead of announcement"
            if broad
            else f"Sector flow in {', '.join(sector[:3])} = possible positioning"
        )

        alerts.append({
            "source":    "Dark Pool",
            "type":      "Institutional Flow",
            "direction": direction,
            "title":     f"Dark pool: {', '.join(matched[:5])}",
            "detail":    (
                f"Institutional dark pool activity. Total volume: {total_vol_str}. "
                f"{'Broad market = possible accumulation before announcement.' if broad else 'Sector-specific = possible rotation or positioning.'}"
            ),
            "link":      "https://www.whalestream.com/market-data/top-dark-pool-flow",
            "keywords":  ", ".join(matched[:6]),
            "etfs":      get_etfs(" ".join(matched).lower()),
            "urgency":   "MEDIUM",
            "uid":       uid,
            "reasoning": {
                "why":           why,
                "signal_type":   "Dark pool = trades hidden from public order books, typically institutional",
                "confidence":    60,
                "source_weight": SOURCE_CREDIBILITY["Dark Pool"]["weight"],
                "hit_rate":      format_hit_rate("Dark Pool", seen_data),
                "caveat":        "No directional info — dark pools can be buy OR sell. Needs confirmation.",
            },
        })
        mark_seen(uid, seen_data)

    except Exception as e:
        print(f"Dark Pool error: {e}")

    return alerts


if __name__ == "__main__":
    from state import load_seen
    seen = load_seen()
    alerts = scan_dark_pool(seen)
    for a in alerts:
        print(f"[{a['urgency']}] {a['title'][:80]} — {a['direction']}")
