"""
portfolio.py — Stocazzo v8
Real broker-style virtual portfolio.

Design:
  - One position per ticker (aggregated, not one per signal)
  - Cash tracked explicitly — positions deduct from cash on open, return on close
  - SELL signal on open LONG  → closes the long first
  - BUY  signal on open SHORT → closes the short first
  - Same direction + under cap → adds to existing position
  - New ticker → opens fresh position
  - P&L calculated against live market price at time of check/close
  - All state persists in seen_signals.json["position_book"]
"""
import requests
from datetime import datetime, timezone
from config import TWELVEDATA_KEY, FINNHUB_KEY
from helpers import now_utc_iso, now_be

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
TOTAL_CAPITAL  = 100_000.0  # EUR, never changes
BASE_STAKE     = 1_000.0    # low confidence position size
MAX_STAKE      = 5_000.0    # high confidence position size
MAX_ALLOCATION = 0.10       # max 10% of capital per ticker
HIT_THRESHOLD  = 2.0        # % move = HIT
ROLLING_WINDOW = 20         # positions for rolling hit rate
CHECK_WINDOWS  = [4, 24, 120]


# ── PRICE FETCH ───────────────────────────────────────────────────────────────
def get_price(ticker):
    """Fetch live price — Twelve Data primary, Finnhub fallback."""
    if TWELVEDATA_KEY:
        try:
            r = requests.get(
                "https://api.twelvedata.com/price",
                params={"symbol": ticker, "apikey": TWELVEDATA_KEY},
                timeout=6,
            )
            if r.status_code == 200:
                p = float(r.json().get("price", 0) or 0)
                if p: return round(p, 4)
        except Exception:
            pass
    if FINNHUB_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}",
                timeout=5,
            )
            if r.status_code == 200:
                p = float(r.json().get("c", 0) or 0)
                if p: return round(p, 4)
        except Exception:
            pass
    return 0.0


def _market_is_open():
    """Mon–Fri 13:00–20:30 UTC."""
    n = datetime.now(timezone.utc)
    if n.weekday() >= 5: return False
    h = n.hour + n.minute / 60
    return 13.0 <= h <= 20.5


# ── BOOK INIT ─────────────────────────────────────────────────────────────────
def _get_book(seen_data):
    """Return position book with all keys guaranteed."""
    book = seen_data.setdefault("position_book", {})
    book.setdefault("cash",          TOTAL_CAPITAL)
    book.setdefault("total_capital", TOTAL_CAPITAL)
    book.setdefault("positions",     {})
    book.setdefault("closed",        [])
    book.setdefault("realised_pnl",  0.0)
    ps = book.setdefault("platform_score", {})
    ps.setdefault("total_hits",  0)
    ps.setdefault("total_misses",0)
    ps.setdefault("total_pnl",   0.0)
    ps.setdefault("by_window",   {})
    ps.setdefault("by_theme",    {})
    ps.setdefault("rolling",     [])
    for w in ["4h","24h","5d"]:
        ww = ps["by_window"].setdefault(w, {})
        ww.setdefault("hits",0); ww.setdefault("misses",0); ww.setdefault("pnl",0.0)
    return book


def _stake(confidence):
    if confidence >= 75: return MAX_STAKE
    elif confidence >= 55: return 2_500.0
    return BASE_STAKE


# ── OPEN / ADD POSITION ───────────────────────────────────────────────────────
def open_position(advice_card, seen_data):
    """Open a new position or add to / flip an existing one."""
    direction = advice_card.get("direction", "WATCH").upper()
    if "WATCH" in direction:
        return

    etfs = advice_card.get("etfs", [])
    if not etfs:
        return

    ticker     = etfs[0][0]
    side       = "LONG" if "BUY" in direction else "SHORT"
    book       = _get_book(seen_data)
    cash       = book["cash"]
    pos_map    = book["positions"]
    confidence = advice_card.get("confidence", 50)
    stake      = _stake(confidence)
    max_cap    = TOTAL_CAPITAL * MAX_ALLOCATION
    uid        = advice_card.get("uid", "")
    theme      = advice_card.get("theme", "")

    entry_price = get_price(ticker)
    if not entry_price:
        print(f"  Portfolio: no price for {ticker} — skipping")
        return

    # ── Existing position ─────────────────────────────────────────────────────
    if ticker in pos_map:
        pos = pos_map[ticker]

        if pos["side"] != side:
            # Opposite signal → close existing, then open new below
            cp = get_price(ticker) or entry_price
            _close(ticker, pos, cp, book, "opposite_signal")
            print(f"  Portfolio: closed {pos['side']} {ticker} @ ${cp:.2f} (opposite signal)")
            cash = book["cash"]  # refreshed after close
        else:
            # Same direction → add if headroom available
            if pos["invested_eur"] >= max_cap:
                print(f"  Portfolio: {ticker} at max allocation — skipping add")
                return
            add = min(stake, max_cap - pos["invested_eur"], cash)
            if add < 100:
                print(f"  Portfolio: insufficient cash/headroom for {ticker}")
                return
            new_shares       = add / entry_price
            total_shares     = pos["shares"] + new_shares
            pos["avg_entry"] = round(
                (pos["avg_entry"] * pos["shares"] + entry_price * new_shares) / total_shares, 4
            )
            pos["shares"]       = round(total_shares, 6)
            pos["invested_eur"] = round(pos["invested_eur"] + add, 2)
            if uid: pos["signals"].append(uid)
            if theme and theme not in pos["themes"]: pos["themes"].append(theme)
            book["cash"] = round(cash - add, 2)
            print(f"  Portfolio: added to {side} {ticker} @ ${entry_price:.2f} (+€{add:.0f})")
            return

    # ── New position ──────────────────────────────────────────────────────────
    stake = min(stake, cash, max_cap)
    if stake < 100:
        print(f"  Portfolio: insufficient cash (€{cash:.0f}) for {ticker}")
        return

    pos_map[ticker] = {
        "side":         side,
        "ticker":       ticker,
        "shares":       round(stake / entry_price, 6),
        "avg_entry":    entry_price,
        "invested_eur": round(stake, 2),
        "open_date":    now_utc_iso(),
        "open_be":      now_be(),
        "signals":      [uid] if uid else [],
        "themes":       [theme] if theme else [],
        "confidence":   confidence,
        "check_4h":     None,
        "check_24h":    None,
    }
    book["cash"] = round(cash - stake, 2)
    print(f"  Portfolio: opened {side} {ticker} @ ${entry_price:.2f} (€{stake:.0f}, {confidence}% conf)")


