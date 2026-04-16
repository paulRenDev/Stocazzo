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
    """Renders virtual portfolio section: open positions + platform score."""
    from helpers import urgency_color

    perf       = get_platform_score(seen_data)
    open_pos   = get_open_positions(seen_data)
    closed_pos = get_closed_positions(seen_data, limit=10)

    # Platform score bar
    roll_rate  = perf.get("rolling_rate")
    roll_hits  = perf.get("rolling_hits", 0)
    roll_total = perf.get("rolling_total", 0)
    total_pnl  = perf.get("total_pnl", 0.0)
    best_theme = perf.get("best_theme", "")
    best_trate = perf.get("best_theme_rate", 0)

    if roll_rate is not None:
        bar_w     = int(roll_rate * 100)
        bar_color = "#007a5e" if roll_rate >= 0.6 else "#b06000" if roll_rate >= 0.4 else "#cc2222"
        rate_str  = f"{roll_rate:.0%}"
        score_html = (
            f"<div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px;'>"
            f"<div>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);margin-bottom:4px;'>Rolling hit rate (last {roll_total} positions)</div>"
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<div style='background:#e0e0d8;border-radius:2px;height:8px;width:120px;'>"
            f"<div style='background:{bar_color};height:8px;border-radius:2px;width:{bar_w}%;'></div></div>"
            f"<span style='font-family:var(--mono);font-size:16px;font-weight:600;color:{bar_color};'>{rate_str}</span>"
            f"<span style='font-family:var(--mono);font-size:11px;color:var(--muted);'>({roll_hits}/{roll_total} hits)</span>"
            f"</div></div>"
            f"<div style='border-left:1px solid var(--border2);padding-left:16px;'>"
            f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);margin-bottom:4px;'>Total virtual P&amp;L</div>"
            f"<div style='font-size:16px;font-weight:600;font-family:var(--mono);"
            f"color:{'var(--green)' if total_pnl >= 0 else 'var(--red);'}'>"
            f"{'+'if total_pnl>=0 else ''}€{total_pnl:.0f}</div>"
            f"</div>"
        )
        if best_theme:
            score_html += (
                f"<div style='border-left:1px solid var(--border2);padding-left:16px;'>"
                f"<div style='font-size:10px;font-family:var(--mono);color:var(--muted);margin-bottom:4px;'>Best theme</div>"
                f"<div style='font-size:14px;font-weight:600;text-transform:capitalize;color:var(--green);'>"
                f"{best_theme.replace('_',' ')} ({best_trate:.0%})</div>"
                f"</div>"
            )
        score_html += "</div>"
    else:
        score_html = (
            "<div style='font-size:12px;color:var(--muted);font-family:var(--mono);padding:8px 0;'>"
            "No closed positions yet — score builds after first 5-day checks</div>"
        )

    # Open positions table
    if open_pos:
        pos_rows = ""
        for p in open_pos:
            pct   = p.get("current_pct", 0)
            pnl   = p.get("current_pnl", 0)
            pc    = "var(--green)" if pct >= 0 else "var(--red)"
            icon  = "▲" if pct >= 0 else "▼"
            side  = p.get("side", "BUY")
            sc    = "var(--green)" if side == "BUY" else "var(--red)"

            # Check badges
            c4h  = p.get("check_4h")
            c24h = p.get("check_24h")
            check_badges = ""
            for label, chk in [("4h", c4h), ("24h", c24h)]:
                if chk:
                    chk_color = "var(--green)" if chk["hit"] else "var(--red)"
                    check_badges += (
                        f"<span style='font-size:10px;font-family:var(--mono);padding:1px 6px;"
                        f"border-radius:3px;background:{chk_color}15;color:{chk_color};margin-right:3px;'>"
                        f"{label}: {chk['pct']:+.1f}%</span>"
                    )

            pos_rows += (
                f"<tr>"
                f"<td style='font-family:var(--mono);font-size:12px;font-weight:700;color:{sc};padding:8px 10px;'>{side}</td>"
                f"<td style='font-family:var(--mono);font-size:13px;font-weight:700;padding:8px 10px;'>"
                f"<a href='https://finance.yahoo.com/quote/{p['ticker']}' target='_blank' "
                f"style='color:var(--green);text-decoration:none;'>{p['ticker']}</a></td>"
                f"<td style='font-size:12px;text-transform:capitalize;padding:8px 10px;'>{p['theme'].replace('_',' ')}</td>"
                f"<td style='font-family:var(--mono);font-size:12px;padding:8px 10px;'>€1,000 @ ${p['entry_price']:.2f}</td>"
                f"<td style='font-family:var(--mono);font-size:12px;font-weight:600;color:{pc};padding:8px 10px;'>"
                f"{icon} {abs(pct):.2f}% · {'+'if pnl>=0 else ''}€{pnl:.0f}</td>"
                f"<td style='font-size:11px;color:var(--muted);font-family:var(--mono);padding:8px 10px;'>{p.get('age','')}</td>"
                f"<td style='padding:8px 10px;'>{check_badges}</td>"
                f"</tr>"
            )
        open_html = (
            f"<div style='margin-bottom:8px;font-size:10px;font-family:var(--mono);"
            f"color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;'>"
            f"Open positions ({len(open_pos)})</div>"
            f"<table style='width:100%;border-collapse:collapse;background:var(--surface);"
            f"border:1px solid var(--border);font-size:13px;margin-bottom:16px;'>"
            f"<tr style='background:#f0f0eb;'>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Side</th>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Ticker</th>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Theme</th>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Entry</th>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>P&amp;L</th>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Age</th>"
            f"<th style='padding:6px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Checks</th>"
            f"</tr>{pos_rows}</table>"
        )
    else:
        open_html = (
            "<div style='font-size:12px;color:var(--muted);font-family:var(--mono);"
            "padding:12px 0;'>No open positions — opens when advice fires with BUY or SELL direction</div>"
        )

    # Closed positions (recent)
    if closed_pos:
        closed_rows = ""
        for p in closed_pos:
            fpct  = p.get("final_pct", 0) or 0
            fpnl  = p.get("final_pnl", 0) or 0
            pc    = "var(--green)" if fpct >= 0 else "var(--red)"
            icon  = "✓" if fpct >= 2 else "✗"
            ic    = "var(--green)" if fpct >= 2 else "var(--red)"
            side  = p.get("side", "BUY")
            sc    = "var(--green)" if side == "BUY" else "var(--red)"
            closed_rows += (
                f"<tr>"
                f"<td style='font-family:var(--mono);font-size:12px;font-weight:700;color:{sc};padding:6px 10px;'>{side}</td>"
                f"<td style='font-family:var(--mono);font-size:13px;font-weight:700;padding:6px 10px;'>{p['ticker']}</td>"
                f"<td style='font-size:12px;text-transform:capitalize;padding:6px 10px;'>{p['theme'].replace('_',' ')}</td>"
                f"<td style='font-family:var(--mono);font-size:12px;font-weight:600;color:{pc};padding:6px 10px;'>"
                f"{'+' if fpct>=0 else ''}{fpct:.2f}% · {'+'if fpnl>=0 else ''}€{fpnl:.0f}</td>"
                f"<td style='font-size:12px;font-weight:600;color:{ic};padding:6px 10px;'>{icon}</td>"
                f"<td style='font-size:11px;color:var(--muted);font-family:var(--mono);padding:6px 10px;'>{p.get('entry_be','')[:10]}</td>"
                f"</tr>"
            )
        closed_html = (
            f"<div style='margin-bottom:8px;font-size:10px;font-family:var(--mono);"
            f"color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;'>"
            f"Recent closed positions</div>"
            f"<table style='width:100%;border-collapse:collapse;background:var(--surface);"
            f"border:1px solid var(--border);font-size:13px;'>"
            f"<tr style='background:#f0f0eb;'>"
            f"<th style='padding:5px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Side</th>"
            f"<th style='padding:5px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Ticker</th>"
            f"<th style='padding:5px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Theme</th>"
            f"<th style='padding:5px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Result</th>"
            f"<th style='padding:5px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Hit</th>"
            f"<th style='padding:5px 10px;font-size:10px;font-family:var(--mono);color:var(--muted);text-transform:uppercase;text-align:left;'>Date</th>"
            f"</tr>{closed_rows}</table>"
        )
    else:
        closed_html = ""

    return (
        f"<div style='background:var(--surface);border:1px solid var(--border);"
        f"border-radius:4px;padding:16px;'>"
        f"{score_html}"
        f"{open_html}"
        f"{closed_html}"
        f"</div>"
    )


