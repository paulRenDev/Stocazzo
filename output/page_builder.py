"""
output/page_builder.py — Stocazzo v7
Generates live.html, history.html, sources.html and index.html.
No scan logic, no mail logic.
"""
import requests
import re

from config import SOURCE_CREDIBILITY, FINNHUB_KEY, TWELVEDATA_KEY, SITE_URL
from portfolio import get_open_positions, get_closed_positions, get_platform_score
from output.advice import format_advice_html_section
from output.analysts import format_panel_html
from helpers import now_utc, now_be, urgency_color
from etf_mapper import KEY_ETFS, etf_yahoo_url, etf_google_url
from scoring import get_source_hit_rate

# ── SHARED CSS ────────────────────────────────────────────────────────────────
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
:root {
  --bg:#f5f5f0; --surface:#fff; --border:#d8d8d0; --border2:#ebebeb;
  --text:#1a1a1a; --muted:#6b6b6b; --dim:#aaa;
  --green:#007a5e; --red:#cc2222; --amber:#b06000; --blue:#1a5fb5;
  --mono:'IBM Plex Mono',monospace; --sans:'IBM Plex Sans',sans-serif;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--text); font-family:var(--sans); font-size:14px; line-height:1.5; }
.app { max-width:1100px; margin:0 auto; padding:2rem 1.5rem; }
header { border-bottom:1px solid var(--border); padding-bottom:1rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; }
.logo { font-family:var(--mono); font-size:10px; color:var(--green); letter-spacing:0.1em; }
h1 { font-size:22px; font-weight:300; margin-top:4px; }
.nav-link { font-family:var(--mono); font-size:11px; color:var(--blue); text-decoration:none; margin-left:12px; }
.updated { font-size:11px; color:var(--dim); font-family:var(--mono); margin-top:4px; }
.section { margin-bottom:2rem; }
.section-title { font-size:10px; font-family:var(--mono); color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:10px; }
.badge { font-size:10px; font-weight:700; padding:2px 7px; border-radius:3px; font-family:var(--mono); white-space:nowrap; }
.src-polymarket { background:#e8f4f0; color:var(--green); }
.src-kalshi { background:#e8f0f8; color:var(--blue); }
.src-darkpool,.src-dark { background:#f0f0eb; color:#444; }
.src-congress { background:#fdf0e8; color:var(--amber); }
.src-pelositracker { background:#f0e8f8; color:#7a3fb5; }
.src-optionsflow { background:#e8f0f0; color:#1a7a7a; }
.src-socialsignal { background:#f8f0e8; color:#8b4513; }
.src-convergence { background:#1a1a1a; color:#fff; }
.src-truthsocial { background:#fff0e8; color:#c04000; }
.src-secedgar,.src-edgar { background:#f0f4e8; color:#3a6010; }
.src-lobbying { background:#f0e8f4; color:#6030a0; }
.src-govcontracts { background:#e8f0f8; color:#0050a0; }
.src-macrors { background:#f5f5f0; color:#555; }
.src-gdelt { background:#e8f8f8; color:#006070; }
.src-feargreed { background:#fff8e8; color:#804000; }
.mono { font-family:var(--mono); } .small { font-size:11px; } .muted { color:var(--muted); }
.dim { color:var(--dim); } .bold { font-weight:600; }
.green { color:var(--green); } .red { color:var(--red); } .amber { color:var(--amber); }
.etf-badge { background:#e8f4f0; color:var(--green); font-family:var(--mono); font-size:11px; font-weight:700; padding:2px 6px; border-radius:3px; text-decoration:none; margin-right:3px; }
.etf-badge:hover { background:var(--green); color:#fff; }
.stock-badge { background:#f0f0eb; color:#1a1a1a; font-family:var(--mono); font-size:11px; font-weight:700; padding:2px 6px; border-radius:3px; text-decoration:none; margin-right:3px; }
.stock-badge:hover { background:#1a1a1a; color:#fff; }
.conf-mini-wrap { background:#e8e8e0; border-radius:2px; height:3px; width:52px; margin-bottom:2px; }
.conf-mini { height:3px; border-radius:2px; }
@media(max-width:700px) { .etf-grid { grid-template-columns:repeat(2,1fr) !important; } }
"""

# ── LEGEND BAR ────────────────────────────────────────────────────────────────
def _legend_bar():
    return """
    <div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;
      padding:10px 14px;background:var(--surface);border:1px solid var(--border);
      border-radius:4px;margin-bottom:1.5rem;font-size:12px;">
      <span style="font-family:var(--mono);font-size:10px;color:var(--muted);
        text-transform:uppercase;letter-spacing:0.08em;margin-right:4px;">Legend</span>
      <span style="display:flex;align-items:center;gap:5px;">
        <span style="width:10px;height:10px;border-radius:2px;background:#007a5e;display:inline-block;"></span>
        <span style="color:var(--green);font-weight:600;">BUY</span>
        <span style="color:var(--muted);">— signal pointing up</span>
      </span>
      <span style="display:flex;align-items:center;gap:5px;">
        <span style="width:10px;height:10px;border-radius:2px;background:#b06000;display:inline-block;"></span>
        <span style="color:var(--amber);font-weight:600;">WATCH</span>
        <span style="color:var(--muted);">— monitor, no clear direction</span>
      </span>
      <span style="display:flex;align-items:center;gap:5px;">
        <span style="width:10px;height:10px;border-radius:2px;background:#cc2222;display:inline-block;"></span>
        <span style="color:var(--red);font-weight:600;">SELL / REDUCE</span>
        <span style="color:var(--muted);">— signal pointing down</span>
      </span>
      <span style="border-left:1px solid var(--border2);padding-left:20px;display:flex;gap:14px;">
        <span style="display:flex;align-items:center;gap:4px;">
          <span style="width:8px;height:8px;border-radius:50%;background:#cc2222;display:inline-block;"></span>
          <span style="color:var(--muted);">HIGH — act within 30 min</span>
        </span>
        <span style="display:flex;align-items:center;gap:4px;">
          <span style="width:8px;height:8px;border-radius:50%;background:#b06000;display:inline-block;"></span>
          <span style="color:var(--muted);">MEDIUM — verify first</span>
        </span>
        <span style="display:flex;align-items:center;gap:4px;">
          <span style="width:8px;height:8px;border-radius:50%;background:#007a5e;display:inline-block;"></span>
          <span style="color:var(--muted);">LOW — background info</span>
        </span>
      </span>
    </div>"""


# ── EXTRACT STOCKS FROM ALERT ─────────────────────────────────────────────────
def _extract_stocks(alert):
    """Extract individual stock tickers mentioned in an alert."""
    KNOWN_STOCKS = [
        "NVDA","MSFT","AAPL","AMZN","META","GOOGL","TSLA","PLTR","AVGO","AMD",
        "LMT","RTX","NOC","GD","BA","HII",
        "XOM","CVX","COP","OXY","SLB",
        "COIN","MSTR","JPM","GS","BAC",
        "INTC","TSM","QCOM","ASML",
    ]
    text = (
        alert.get("title","") + " " +
        alert.get("detail","") + " " +
        alert.get("keywords","")
    ).upper()

    found = []
    for ticker in KNOWN_STOCKS:
        if re.search(r'\b' + ticker + r'\b', text):
            found.append(ticker)
    return found[:4]



def _portfolio_html(seen_data):
    """Renders broker-style portfolio: summary cards + open positions + closed positions."""
    from portfolio import get_portfolio_summary

    s  = get_portfolio_summary(seen_data)
    th = "font-family:var(--mono);font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);"
    td = "padding:8px 10px;font-size:12px;vertical-align:middle;"
    tdm= td + "font-family:var(--mono);"

    # ── SUMMARY METRIC CARDS ─────────────────────────────────────────────────
    def metric_card(label, value, sub, vc=None):
        vc_style = f"color:{vc};" if vc else ""
        return (
            f"<div style='background:var(--surface);border:1px solid var(--border);"
            f"border-radius:4px;padding:14px 16px;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);"
            f"text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>{label}</div>"
            f"<div style='font-size:22px;font-weight:600;font-family:var(--mono);{vc_style}'>{value}</div>"
            f"<div style='font-size:11px;color:var(--muted);margin-top:3px;'>{sub}</div>"
            f"</div>"
        )

    cash_card = metric_card(
        "Cash available",
        f"€{s['cash']:,.0f}",
        f"{s['cash']/s['total_capital']*100:.1f}% uninvested"
    )
    inv_card = metric_card(
        "Invested",
        f"€{s['invested']:,.0f}",
        f"{s['n_open']} position{'s' if s['n_open']!=1 else ''} open"
    )
    unreal_pnl = s["unrealised_pnl"]
    unreal_sub  = "market closed" if not s["market_open"] else f"{'+'if unreal_pnl>=0 else ''}€{unreal_pnl:.0f} unrealised"
    unreal_card = metric_card(
        "Unrealised P&amp;L",
        f"{'+'if unreal_pnl>=0 else ''}€{unreal_pnl:.0f}",
        unreal_sub,
        "var(--green)" if unreal_pnl >= 0 else "var(--red)"
    )
    real_pnl  = s["realised_pnl"]
    real_card = metric_card(
        "Realised P&amp;L",
        f"{'+'if real_pnl>=0 else ''}€{real_pnl:.0f}",
        f"{s['n_closed']} closed position{'s' if s['n_closed']!=1 else ''}",
        "var(--green)" if real_pnl >= 0 else "var(--red)"
    )

    summary_row = (
        f"<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;'>"
        f"{cash_card}{inv_card}{unreal_card}{real_card}"
        f"</div>"
    )

    # ── SECOND ROW: hit rate + total value + best theme ───────────────────────
    roll_n    = s["rolling_n"]
    roll_rate = s["rolling_hit_rate"]
    roll_hits = round(roll_n * roll_rate / 100) if roll_n else 0
    bar_c     = "#007a5e" if roll_rate >= 60 else "#b06000" if roll_rate >= 40 else "#cc2222"

    if roll_n:
        hit_rate_card = (
            f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:14px 16px;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;'>Rolling hit rate</div>"
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<div style='flex:1;height:6px;background:#e0e0d8;border-radius:3px;'>"
            f"<div style='width:{roll_rate}%;height:6px;background:{bar_c};border-radius:3px;'></div></div>"
            f"<span style='font-size:18px;font-weight:600;font-family:var(--mono);color:{bar_c};'>{roll_rate:.0f}%</span>"
            f"</div>"
            f"<div style='font-size:11px;color:var(--muted);margin-top:4px;'>{roll_hits} / {roll_n} closed positions</div>"
            f"</div>"
        )
    else:
        hit_rate_card = (
            f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:14px 16px;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;'>Rolling hit rate</div>"
            f"<div style='font-size:12px;color:var(--muted);font-family:var(--mono);'>Builds after first 5-day checks</div>"
            f"</div>"
        )

    total_v   = s["total_value"]
    total_pnl = s["total_pnl"]
    total_pct = s["total_pnl_pct"]
    pnl_c     = "var(--green)" if total_pnl >= 0 else "var(--red)"
    total_card = (
        f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:14px 16px;'>"
        f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>Total portfolio value</div>"
        f"<div style='font-size:22px;font-weight:600;font-family:var(--mono);'>€{total_v:,.0f}</div>"
        f"<div style='font-size:11px;font-family:var(--mono);color:{pnl_c};margin-top:3px;'>{'+'if total_pnl>=0 else ''}€{total_pnl:.0f} · {'+'if total_pct>=0 else ''}{total_pct:.2f}%</div>"
        f"</div>"
    )

    best_t = s.get("best_theme")
    by_theme = s.get("platform_score", {}).get("by_theme", {})
    if best_t and best_t in by_theme:
        bt = by_theme[best_t]
        bt_h = bt.get("hits", 0); bt_m = bt.get("misses", 0)
        bt_rate = f"{bt_h/(bt_h+bt_m)*100:.0f}%" if bt_h+bt_m > 0 else "—"
        best_card = (
            f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:14px 16px;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>Best theme</div>"
            f"<div style='font-size:16px;font-weight:600;text-transform:capitalize;color:var(--green);'>{best_t.replace('_',' ')}</div>"
            f"<div style='font-size:11px;color:var(--muted);margin-top:3px;'>{bt_rate} hit rate · {bt_h}/{bt_h+bt_m}</div>"
            f"</div>"
        )
    else:
        best_card = (
            f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:14px 16px;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>Best theme</div>"
            f"<div style='font-size:12px;color:var(--muted);font-family:var(--mono);'>No closed positions yet</div>"
            f"</div>"
        )

    stats_row = (
        f"<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px;'>"
        f"{hit_rate_card}{total_card}{best_card}"
        f"</div>"
    )

    # ── OPEN POSITIONS TABLE ──────────────────────────────────────────────────
    open_pos = s["open_positions"]
    if open_pos:
        pos_rows = ""
        for p in open_pos:
            side      = p.get("side", "BUY")
            raw_side  = p.get("side", "LONG")  # LONG/SHORT from position book
            is_long   = raw_side in ("LONG", "BUY")
            sc        = "#27500A" if is_long else "#791F1F"
            sbg       = "#EAF3DE" if is_long else "#FCEBEB"
            side_lbl  = "LONG" if is_long else "SHORT"
            ticker    = p.get("ticker", "")
            theme     = (p.get("themes") or [p.get("theme","")])[0] or ""
            avg_entry = p.get("avg_entry", 0)
            invested  = p.get("invested_eur", 0)
            pnl_pct   = p.get("pnl_pct", 0)
            pnl_eur   = p.get("pnl_eur", 0)
            market_open = s["market_open"]

            # Age
            from datetime import datetime, timezone
            try:
                open_dt = datetime.fromisoformat(p["open_date"].replace("Z","+00:00"))
                hours   = (datetime.now(timezone.utc) - open_dt).total_seconds() / 3600
                age_str = f"{int(hours)}h" if hours < 48 else f"{int(hours/24)}d"
            except Exception:
                age_str = p.get("age", "—")

            # P&L cell
            if not market_open:
                pnl_cell = "<span style='color:var(--muted);font-size:11px;'>— market closed</span>"
            else:
                pc = "var(--green)" if pnl_pct >= 0 else "var(--red)"
                pnl_cell = (
                    f"<span style='color:{pc};font-weight:600;font-family:var(--mono);'>"
                    f"{'+'if pnl_pct>=0 else ''}{pnl_pct:.1f}% · {'+'if pnl_eur>=0 else ''}€{pnl_eur:.0f}"
                    f"</span>"
                )

            # Check badges
            check_html = ""
            for lbl, chk in [("4h", p.get("check_4h")), ("24h", p.get("check_24h"))]:
                if chk:
                    cc = "var(--green)" if chk.get("hit") else "var(--red)"
                    check_html += (
                        f"<span style='font-size:10px;font-family:var(--mono);padding:1px 6px;"
                        f"border-radius:3px;background:{cc}18;color:{cc};margin-right:4px;'>"
                        f"{lbl}: {chk['pct']:+.1f}%</span>"
                    )
            if not check_html:
                check_html = "<span style='font-size:11px;color:var(--muted);'>—</span>"

            pos_rows += (
                f"<tr style='border-bottom:1px solid var(--border);'>"
                f"<td style='{td}'><span style='background:{sbg};color:{sc};font-family:var(--mono);"
                f"font-size:11px;font-weight:600;padding:2px 8px;border-radius:3px;'>{side_lbl}</span></td>"
                f"<td style='{tdm}font-weight:600;'>"
                f"<a href='https://finance.yahoo.com/quote/{ticker}' target='_blank' "
                f"style='color:#185FA5;text-decoration:none;'>{ticker}</a></td>"
                f"<td style='{td}color:var(--muted);text-transform:capitalize;'>{theme.replace('_',' ')}</td>"
                f"<td style='{tdm}'>€{invested:,.0f} @ ${avg_entry:.2f}</td>"
                f"<td style='{tdm}'>{pnl_cell}</td>"
                f"<td style='{td}color:var(--muted);'>{age_str}</td>"
                f"<td style='{td}'>{check_html}</td>"
                f"</tr>"
            )

        open_html = (
            f"<div style='background:var(--surface);border:1px solid var(--border);"
            f"border-radius:4px;margin-bottom:12px;overflow:hidden;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);"
            f"text-transform:uppercase;letter-spacing:.06em;padding:10px 14px;"
            f"border-bottom:1px solid var(--border);'>Open positions ({len(open_pos)})</div>"
            f"<div style='overflow-x:auto;'>"
            f"<table style='width:100%;border-collapse:collapse;'>"
            f"<tr style='background:#f0f0eb;'>"
            f"<th style='{th}'>Side</th><th style='{th}'>Ticker</th><th style='{th}'>Theme</th>"
            f"<th style='{th}'>Avg entry</th><th style='{th}'>P&amp;L</th>"
            f"<th style='{th}'>Age</th><th style='{th}'>Checks</th>"
            f"</tr>{pos_rows}"
            f"</table></div></div>"
        )
    else:
        open_html = (
            "<div style='font-size:12px;color:var(--muted);font-family:var(--mono);"
            "padding:12px 0;'>No open positions — portfolio opens when a BUY or SELL verdict fires with sufficient confidence</div>"
        )

    # ── CLOSED POSITIONS TABLE ────────────────────────────────────────────────
    closed_pos = s["closed_positions"]
    if closed_pos:
        c_rows = ""
        for p in reversed(closed_pos[-10:]):
            raw_side = p.get("side", "LONG")
            is_long  = raw_side in ("LONG", "BUY")
            sc       = "#27500A" if is_long else "#791F1F"
            sbg      = "#EAF3DE" if is_long else "#FCEBEB"
            side_lbl = "LONG" if is_long else "SHORT"
            ticker   = p.get("ticker", "")
            theme    = (p.get("themes") or [p.get("theme","")])[0] or ""
            entry    = p.get("avg_entry", 0)
            close_p  = p.get("close_price", 0)
            pnl_pct  = p.get("pnl_pct", 0)
            pnl_eur  = p.get("pnl_eur", 0)
            hold     = p.get("hold_hours", 0)
            hit      = p.get("hit", False)
            reason   = p.get("close_reason","").replace("_"," ")
            pc       = "var(--green)" if pnl_eur >= 0 else "var(--red)"
            hc       = "#27500A" if hit else "#791F1F"
            hbg      = "#EAF3DE" if hit else "#FCEBEB"
            hold_str = f"{int(hold)}h" if hold < 48 else f"{int(hold/24)}d"

            c_rows += (
                f"<tr style='border-bottom:1px solid var(--border);'>"
                f"<td style='{td}'><span style='background:{sbg};color:{sc};font-family:var(--mono);"
                f"font-size:11px;font-weight:600;padding:2px 8px;border-radius:3px;'>{side_lbl}</span></td>"
                f"<td style='{tdm}font-weight:600;color:#185FA5;'>{ticker}</td>"
                f"<td style='{td}color:var(--muted);text-transform:capitalize;'>{theme.replace('_',' ')}</td>"
                f"<td style='{tdm}'>${entry:.2f} → ${close_p:.2f}</td>"
                f"<td style='{tdm}color:{pc};font-weight:600;'>{'+'if pnl_eur>=0 else ''}€{pnl_eur:.0f} · {'+'if pnl_pct>=0 else ''}{pnl_pct:.1f}%</td>"
                f"<td style='{td}color:var(--muted);'>{hold_str}</td>"
                f"<td style='{td}'><span style='background:{hbg};color:{hc};font-family:var(--mono);"
                f"font-size:11px;font-weight:600;padding:2px 8px;border-radius:3px;'>{'HIT' if hit else 'MISS'}</span></td>"
                f"<td style='{td}font-size:11px;color:var(--muted);'>{reason}</td>"
                f"</tr>"
            )

        closed_html = (
            f"<div style='background:var(--surface);border:1px solid var(--border);"
            f"border-radius:4px;overflow:hidden;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);"
            f"text-transform:uppercase;letter-spacing:.06em;padding:10px 14px;"
            f"border-bottom:1px solid var(--border);'>Closed positions</div>"
            f"<div style='overflow-x:auto;'>"
            f"<table style='width:100%;border-collapse:collapse;'>"
            f"<tr style='background:#f0f0eb;'>"
            f"<th style='{th}'>Side</th><th style='{th}'>Ticker</th><th style='{th}'>Theme</th>"
            f"<th style='{th}'>Entry → Close</th><th style='{th}'>P&amp;L</th>"
            f"<th style='{th}'>Hold</th><th style='{th}'>Result</th><th style='{th}'>Reason</th>"
            f"</tr>{c_rows}"
            f"</table></div></div>"
        )
    else:
        closed_html = ""

    return (
        f"<div style='background:var(--surface);border:1px solid var(--border);"
        f"border-radius:4px;padding:16px;'>"
        f"{summary_row}"
        f"{stats_row}"
        f"{open_html}"
        f"{closed_html}"
        f"</div>"
    )


# ── LIVE.HTML ─────────────────────────────────────────────────────────────────
def generate_live_html(seen_data, all_alerts, advice_cards=None, analyst_verdicts=None, panel_advice=None, skip_prices=False):
    active_tickers = {t for a in all_alerts for t, n, e in a.get("etfs", [])}
    advice_cards_list = advice_cards or []
    advice_html       = format_advice_html_section(advice_cards_list)
    portfolio_section = _portfolio_html(seen_data)
    # Analyst panel
    if analyst_verdicts and panel_advice:
        panel_html = format_panel_html(analyst_verdicts, panel_advice)
    else:
        panel_html = "<div style='color:var(--muted);font-family:var(--mono);font-size:12px;padding:1rem;'>No panel data yet — run scanner first.</div>"


    # ── SIGNAL CARDS ──────────────────────────────────────────────────────────
    alert_cards = ""
    for a in all_alerts[:10]:
        c       = urgency_color(a["urgency"])
        is_conv = a["source"] == "CONVERGENCE"
        r       = a.get("reasoning", {})
        cp      = min(100, max(5, r.get("confidence", 50)))
        cc      = "#007a5e" if cp >= 65 else "#b06000" if cp >= 45 else "#cc2222"
        d       = a.get("direction", "").upper()
        dc      = "var(--green)" if any(w in d for w in ["BUY","YES","ACCUM","BULLISH"]) else \
                  "var(--red)"   if any(w in d for w in ["SELL","NO","REDUCE","BEARISH"]) else "var(--amber)"
        src_cls = "src-" + a.get("source","").lower().replace(" ","").replace("(","").replace(")","").replace("/","").replace("&","")

        # ETF badges
        etf_badges = "".join(
            f'<a href="{etf_yahoo_url(t,e)}" class="etf-badge" target="_blank">{t}</a>'
            for t, n, e in a.get("etfs", [])[:3]
        )

        # Individual stock badges (separate row)
        stocks      = _extract_stocks(a)
        stock_row   = ""
        if stocks:
            stock_badges = "".join(
                f'<a href="https://finance.yahoo.com/quote/{s}" class="stock-badge" target="_blank">{s}</a>'
                for s in stocks
            )
            stock_row = (
                f"<div style='margin-top:4px;'>"
                f"<span style='font-size:10px;font-family:var(--mono);color:var(--muted);margin-right:6px;'>Stocks</span>"
                f"{stock_badges}</div>"
            )

        alert_cards += (
            f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:4px;"
            f"padding:14px;margin-bottom:10px;border-left:3px solid {'#1a1a1a' if is_conv else c};'>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;'>"
            f"<span class='badge {src_cls}'>{a.get('source','').upper()}</span>"
            f"<span style='font-family:var(--mono);font-size:11px;font-weight:600;color:{dc};'>{a.get('direction','')[:25]}</span>"
            f"<span style='font-size:10px;font-family:var(--mono);padding:2px 8px;border-radius:10px;"
            f"font-weight:600;background:{c}20;color:{c};'>{a.get('urgency','')}</span>"
            f"<span style='font-family:var(--mono);font-size:10px;color:var(--dim);margin-left:auto;'>scan: {now_be()[:16]}</span>"
            f"</div>"
            f"<div style='font-size:14px;font-weight:600;margin-bottom:4px;line-height:1.4;'>{a.get('title','')[:100]}</div>"
            f"<div style='font-size:12px;color:var(--muted);margin-bottom:6px;line-height:1.5;'>{a.get('detail','')[:160]}</div>"
            f"<div style='font-size:12px;color:var(--muted);margin-bottom:8px;border-left:2px solid var(--border2);"
            f"padding-left:8px;line-height:1.5;'><span style='font-family:var(--mono);'>Why: </span>{r.get('why','')[:140]}</div>"
            f"<div style='padding-top:8px;border-top:1px solid var(--border2);'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>"
            f"<div>"
            f"<div style='margin-bottom:4px;'>"
            f"<span style='font-size:10px;font-family:var(--mono);color:var(--muted);margin-right:6px;'>ETFs</span>"
            f"{etf_badges}</div>"
            f"{stock_row}"
            f"</div>"
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<div class='conf-mini-wrap'><div class='conf-mini' style='width:{cp}%;background:{cc};'></div></div>"
            f"<span style='font-family:var(--mono);font-size:11px;color:{cc};'>{cp}%</span>"
            f"<a href='{a.get('link','#')}' style='font-family:var(--mono);font-size:11px;color:var(--blue);"
            f"text-decoration:none;' target='_blank'>source ↗</a>"
            f"</div></div></div></div>"
        )

    if not alert_cards:
        alert_cards = (
            "<div style='text-align:center;color:var(--dim);font-family:var(--mono);font-size:12px;"
            "padding:2rem;background:var(--surface);border:1px solid var(--border);border-radius:4px;'>"
            "No new signals in this run — scanner active every 30 min</div>"
        )

    # ── ETF WATCHLIST — dynamic JS rendering ─────────────────────────────────
    # Prices fetched client-side via Twelve Data API — no server needed
    active_tickers_js = str(list(active_tickers)).replace("'", '"')

    twelvedata_key = TWELVEDATA_KEY or ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="120">
<title>Stocazzo — Live</title>
<style>{_CSS}
.sources-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
.etf-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
@media(max-width:700px) {{ .sources-grid {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <div class="logo">STOCAZZO // SIGNAL TRACKER</div>
      <h1>Live Dashboard</h1>
      <div class="updated">Last scan: {now_utc()} · {now_be()}</div>
    </div>
    <div>
      <a href="sources.html" class="nav-link">Sources →</a>
      <a href="history.html" class="nav-link">Signal History →</a>
    </div>
  </header>

  {_legend_bar()}

  <div class="section">
    <div class="section-title">Analyst panel — weighted verdict</div>
    {panel_html}
  </div>

  <div class="section">
    <div class="section-title">Virtual portfolio — €100,000 capital · one position per ticker · live P&amp;L</div>
    {portfolio_section}
  </div>

  <div class="section">
    <div class="section-title">Current signals ({len(all_alerts)})</div>
    {alert_cards}
  </div>

  <div class="section">
    <div class="section-title">ETF watchlist — live prices</div>
    <div id="fear-greed-bar" style="margin-bottom:12px;"></div>
    <div id="etf-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
      <div style="color:var(--muted);font-family:var(--mono);font-size:12px;padding:8px;">Loading prices...</div>
    </div>
  </div>
</div>
<div id="td-key" data-key="{twelvedata_key}" style="display:none;"></div>
<div id="active-tickers" data-tickers="{active_tickers_js}" style="display:none;"></div>
</body>
</html>"""

    # Dynamic ETF + Fear&Greed script — injected separately to avoid f-string brace conflicts
    _ETF_DATA_JSON = '{\n  "XLE": {\n    "name": "Energy Select SPDR",\n    "exchange": "NYSE",\n    "theme": "Energie",\n    "yahoo": "https://finance.yahoo.com/quote/XLE",\n    "google": "https://www.google.com/finance/quote/XLE:NYSE"\n  },\n  "IEO": {\n    "name": "Oil & Gas E&P",\n    "exchange": "NYSE",\n    "theme": "Energie",\n    "yahoo": "https://finance.yahoo.com/quote/IEO",\n    "google": "https://www.google.com/finance/quote/IEO:NYSE"\n  },\n  "INRG": {\n    "name": "Global Clean Energy",\n    "exchange": "AMS",\n    "theme": "Renewables",\n    "yahoo": "https://finance.yahoo.com/quote/INRG.AS",\n    "google": "https://www.google.com/finance/quote/INRG:AMS"\n  },\n  "ICLN": {\n    "name": "Clean Energy",\n    "exchange": "NASDAQ",\n    "theme": "Renewables",\n    "yahoo": "https://finance.yahoo.com/quote/ICLN",\n    "google": "https://www.google.com/finance/quote/ICLN:NASDAQ"\n  },\n  "GLD": {\n    "name": "SPDR Gold",\n    "exchange": "NYSE",\n    "theme": "Goud",\n    "yahoo": "https://finance.yahoo.com/quote/GLD",\n    "google": "https://www.google.com/finance/quote/GLD:NYSE"\n  },\n  "IGLN": {\n    "name": "Physical Gold ETC",\n    "exchange": "AMS",\n    "theme": "Goud",\n    "yahoo": "https://finance.yahoo.com/quote/IGLN.AS",\n    "google": "https://www.google.com/finance/quote/IGLN:AMS"\n  },\n  "ITA": {\n    "name": "US Aerospace & Defense",\n    "exchange": "NYSE",\n    "theme": "Defensie",\n    "yahoo": "https://finance.yahoo.com/quote/ITA",\n    "google": "https://www.google.com/finance/quote/ITA:NYSE"\n  },\n  "SOXX": {\n    "name": "Semiconductors",\n    "exchange": "NASDAQ",\n    "theme": "Tech",\n    "yahoo": "https://finance.yahoo.com/quote/SOXX",\n    "google": "https://www.google.com/finance/quote/SOXX:NASDAQ"\n  },\n  "QQQ": {\n    "name": "Nasdaq-100",\n    "exchange": "NASDAQ",\n    "theme": "Tech",\n    "yahoo": "https://finance.yahoo.com/quote/QQQ",\n    "google": "https://www.google.com/finance/quote/QQQ:NASDAQ"\n  },\n  "IBIT": {\n    "name": "Bitcoin Trust",\n    "exchange": "NASDAQ",\n    "theme": "Crypto",\n    "yahoo": "https://finance.yahoo.com/quote/IBIT",\n    "google": "https://www.google.com/finance/quote/IBIT:NASDAQ"\n  },\n  "TLT": {\n    "name": "20yr Treasury Bond",\n    "exchange": "NASDAQ",\n    "theme": "Obligaties",\n    "yahoo": "https://finance.yahoo.com/quote/TLT",\n    "google": "https://www.google.com/finance/quote/TLT:NASDAQ"\n  },\n  "IWDA": {\n    "name": "MSCI World",\n    "exchange": "AMS",\n    "theme": "Breed",\n    "yahoo": "https://finance.yahoo.com/quote/IWDA.AS",\n    "google": "https://www.google.com/finance/quote/IWDA:AMS"\n  }\n}'
    _DYNAMIC_SCRIPT = """<script>
(function() {
  var key     = document.getElementById('td-key').getAttribute('data-key');
  var active  = JSON.parse(document.getElementById('active-tickers').getAttribute('data-tickers') || '[]');
  var etfData = """ + _ETF_DATA_JSON + """;
  var tickers = Object.keys(etfData);
  var prices  = {};

  function renderGrid() {
    var grid = document.getElementById('etf-grid');
    if (!grid) return;
    grid.innerHTML = '';
    tickers.forEach(function(t) {
      var info = etfData[t];
      var q    = prices[t];
      var isActive = active.indexOf(t) >= 0;
      var border = isActive ? 'border-left:3px solid var(--green);' : '';
      var dot    = isActive ? '<span style="width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;"></span>' : '';
      var priceHtml = '';
      if (q && q.close) {
        var pct   = parseFloat(q.percent_change || 0);
        var price = parseFloat(q.close);
        var pc    = pct >= 0 ? 'var(--green)' : 'var(--red)';
        var icon  = pct >= 0 ? '\u25b2' : '\u25bc';
        priceHtml = '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:6px;">' +
          '<span style="font-family:var(--mono);font-weight:600;font-size:13px;">$' + price.toFixed(2) + '</span>' +
          '<span style="font-family:var(--mono);font-size:11px;font-weight:600;color:' + pc + ';">' + icon + ' ' + Math.abs(pct).toFixed(2) + '%</span>' +
          '</div>';
      } else {
        priceHtml = '<div style="font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:6px;">—</div>';
      }
      var d = document.createElement('div');
      d.style.cssText = 'background:var(--surface);border:1px solid var(--border);padding:10px;border-radius:4px;' + border;
      d.innerHTML =
        '<div style="display:flex;align-items:center;justify-content:space-between;">' +
        '<a href="' + info.yahoo + '" target="_blank" style="font-family:var(--mono);font-size:14px;font-weight:700;color:var(--green);text-decoration:none;">' + t + '</a>' + dot +
        '</div>' +
        '<div style="font-size:12px;color:var(--muted);margin:2px 0;">' + info.name + '</div>' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:3px;">' +
        '<span style="font-family:var(--mono);font-size:11px;color:var(--dim);">' + info.exchange + '</span>' +
        '<span style="font-size:10px;background:#f0f0eb;color:var(--muted);padding:1px 6px;border-radius:3px;">' + info.theme + '</span>' +
        '</div>' + priceHtml +
        '<div style="display:flex;gap:4px;margin-top:6px;">' +
        '<a href="' + info.yahoo + '" target="_blank" style="font-family:var(--mono);font-size:10px;padding:2px 7px;border:1px solid var(--border);border-radius:3px;text-decoration:none;color:var(--blue);">Yahoo</a>' +
        '<a href="' + info.google + '" target="_blank" style="font-family:var(--mono);font-size:10px;padding:2px 7px;border:1px solid var(--border);border-radius:3px;text-decoration:none;color:var(--muted);">Google</a>' +
        '</div>';
      grid.appendChild(d);
    });
  }

  function fetchNext(i) {
    if (i >= tickers.length) { renderGrid(); return; }
    if (!key) { renderGrid(); return; }
    var t = tickers[i];
    fetch('https://api.twelvedata.com/quote?symbol=' + t + '&apikey=' + key)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data && data.close) prices[t] = data;
        renderGrid();
        setTimeout(function() { fetchNext(i + 1); }, 600);
      }).catch(function() {
        setTimeout(function() { fetchNext(i + 1); }, 600);
      });
  }

  fetch('https://production.dataviz.cnn.io/index/fearandgreed/graphdata')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var fg    = data.fear_and_greed || {};
      var score = parseFloat(fg.score || fg.value || 50);
      var label = fg.rating || fg.value_classification || '';
      var color = score <= 25 ? '#cc2222' : score <= 45 ? '#b06000' : score <= 55 ? '#888' : score <= 75 ? '#007a5e' : '#005f4a';
      var bar = document.getElementById('fear-greed-bar');
      if (bar) bar.innerHTML =
        '<div style="display:flex;align-items:center;gap:12px;background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:10px 14px;">' +
        '<span style="font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;">Fear &amp; Greed</span>' +
        '<div style="background:#e0e0d8;border-radius:4px;height:8px;width:200px;"><div style="background:' + color + ';height:8px;border-radius:4px;width:' + score + '%;"></div></div>' +
        '<span style="font-family:var(--mono);font-size:14px;font-weight:600;color:' + color + ';">' + Math.round(score) + '/100</span>' +
        '<span style="font-size:12px;color:var(--muted);">' + label + '</span>' +
        '<span style="font-size:10px;color:var(--dim);margin-left:auto;font-family:var(--mono);">live</span>' +
        '</div>';
    }).catch(function() {});

  fetchNext(0);
})();
</script>"""

    # Inject script into html at the end
    html = html.replace("</body>\n</html>", _DYNAMIC_SCRIPT + "\n</body>\n</html>")

    with open("live.html", "w") as f:
        f.write(html)
    print("live.html generated")


# ── SOURCES.HTML ──────────────────────────────────────────────────────────────
def generate_sources_html(seen_data):
    """Dedicated sources page — moved off live dashboard."""
    stats = seen_data.get("stats", {})

    source_cards = ""
    for src, cred in SOURCE_CREDIBILITY.items():
        stat  = stats.get(src, {"hits": 0, "misses": 0, "pending": 0})
        total = stat["hits"] + stat["misses"]
        w     = cred["weight"]
        stars = "★" * w + "☆" * (5 - w)

        if total > 0:
            rate      = f"{stat['hits']/total:.0%}"
            bar       = int(stat['hits']/total*100)
            rate_html = (
                f"<div style='background:#e0e0d8;border-radius:2px;height:4px;width:100%;margin:6px 0 3px;'>"
                f"<div style='background:var(--green);height:4px;border-radius:2px;width:{bar}%;'></div></div>"
                f"<div style='font-size:12px;font-family:var(--mono);color:var(--green);font-weight:600;'>"
                f"{stat['hits']}/{total} · {rate}</div>"
            )
        else:
            rate_html = (
                f"<div style='font-size:11px;font-family:var(--mono);color:var(--muted);margin-top:6px;'>"
                f"No verified data yet</div>"
            )

        src_cls = "src-" + src.lower().replace(" ","").replace("(","").replace(")","").replace("/","").replace("&","")

        # Category label
        is_crony = src in ["Polymarket","Kalshi","SEC EDGAR","Pelosi Tracker","Congress","Dark Pool","Options Flow","Truth Social","Lobbying","Gov Contracts"]
        cat_color = "#cc2222" if is_crony else "#1a5fb5"
        cat_label = "Crony" if is_crony else "Macro"

        source_cards += (
            f"<div style='background:var(--surface);border:1px solid var(--border);"
            f"border-radius:4px;padding:16px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;'>"
            f"<span class='badge {src_cls}'>{src.upper()}</span>"
            f"<span style='font-size:10px;font-family:var(--mono);padding:2px 7px;border-radius:3px;"
            f"background:{cat_color}15;color:{cat_color};font-weight:600;'>{cat_label}</span>"
            f"</div>"
            f"<div style='font-size:13px;color:var(--amber);margin-bottom:6px;letter-spacing:0.05em;'>{stars}</div>"
            f"<div style='font-size:12px;color:var(--muted);margin-bottom:4px;'>{cred.get('type','')}</div>"
            f"<div style='font-size:11px;font-family:var(--mono);color:var(--blue);margin-bottom:6px;'>"
            f"Lead time: {cred.get('avg_lead_time','?')}</div>"
            f"<div style='font-size:11px;color:var(--text);line-height:1.5;margin-bottom:8px;'>{cred['note']}</div>"
            f"{rate_html}"
            f"</div>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stocazzo — Sources</title>
<style>{_CSS}
.sources-full {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
@media(max-width:700px) {{ .sources-full {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <div class="logo">STOCAZZO // SIGNAL TRACKER</div>
      <h1>Signal Sources</h1>
      <div class="updated">{len(SOURCE_CREDIBILITY)} active sources · {now_be()}</div>
    </div>
    <div>
      <a href="live.html" class="nav-link">Live Dashboard →</a>
      <a href="history.html" class="nav-link">Signal History →</a>
    </div>
  </header>

  <div style="display:flex;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap;">
    <div style="display:flex;align-items:center;gap:6px;font-size:12px;">
      <span style="width:10px;height:10px;border-radius:2px;background:#cc222215;border:1px solid #cc2222;display:inline-block;"></span>
      <span style="color:#cc2222;font-weight:600;">Crony</span>
      <span style="color:var(--muted);">— signals BEFORE the news (insider, prediction markets)</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;font-size:12px;">
      <span style="width:10px;height:10px;border-radius:2px;background:#1a5fb515;border:1px solid #1a5fb5;display:inline-block;"></span>
      <span style="color:#1a5fb5;font-weight:600;">Macro</span>
      <span style="color:var(--muted);">— signals AFTER the news (RSS, GDELT, sentiment)</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;font-size:12px;margin-left:auto;">
      <span style="color:var(--amber);">★★★★★</span>
      <span style="color:var(--muted);">= source weight (1-5)</span>
    </div>
  </div>

  <div class="sources-full">{source_cards}</div>

</div>
</body>
</html>"""

    with open("sources.html", "w") as f:
        f.write(html)
    print("sources.html generated")


# ── HISTORY.HTML ──────────────────────────────────────────────────────────────

def _detail_block(h):
    """Render the detail/snippet block with optional source link."""
    detail = h.get("detail","") or h.get("title","")
    link   = h.get("link","")
    link_html = ""
    if link:
        link_html = (
            f" &nbsp;<a href='{link}' target='_blank' "
            f"style='font-family:var(--mono);font-size:11px;color:var(--blue);'>source ↗</a>"
        )
    return (
        f"<div style='background:var(--surface);border:1px solid var(--border2);border-radius:4px;"
        f"padding:10px 12px;margin-bottom:12px;font-size:13px;line-height:1.6;color:var(--text);'>"
        f"{detail}{link_html}</div>"
    )


def generate_history_html(seen_data):
    history = seen_data.get("history", [])
    stats   = seen_data.get("stats", {})

    total   = len(history)
    hits    = sum(1 for h in history if h.get("verified") is True)
    misses  = sum(1 for h in history if h.get("verified") is False)
    pending = sum(1 for h in history if h.get("verified") is None)
    rate    = f"{hits/(hits+misses):.0%}" if (hits + misses) > 0 else "n/a"

    # Per-source stats table
    source_rows = ""
    for src, stat in stats.items():
        t     = stat["hits"] + stat["misses"]
        r     = f"{stat['hits']/t:.0%}" if t else "—"
        bar   = int(stat["hits"]/t*100) if t else 0
        color = "var(--green)" if bar >= 60 else "var(--amber)" if bar >= 40 else "var(--red)"
        note  = SOURCE_CREDIBILITY.get(src, {}).get("note", "")
        source_rows += (
            f"<tr>"
            f"<td class='mono'>{src}</td>"
            f"<td class='mono green bold'>{stat['hits']}</td>"
            f"<td class='mono red'>{stat['misses']}</td>"
            f"<td class='mono muted'>{stat['pending']}</td>"
            f"<td><div style='background:#e0e0d8;border-radius:2px;height:4px;width:80px;margin-bottom:3px;'>"
            f"<div style='background:{color};height:4px;border-radius:2px;width:{bar}%;'></div></div>"
            f"<span class='mono small bold' style='color:{color};'>{r}</span></td>"
            f"<td class='muted small'>{note[:80]}</td>"
            f"</tr>"
        )

    # Signal rows
    signal_rows = ""
    for idx, h in enumerate(reversed(history)):
        verified = h.get("verified")
        pct      = h.get("pct_change")

        d_upper = h.get("direction","").upper()
        is_actionable = any(w in d_upper for w in ["BUY","SELL","BULLISH","BEARISH","REDUCE","ACCUM","YES","NO"])

        if verified is True:
            sc, si, sl = "hit",     "✓", f"HIT {pct:+.1f}%" if pct is not None else "HIT"
        elif verified is False:
            sc, si, sl = "miss",    "✗", f"MISS {pct:+.1f}%" if pct is not None else "MISS"
        elif not is_actionable:
            sc, si, sl = "pending", "—", "WATCH"
        else:
            sc, si, sl = "pending", "·", "PENDING"

        d  = h.get("direction", "").upper()
        dc = "green" if any(w in d for w in ["BUY","YES","ACCUM","BULLISH"]) else \
             "red"   if any(w in d for w in ["SELL","NO","REDUCE","BEARISH"]) else "amber"

        etf_badges = "".join(
            f'<a href="{etf_yahoo_url(t,e)}" class="etf-badge" target="_blank">{t}</a>'
            for t, n, e in h.get("etfs", [])
        )

        cp = min(100, max(5, h.get("confidence", 50)))
        cc = "#007a5e" if cp >= 65 else "#b06000" if cp >= 45 else "#cc2222"
        r       = h.get("reasoning_stored", {})
        why     = r.get("why", h.get("detail", ""))
        caveat  = r.get("caveat", "")
        bd      = r.get("breakdown", [])
        bd_rows = ""
        for b in bd:
            bdc = "green" if "BUY" in b.get("direction","").upper() else \
                  "red"   if "SELL" in b.get("direction","").upper() else "amber"
            bd_rows += (
                f"<tr><td class='mono small'>{b['source']}</td>"
                f"<td class='mono small {bdc} bold'>{b['direction']}</td>"
                f"<td class='mono small green'>{b['points']}pts</td>"
                f"<td class='mono small muted'>{b['reasoning']}</td></tr>"
            )
        bd_html = (
            f"<table style='width:100%;border-collapse:collapse;font-size:11px;margin-top:8px;"
            f"border:1px solid var(--border2);'>"
            f"<tr style='background:#f0f0eb;'><th style='padding:4px 8px;'>Source</th>"
            f"<th style='padding:4px 8px;'>Direction</th><th style='padding:4px 8px;'>Pts</th>"
            f"<th style='padding:4px 8px;'>Reasoning</th></tr>{bd_rows}</table>"
            if bd_rows else ""
        )
        vd_html = (
            f"<div style='margin-top:8px;padding-top:8px;border-top:1px solid var(--border2);'>"
            f"<span class='mono small muted'>Verified: {h.get('verified_date','')} · "
            f"Entry: ${h.get('price_entry','—')} → Now: ${h.get('price_now','—')}</span></div>"
            if verified is not None else ""
        )
        src_cls = "src-" + h.get("source","").lower().replace(" ","").replace("(","").replace(")","").replace("/","").replace("&","")

        signal_rows += f"""
        <tr class="signal-row {sc}" onclick="toggleR({idx})">
          <td class="mono muted small" style="white-space:nowrap;">{h.get('date_be','')[:16]}</td>
          <td><span class="badge {src_cls}">{h.get('source','').upper()}</span></td>
          <td class="mono {dc} bold small">{h.get('direction','')[:18]}</td>
          <td style="max-width:300px;"><span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{h.get('title','')}">{h.get('title','')[:100]}</span></td>
          <td>{etf_badges}</td>
          <td>
            <div class="conf-mini-wrap"><div class="conf-mini" style="width:{cp}%;background:{cc};"></div></div>
            <span class="mono small" style="color:{cc};">{cp}%</span>
          </td>
          <td><span style="font-size:11px;font-family:var(--mono);font-weight:600;padding:2px 8px;border-radius:3px;
            {'background:#e8f4f0;color:var(--green);' if sc=='hit' else 'background:#fce8e8;color:var(--red);' if sc=='miss' else 'background:#f5f5f0;color:var(--dim);'}">{si} {sl}</span></td>
          <td style="width:24px;text-align:center;"><span id="ei{idx}" style="font-size:11px;color:var(--dim);font-family:var(--mono);transition:transform 0.15s;display:inline-block;">▸</span></td>
        </tr>
        <tr id="rr{idx}" style="display:none;">
          <td colspan="8" style="padding:0;">
            <div style="background:#f8f8f4;border-top:1px solid var(--border2);padding:14px 16px;">
              {_detail_block(h)}
              <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:10px;">
                <div><div style="font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;margin-bottom:3px;">Why</div>
                  <div style="font-size:12px;line-height:1.5;">{why}</div></div>
                <div><div style="font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;margin-bottom:3px;">Caveat</div>
                  <div style="font-size:12px;color:var(--amber);line-height:1.5;">{caveat}</div></div>
              </div>
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <div style="flex:1;background:#e0e0d8;border-radius:2px;height:5px;"><div style="background:{cc};height:5px;border-radius:2px;width:{cp}%;"></div></div>
                <span class="mono small" style="color:{cc};">Confidence: {cp}%</span>
              </div>
              {bd_html}{vd_html}
            </div>
          </td>
        </tr>"""

    if not signal_rows:
        signal_rows = '<tr><td colspan="8" style="text-align:center;color:var(--dim);padding:2rem;font-family:var(--mono);">No signals recorded yet</td></tr>'

    rate_color = "var(--green)" if rate != "n/a" and int(rate.replace('%','')) >= 60 else "var(--amber)"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stocazzo — History</title>
<style>{_CSS}
table {{ width:100%; border-collapse:collapse; background:var(--surface); border:1px solid var(--border); font-size:13px; }}
th {{ background:#f0f0eb; padding:7px 10px; text-align:left; font-size:10px; font-family:var(--mono); color:var(--muted); text-transform:uppercase; letter-spacing:0.06em; border-bottom:1px solid var(--border); }}
td {{ padding:9px 10px; border-bottom:1px solid var(--border2); vertical-align:middle; }}
.signal-row {{ cursor:pointer; }} .signal-row:hover td {{ background:#fafaf8; }}
.signal-row.hit td:first-child {{ border-left:3px solid var(--green); }}
.signal-row.miss td:first-child {{ border-left:3px solid var(--red); }}
.signal-row.pending td:first-child {{ border-left:3px solid #ddd; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:1.5rem; }}
.stat {{ background:var(--surface); border:1px solid var(--border); padding:14px; border-radius:4px; }}
.stat .val {{ font-size:26px; font-weight:400; font-family:var(--mono); }}
.stat .lbl {{ font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:0.06em; margin-top:3px; }}
.filter-btn {{ font-family:var(--mono); font-size:11px; padding:4px 10px; border:1px solid var(--border); background:var(--surface); cursor:pointer; border-radius:3px; color:var(--muted); margin-right:4px; margin-bottom:4px; }}
.filter-btn.active, .filter-btn:hover {{ background:var(--text); color:#fff; border-color:var(--text); }}
@media(max-width:700px) {{ .stats-grid {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <div class="logo">STOCAZZO // SIGNAL TRACKER</div>
      <h1>Signal History &amp; Backcheck</h1>
      <div class="updated">Updated: {now_utc()} · {now_be()} · {total} signals</div>
    </div>
    <div>
      <a href="live.html" class="nav-link">Live Dashboard →</a>
      <a href="sources.html" class="nav-link">Sources →</a>
    </div>
  </header>

  <div class="stats-grid">
    <div class="stat"><div class="val">{total}</div><div class="lbl">Total signals</div></div>
    <div class="stat"><div class="val" style="color:var(--green);">{hits}</div><div class="lbl">Verified hits</div></div>
    <div class="stat"><div class="val" style="color:var(--red);">{misses}</div><div class="lbl">Missed predictions</div></div>
    <div class="stat"><div class="val" style="color:{rate_color};">{rate}</div><div class="lbl">Overall hit rate</div></div>
  </div>

  <div class="section">
    <div class="section-title">Hit rate per source</div>
    <table>
      <tr><th>Source</th><th>Hits</th><th>Misses</th><th>Pending</th><th>Hit rate</th><th>Notes</th></tr>
      {source_rows}
    </table>
  </div>

  <div class="section">
    <div class="section-title">Signal log — click row to expand reasoning</div>
    <div style="margin-bottom:10px;">
      <button class="filter-btn active" onclick="filter('all',this)">All ({total})</button>
      <button class="filter-btn" onclick="filter('hit',this)">✓ Hits ({hits})</button>
      <button class="filter-btn" onclick="filter('miss',this)">✗ Misses ({misses})</button>
      <button class="filter-btn" onclick="filter('pending',this)">· Pending ({pending})</button>
      <button class="filter-btn" onclick="filter('convergence',this)">⚡ Convergence</button>
    </div>
    <table id="sig-table">
      <tr><th>Date (BE)</th><th>Source</th><th>Direction</th><th>Signal</th><th>ETFs</th><th>Confidence</th><th>Result</th><th></th></tr>
      {signal_rows}
    </table>
  </div>
</div>

<script>
function toggleR(i) {{
  var rr=document.getElementById('rr'+i), ei=document.getElementById('ei'+i);
  var open=rr.style.display!=='none';
  rr.style.display=open?'none':'table-row';
  ei.style.transform=open?'':'rotate(90deg)';
}}
function filter(f,btn) {{
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#sig-table .signal-row').forEach(function(row) {{
    var idx=row.getAttribute('onclick').match(/[0-9]+/)[0];
    var rr=document.getElementById('rr'+idx);
    var show=false;
    if(f==='all') show=true;
    else if(f==='convergence') show=!!row.querySelector('.src-convergence');
    else show=row.classList.contains(f);
    row.style.display=show?'':'none';
    if(rr&&!show) rr.style.display='none';
  }});
}}
</script>
</body>
</html>"""

    with open("history.html", "w") as f:
        f.write(html)
    print("history.html generated")


# ── INDEX.HTML ────────────────────────────────────────────────────────────────
def generate_index_html():
    with open("index.html", "w") as f:
        f.write("""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url=live.html">
<title>Stocazzo</title></head>
<body><a href="live.html">Go to Live Dashboard →</a></body></html>""")
    print("index.html generated")


# ── FETCH ETF QUOTES ──────────────────────────────────────────────────────────
def _fetch_etf_quotes():
    quotes  = {}
    tickers = [t for t, n, e, theme in KEY_ETFS]

    if TWELVEDATA_KEY:
        for ticker in tickers:
            try:
                r = requests.get(
                    "https://api.twelvedata.com/quote",
                    params={"symbol": ticker, "apikey": TWELVEDATA_KEY},
                    timeout=6,
                )
                if r.status_code == 200:
                    data  = r.json()
                    price = float(data.get("close", 0) or 0)
                    pct   = float(data.get("percent_change", 0) or 0)
                    if price:
                        quotes[ticker] = {"price": price, "pct": pct}
            except Exception as e:
                print(f"Twelve Data quote {ticker}: {e}")
                break

    if FINNHUB_KEY:
        for t, n, e, theme in KEY_ETFS:
            if t in quotes:
                continue
            try:
                r = requests.get(
                    f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_KEY}",
                    timeout=4,
                )
                if r.status_code == 200:
                    q     = r.json()
                    price = q.get("c", 0)
                    prev  = q.get("pc", 0)
                    if price and prev:
                        pct = ((price - prev) / prev) * 100
                        quotes[t] = {"price": price, "pct": pct}
            except Exception:
                pass

    return quotes