# ── CLOSE POSITION ────────────────────────────────────────────────────────────
def _close(ticker, pos, close_price, book, reason):
    """Close a position at close_price. Returns closed record."""
    if pos["side"] == "LONG":
        pnl_pct = (close_price - pos["avg_entry"]) / pos["avg_entry"] * 100
    else:
        pnl_pct = (pos["avg_entry"] - close_price) / pos["avg_entry"] * 100

    pnl_eur    = round(pos["invested_eur"] * pnl_pct / 100, 2)
    open_dt    = datetime.fromisoformat(pos["open_date"].replace("Z","+00:00"))
    hold_hours = round((datetime.now(timezone.utc) - open_dt).total_seconds() / 3600, 1)

    rec = {
        "ticker":       ticker,
        "side":         pos["side"],
        "shares":       pos["shares"],
        "avg_entry":    pos["avg_entry"],
        "close_price":  close_price,
        "invested_eur": pos["invested_eur"],
        "pnl_eur":      pnl_eur,
        "pnl_pct":      round(pnl_pct, 2),
        "open_date":    pos["open_date"],
        "open_be":      pos.get("open_be",""),
        "close_date":   now_utc_iso(),
        "close_be":     now_be(),
        "hold_hours":   hold_hours,
        "signals":      pos.get("signals",[]),
        "themes":       pos.get("themes",[]),
        "close_reason": reason,
        "hit":          pnl_pct >= HIT_THRESHOLD,
    }
    book["closed"].append(rec)
    book["realised_pnl"] = round(book.get("realised_pnl",0.0) + pnl_eur, 2)
    book["cash"]         = round(book.get("cash",0.0) + pos["invested_eur"] + pnl_eur, 2)
    book["positions"].pop(ticker, None)
    return rec


# ── UPDATE CHECKS ─────────────────────────────────────────────────────────────
def update_positions(seen_data):
    """Check open positions, record snapshots, close at 5d. Returns newly closed."""
    if not _market_is_open():
        print("  Portfolio: market closed — skipping price checks")
        return []

    book    = _get_book(seen_data)
    pos_map = book["positions"]
    if not pos_map:
        return []

    now    = datetime.now(timezone.utc)
    closed = []

    for ticker, pos in list(pos_map.items()):
        try:
            open_dt = datetime.fromisoformat(pos["open_date"].replace("Z","+00:00"))
            hours   = (now - open_dt).total_seconds() / 3600
        except Exception:
            continue

        price = get_price(ticker)
        if not price:
            continue

        if pos["side"] == "LONG":
            pct = (price - pos["avg_entry"]) / pos["avg_entry"] * 100
        else:
            pct = (pos["avg_entry"] - price) / pos["avg_entry"] * 100
        eur = round(pos["invested_eur"] * pct / 100, 2)
        hit = pct >= HIT_THRESHOLD

        snap = {"price": price, "pct": round(pct,2), "pnl_eur": eur, "date": now_utc_iso(), "hit": hit}

        if hours >= 4 and pos.get("check_4h") is None:
            pos["check_4h"] = snap
            print(f"  Portfolio 4h:  {ticker} {pos['side']} {pct:+.1f}% (€{eur:+.0f}) {'HIT' if hit else 'MISS'}")
            _score(book, "4h", hit, eur, pos.get("themes",[]))

        if hours >= 24 and pos.get("check_24h") is None:
            pos["check_24h"] = snap
            print(f"  Portfolio 24h: {ticker} {pos['side']} {pct:+.1f}% (€{eur:+.0f}) {'HIT' if hit else 'MISS'}")
            _score(book, "24h", hit, eur, pos.get("themes",[]))

        if hours >= 120:
            rec = _close(ticker, pos, price, book, "5d_checkpoint")
            print(f"  Portfolio 5d (closed): {ticker} {rec['side']} {rec['pnl_pct']:+.1f}% (€{rec['pnl_eur']:+.0f}) {'HIT' if rec['hit'] else 'MISS'}")
            _score(book, "5d", rec["hit"], rec["pnl_eur"], rec.get("themes",[]))
            _rolling(book, rec)
            closed.append(rec)

    return closed


