"""
output/mail_builder.py — CronyPony v7
Builds and sends HTML emails. No scan logic.
Mailing list: lijst van e-mailadressen in ALERT_EMAIL (kommagescheiden voor meerdere).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_USER, GMAIL_PASSWORD, ALERT_EMAIL, SOURCE_CREDIBILITY, SITE_URL
from helpers import now_utc, now_be, convert_et_to_cet, urgency_color
from etf_mapper import etf_yahoo_url, etf_google_url
from scoring import get_source_hit_rate


# ── HELPERFUNCTIES VOOR HTML ──────────────────────────────────────────────────
def _etf_html(etfs):
    if not etfs:
        return "<span style='color:#9a9a9a;font-size:12px;'>No ETF match</span>"
    items = []
    for t, n, e in etfs:
        yahoo  = etf_yahoo_url(t, e)
        google = etf_google_url(t, e)
        items.append(
            f"<div style='display:flex;align-items:center;gap:8px;margin:3px 0;'>"
            f"<span style='background:#e8f4f0;color:#007a5e;font-family:monospace;font-size:12px;"
            f"font-weight:700;padding:3px 10px;border-radius:3px;min-width:56px;text-align:center;'>{t}</span>"
            f"<span style='font-size:12px;color:#6b6b6b;flex:1;'>{n} <span style='color:#bbb;'>({e})</span></span>"
            f"<a href='{yahoo}' style='font-size:11px;color:#1a5fb5;padding:2px 7px;border:1px solid #1a5fb5;"
            f"border-radius:3px;text-decoration:none;font-family:monospace;'>Yahoo ↗</a>"
            f"<a href='{google}' style='font-size:11px;color:#888;padding:2px 7px;border:1px solid #ddd;"
            f"border-radius:3px;text-decoration:none;font-family:monospace;'>Google ↗</a>"
            f"</div>"
        )
    return "".join(items)


def _reasoning_html(reasoning, seen_data):
    if not reasoning:
        return ""

    why        = reasoning.get("why", "")
    sig_type   = reasoning.get("signal_type", "")
    confidence = reasoning.get("confidence", 0)
    sw         = reasoning.get("source_weight", 1)
    hit_rate   = reasoning.get("hit_rate", "onbekend")
    caveat     = reasoning.get("caveat", "")
    breakdown  = reasoning.get("breakdown", [])

    bar_width = min(100, max(5, confidence))
    bar_color = "#007a5e" if confidence >= 65 else "#b06000" if confidence >= 45 else "#cc2222"

    breakdown_html = ""
    if breakdown:
        rows = ""
        for b in breakdown:
            d_color = "#007a5e" if "BUY" in b.get("direction", "").upper() else \
                      "#cc2222" if "SELL" in b.get("direction", "").upper() else "#b06000"
            rows += (
                f"<tr>"
                f"<td style='font-family:monospace;font-size:11px;padding:3px 8px;color:#1a1a1a;"
                f"border-bottom:1px solid #f0f0eb;'>{b['source']}</td>"
                f"<td style='font-family:monospace;font-size:11px;padding:3px 8px;color:{d_color};"
                f"border-bottom:1px solid #f0f0eb;font-weight:600;'>{b['direction']}</td>"
                f"<td style='font-family:monospace;font-size:11px;padding:3px 8px;color:#007a5e;"
                f"border-bottom:1px solid #f0f0eb;font-weight:600;'>{b['points']}ptn</td>"
                f"<td style='font-family:monospace;font-size:10px;padding:3px 8px;color:#9a9a9a;"
                f"border-bottom:1px solid #f0f0eb;'>{b['reasoning']}</td>"
                f"</tr>"
            )
        breakdown_html = (
            f"<div style='margin-top:8px;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#6b6b6b;text-transform:uppercase;"
            f"letter-spacing:0.06em;margin-bottom:4px;'>Score breakdown</div>"
            f"<table style='width:100%;border-collapse:collapse;background:#fafaf8;border:1px solid #f0f0eb;'>"
            f"<tr style='background:#f5f5f0;'>"
            f"<td style='font-size:10px;font-family:monospace;color:#9a9a9a;padding:2px 8px;'>Bron</td>"
            f"<td style='font-size:10px;font-family:monospace;color:#9a9a9a;padding:2px 8px;'>Signaal</td>"
            f"<td style='font-size:10px;font-family:monospace;color:#9a9a9a;padding:2px 8px;'>Punten</td>"
            f"<td style='font-size:10px;font-family:monospace;color:#9a9a9a;padding:2px 8px;'>Reasoning</td>"
            f"</tr>{rows}</table></div>"
        )

    caveat_html = (
        f"<div style='font-size:11px;color:#b06000;margin-top:6px;font-family:monospace;'>⚠ {caveat}</div>"
        if caveat else ""
    )

    return (
        f"<div style='background:#f8f8f4;border:1px solid #e8e8e0;border-radius:4px;"
        f"padding:10px 12px;margin-bottom:10px;'>"
        f"<div style='font-size:10px;font-family:monospace;color:#9a9a9a;text-transform:uppercase;"
        f"letter-spacing:0.06em;margin-bottom:6px;'>Why this recommendation</div>"
        f"<div style='font-size:12px;color:#1a1a1a;margin-bottom:6px;line-height:1.5;'>{why}</div>"
        f"<div style='margin-bottom:8px;'>"
        f"<span style='font-size:10px;font-family:monospace;color:#9a9a9a;margin-right:8px;'>Signal type</span>"
        f"<span style='font-size:11px;font-family:monospace;color:#1a1a1a;'>{sig_type}</span></div>"
        f"<div style='margin-bottom:8px;'>"
        f"<span style='font-size:10px;font-family:monospace;color:#9a9a9a;margin-right:8px;'>Hit rate</span>"
        f"<span style='font-size:11px;font-family:monospace;color:#007a5e;'>{hit_rate}</span></div>"
        f"<div style='margin-bottom:8px;'>"
        f"<span style='font-size:10px;font-family:monospace;color:#9a9a9a;margin-right:8px;'>Weight</span>"
        f"<span style='font-size:11px;font-family:monospace;color:#1a1a1a;'>{'★' * sw}{'☆' * (5-sw)} ({sw}/5)</span></div>"
        f"<div style='background:#e8e8e0;border-radius:2px;height:4px;margin-bottom:4px;'>"
        f"<div style='background:{bar_color};height:4px;border-radius:2px;width:{bar_width}%;'></div></div>"
        f"<div style='font-size:10px;font-family:monospace;color:{bar_color};'>Confidence: {confidence}%</div>"
        f"{breakdown_html}{caveat_html}</div>"
    )


def _action_advice(alert):
    source    = alert.get("source", "")
    direction = alert.get("direction", "").upper()
    etfs      = alert.get("etfs", [])
    etf_names = ", ".join(e[0] for e in etfs[:2]) if etfs else "geen ETF match"

    if source == "CONVERGENCE":
        return alert.get("_conv_action", "WATCH"), alert.get("_conv_color", "#b06000"), alert.get("_conv_advice", "Multi-bron convergentie")

    if source in ("Polymarket", "Kalshi"):
        if "YES" in direction:
            return "BUY", "#007a5e", f"Markt prijst positief resultaat in — {etf_names}"
        if "NO" in direction:
            return "REDUCE / HEDGE", "#cc2222", "Markt prijst negatief resultaat in — verlaag exposure"
        return "WATCH", "#b06000", f"Volg kansen — {etf_names}"

    if source == "Dark Pool":
        if "ACCUMULATIE" in direction:
            return "BUY", "#007a5e", f"Institutionele accumulatie — {etf_names}"
        return "WATCH", "#b06000", f"Sectorflow — volg {etf_names} voor entry"

    if source in ("Congress", "Pelosi Tracker"):
        if "BUY" in direction:
            return "ACCUMULEER", "#007a5e", f"Congres koopt — {etf_names}"
        if "SELL" in direction:
            return "VERLAAG", "#cc2222", f"Congres verkoopt — trim exposure"
        return "WATCH", "#b06000", f"Volg congresactiviteit — {etf_names}"

    return "WATCH", "#b06000", f"Volg — {etf_names}"


# ── HOOFDFUNCTIE ──────────────────────────────────────────────────────────────
def send_email(alerts, backcheck_results, seen_data):
    """Bouwt en verstuurt HTML mail naar de mailing list."""

    if not alerts and not backcheck_results:
        return

    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("Email: geen credentials — enkel console output")
        for a in alerts:
            print(f"\n[{a['source']}] {a['title']}")
        return

    # Bouw alert rijen
    rows = ""
    for a in alerts:
        c       = urgency_color(a["urgency"])
        is_conv = a["source"] == "CONVERGENCE"

        src_badge = (
            f"<span style='background:#1a1a1a;color:#fff;font-size:11px;font-weight:700;"
            f"padding:3px 12px;border-radius:3px;font-family:monospace;'>{a['source'].upper()}</span>"
            if is_conv else
            f"<span style='background:{c};color:white;font-size:10px;font-weight:700;"
            f"padding:2px 8px;border-radius:3px;font-family:monospace;'>{a['source'].upper()}</span>"
        )

        action_label, action_color, action_desc = _action_advice(a)

        rows += (
            f"<tr><td style='padding:16px;border-bottom:1px solid #f0f0eb;vertical-align:top;"
            f"{'background:#fafafa;' if is_conv else ''}'>"
            f"<div style='display:flex;gap:5px;margin-bottom:8px;flex-wrap:wrap;align-items:center;'>"
            f"{src_badge}"
            f"<span style='background:#f0f0eb;color:#888;font-size:10px;padding:2px 7px;"
            f"border-radius:3px;font-family:monospace;'>{a['type']}</span>"
            f"<span style='background:{c}22;color:{c};font-size:10px;font-weight:600;"
            f"padding:2px 8px;border-radius:3px;font-family:monospace;'>{a['direction']}</span>"
            f"<span style='background:{c}15;color:{c};font-size:10px;padding:2px 7px;"
            f"border-radius:3px;font-family:monospace;'>{a['urgency']}</span>"
            f"</div>"
            f"<div style='font-size:14px;font-weight:600;color:#1a1a1a;margin-bottom:4px;line-height:1.4;'>"
            f"{convert_et_to_cet(a['title'])}</div>"
            f"<div style='font-size:12px;color:#6b6b6b;margin-bottom:10px;line-height:1.5;'>"
            f"{convert_et_to_cet(a['detail'])}</div>"
            f"<div style='background:{action_color}12;border-left:3px solid {action_color};"
            f"padding:8px 12px;margin-bottom:10px;border-radius:0 4px 4px 0;'>"
            f"<div style='font-size:10px;font-family:monospace;color:{action_color};"
            f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;'>Recommendation</div>"
            f"<div style='font-size:14px;font-weight:700;color:{action_color};font-family:monospace;'>"
            f"{action_label}</div>"
            f"<div style='font-size:12px;color:#6b6b6b;margin-top:2px;'>{action_desc}</div></div>"
            f"{_reasoning_html(a.get('reasoning', {}), seen_data)}"
            f"<div style='margin-bottom:8px;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#007a5e;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:5px;'>ETFs</div>"
            f"{_etf_html(a['etfs'])}</div>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-top:8px;padding-top:8px;border-top:1px solid #f0f0eb;'>"
            f"<a href='{a['link']}' style='font-size:11px;color:#1a5fb5;text-decoration:none;"
            f"font-family:monospace;'>View source →</a>"
            f"<span style='font-size:10px;font-family:monospace;color:#c0c0b8;'>{a['keywords']}</span>"
            f"</div></td></tr>"
        )

    # Backcheck sectie
    backcheck_html = ""
    if backcheck_results:
        bc_rows = ""
        for bc in backcheck_results:
            color = "#007a5e" if bc.get("hit") else "#cc2222" if bc.get("hit") is False else "#b06000"
            icon  = "✓" if bc.get("hit") else "✗" if bc.get("hit") is False else "~"
            bc_rows += (
                f"<tr>"
                f"<td style='font-size:11px;font-family:monospace;padding:4px 8px;color:{color};font-weight:700;'>{icon}</td>"
                f"<td style='font-size:11px;font-family:monospace;padding:4px 8px;color:#1a1a1a;'>{bc['source']}</td>"
                f"<td style='font-size:11px;font-family:monospace;padding:4px 8px;color:#1a1a1a;'>{bc['ticker']} {bc['direction']}</td>"
                f"<td style='font-size:11px;font-family:monospace;padding:4px 8px;color:{color};font-weight:600;'>{bc['pct_change']:+.1f}% in {bc['days']}d</td>"
                f"<td style='font-size:11px;font-family:monospace;padding:4px 8px;color:#9a9a9a;'>${bc['price_entry']:.2f} → ${bc['price_now']:.2f}</td>"
                f"</tr>"
            )

        stats_spans = ""
        for src, stat in seen_data.get("stats", {}).items():
            total = stat["hits"] + stat["misses"]
            rate  = f"{stat['hits']/total:.0%}" if total else "n/a"
            stats_spans += (
                f"<span style='font-family:monospace;font-size:11px;margin-right:16px;'>"
                f"<b>{src}</b>: {rate} ({stat['hits']}/{total})</span>"
            )

        backcheck_html = (
            f"<tr><td style='padding:16px;background:#f5f5f0;border-bottom:1px solid #e8e8e0;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#6b6b6b;text-transform:uppercase;"
            f"letter-spacing:0.06em;margin-bottom:8px;'>Backcheck results (5-day verification)</div>"
            f"<table style='width:100%;border-collapse:collapse;'>{bc_rows}</table>"
            f"<div style='margin-top:10px;padding-top:8px;border-top:1px solid #e8e8e0;'>"
            f"<div style='font-size:10px;font-family:monospace;color:#9a9a9a;margin-bottom:4px;'>"
            f"Updated hit rates:</div>{stats_spans}</div></td></tr>"
        )

    html = (
        f"<html><body style='font-family:Arial,sans-serif;background:#f5f5f0;margin:0;padding:20px;'>"
        f"<div style='max-width:680px;margin:0 auto;background:white;border:1px solid #d8d8d0;"
        f"border-radius:8px;overflow:hidden;'>"
        f"<div style='background:#007a5e;padding:20px 24px;'>"
        f"<div style='font-family:monospace;font-size:10px;color:#9fe1cb;letter-spacing:0.12em;'>"
        f"STOCAZZO // SIGNAL TRACKER</div>"
        f"<div style='font-size:22px;font-weight:300;color:white;'>"
        f"{len(alerts)} nieuw{'e' if len(alerts) != 1 else ''} signaal{'en' if len(alerts) != 1 else ''}</div>"
        f"<div style='font-size:12px;color:#9fe1cb;margin-top:4px;font-family:monospace;'>"
        f"{now_utc()} &nbsp;·&nbsp; {now_be()}</div></div>"
        f"<table style='width:100%;border-collapse:collapse;'>{rows}{backcheck_html}</table>"
        f"<div style='padding:16px 24px;background:#f5f5f0;border-top:1px solid #d8d8d0;'>"
        f"<div style='font-size:11px;color:#9a9a9a;font-family:monospace;'>"
        f"Sources: Polymarket · Kalshi · Dark Pool · Congress · Pelosi Tracker · Options Flow<br>"
        f"<a href='{SITE_URL}' style='color:#1a5fb5;'>Open Stocazzo Signal Tracker →</a>"
        f"</div></div></div></body></html>"
    )

    # Mailing list: ALERT_EMAIL kan kommagescheiden zijn voor meerdere ontvangers
    recipients = [e.strip() for e in ALERT_EMAIL.split(",") if e.strip()]

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"Crony Signal: {len(alerts)} new signal{'s' if len(alerts) != 1 else ''} — {now_be()}"
        )
        msg["From"] = GMAIL_USER
        msg["To"]   = ", ".join(recipients)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_USER, recipients, msg.as_string())

        print(f"Mail verstuurd naar: {', '.join(recipients)}")

    except Exception as e:
        print(f"Mail fout: {e}")