# ── LIVE.HTML ─────────────────────────────────────────────────────────────────
def generate_live_html(seen_data, all_alerts, advice_cards=None, skip_prices=False):
    etf_quotes     = _fetch_etf_quotes()
    active_tickers = {t for a in all_alerts for t, n, e in a.get("etfs", [])}
    advice_cards_list = advice_cards or []
    advice_html       = format_advice_html_section(advice_cards_list)
    portfolio_section = _portfolio_html(seen_data)

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
            f"<span style='font-family:var(--mono);font-size:10px;color:var(--dim);margin-left:auto;'>{now_be()[:16]}</span>"
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

    # ── ETF WATCHLIST ─────────────────────────────────────────────────────────
    etf_grid = ""
    for t, n, e, theme in KEY_ETFS:
        is_active    = t in active_tickers
        border_style = "border-left:3px solid var(--green);" if is_active else ""
        active_dot   = "<span style='width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;'></span>" if is_active else ""
        q            = etf_quotes.get(t)
        price_html   = ""
        if q:
            pct_color = "var(--green)" if q["pct"] > 0 else "var(--red)"
            pct_icon  = "▲" if q["pct"] > 0 else "▼"
            price_html = (
                f"<div style='display:flex;justify-content:space-between;align-items:baseline;margin-top:6px;'>"
                f"<span style='font-family:var(--mono);font-weight:600;font-size:13px;'>${q['price']:.2f}</span>"
                f"<span style='font-family:var(--mono);font-size:11px;font-weight:600;color:{pct_color};'>"
                f"{pct_icon} {abs(q['pct']):.2f}%</span></div>"
            )
        etf_grid += (
            f"<div style='background:var(--surface);border:1px solid var(--border);padding:10px;"
            f"border-radius:4px;{border_style}'>"
            f"<div style='display:flex;align-items:center;justify-content:space-between;'>"
            f"<a href='{etf_yahoo_url(t,e)}' target='_blank' style='font-family:var(--mono);font-size:14px;"
            f"font-weight:700;color:var(--green);text-decoration:none;'>{t}</a>{active_dot}</div>"
            f"<div style='font-size:12px;color:var(--muted);margin:2px 0;'>{n}</div>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-top:3px;'>"
            f"<span style='font-family:var(--mono);font-size:11px;color:var(--dim);'>{e}</span>"
            f"<span style='font-size:10px;background:#f0f0eb;color:var(--muted);padding:1px 6px;border-radius:3px;'>{theme}</span></div>"
            f"{price_html}"
            f"<div style='display:flex;gap:4px;margin-top:6px;'>"
            f"<a href='{etf_yahoo_url(t,e)}' target='_blank' style='font-family:var(--mono);font-size:10px;"
            f"padding:2px 7px;border:1px solid var(--border);border-radius:3px;text-decoration:none;color:var(--blue);'>Yahoo</a>"
            f"<a href='{etf_google_url(t,e)}' target='_blank' style='font-family:var(--mono);font-size:10px;"
            f"padding:2px 7px;border:1px solid var(--border);border-radius:3px;text-decoration:none;color:var(--muted);'>Google</a>"
            f"</div></div>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    <div class="section-title">Cumulative advice ({len(advice_cards_list)} themes) — all sources combined</div>
    {advice_html}
  </div>

  <div class="section">
    <div class="section-title">Virtual portfolio — €1,000 per advice · adaptive confidence score</div>
    {portfolio_section}
  </div>

  <div class="section">
    <div class="section-title">Current signals ({len(all_alerts)})</div>
    {alert_cards}
  </div>

  <div class="section">
    <div class="section-title">ETF watchlist</div>
    <div class="etf-grid">{etf_grid}</div>
  </div>
</div>
</body>
</html>"""

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

        if verified is True:
            sc, si, sl = "hit",     "✓", f"HIT {pct:+.1f}%" if pct is not None else "HIT"
        elif verified is False:
            sc, si, sl = "miss",    "✗", f"MISS {pct:+.1f}%" if pct is not None else "MISS"
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
          <td style="max-width:260px;"><span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{h.get('title','')[:80]}</span></td>
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