# ── SCORE HELPERS ─────────────────────────────────────────────────────────────
def _score(book, window, hit, pnl, themes):
    ps = book["platform_score"]
    if hit: ps["total_hits"]   += 1
    else:   ps["total_misses"] += 1
    ps["total_pnl"] = round(ps.get("total_pnl",0.0) + pnl, 2)
    w = ps["by_window"].setdefault(window, {"hits":0,"misses":0,"pnl":0.0})
    w.setdefault("hits",0); w.setdefault("misses",0); w.setdefault("pnl",0.0)
    if hit: w["hits"] += 1
    else:   w["misses"] += 1
    w["pnl"] = round(w["pnl"] + pnl, 2)
    for t in (themes or []):
        th = ps["by_theme"].setdefault(t, {"hits":0,"misses":0,"pnl":0.0})
        th.setdefault("hits",0); th.setdefault("misses",0); th.setdefault("pnl",0.0)
        if hit: th["hits"] += 1
        else:   th["misses"] += 1
        th["pnl"] = round(th["pnl"] + pnl, 2)


def _rolling(book, rec):
    ps = book["platform_score"]
    r  = ps.setdefault("rolling", [])
    r.append({"hit":rec["hit"],"pnl":rec["pnl_eur"],"pct":rec["pnl_pct"],
              "theme":(rec.get("themes") or ["unknown"])[0],"ticker":rec["ticker"]})
    ps["rolling"] = r[-ROLLING_WINDOW:]


# ── SUMMARY ───────────────────────────────────────────────────────────────────
def get_portfolio_summary(seen_data):
    """Full portfolio summary for page_builder."""
    book   = _get_book(seen_data)
    cash   = book["cash"]
    pos_map= book["positions"]
    ps     = book["platform_score"]
    market = _market_is_open()

    positions_out = []
    unrealised    = 0.0

    for ticker, pos in pos_map.items():
        if market:
            price = get_price(ticker) or pos["avg_entry"]
        else:
            price = pos["avg_entry"]

        if pos["side"] == "LONG":
            pct = (price - pos["avg_entry"]) / pos["avg_entry"] * 100
        else:
            pct = (pos["avg_entry"] - price) / pos["avg_entry"] * 100
        eur = round(pos["invested_eur"] * pct / 100, 2)
        unrealised += eur

        positions_out.append({
            **pos,
            "current_price": price,
            "pnl_pct":       round(pct, 2),
            "pnl_eur":       eur,
        })

    invested    = sum(p["invested_eur"] for p in pos_map.values())
    total_value = cash + invested + unrealised
    total_pnl   = book["realised_pnl"] + unrealised
    pnl_pct     = total_pnl / book["total_capital"] * 100

    rolling     = ps.get("rolling", [])
    hit_rate    = (sum(1 for r in rolling if r["hit"]) / len(rolling) * 100) if rolling else 0.0

    by_theme  = ps.get("by_theme", {})
    best_theme = max(
        by_theme.items(),
        key=lambda x: x[1].get("hits",0) / max(x[1].get("hits",0)+x[1].get("misses",0),1),
        default=(None,{})
    )[0]

    return {
        "cash":             round(cash, 2),
        "invested":         round(invested, 2),
        "total_value":      round(total_value, 2),
        "total_capital":    book["total_capital"],
        "unrealised_pnl":   round(unrealised, 2),
        "realised_pnl":     round(book["realised_pnl"], 2),
        "total_pnl":        round(total_pnl, 2),
        "total_pnl_pct":    round(pnl_pct, 2),
        "open_positions":   positions_out,
        "closed_positions": book["closed"][-50:],
        "n_open":           len(pos_map),
        "n_closed":         len(book["closed"]),
        "rolling_hit_rate": round(hit_rate, 1),
        "rolling_n":        len(rolling),
        "best_theme":       best_theme,
        "market_open":      market,
        "platform_score":   ps,
    }


# ── LEGACY SHIMS ──────────────────────────────────────────────────────────────
def _ensure_score(seen_data):
    return _get_book(seen_data)["platform_score"]

def get_platform_score(seen_data):
    return _get_book(seen_data)["platform_score"]

def _update_platform_score(seen_data, checks):
    """Legacy: called by old main.py. Now a no-op — score updated inline."""
    pass
