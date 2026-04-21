"""
main.py — Stocazzo v7.2
Orchestrator. Calls everything, does nothing else itself.

v7.1: Stock enrichment — yfinance technical context passed to analyst panel.
v7.2: Signal volume expansion:
      - scan_news_feeds: 20+ RSS feeds (Reuters, AP, MarketWatch, Yahoo, Google News, etc.)
      - scan_polymarket_expanded: all financial Polymarket categories (not just politics)
      - scan_capitol_trades + scan_openinsider: replace dead congress/pelosi/darkpool
      - scan_benzinga: replaces blocked options flow
      Dropped: scan_congress (403), scan_pelosi (broken regex),
               scan_dark_pool (cloud blocked), scan_unusual_whales (cloud blocked).
"""
from helpers import now_utc
from state import load_seen, add_to_history, commit_seen
from scoring import run_backcheck, queue_for_backcheck, update_history_backcheck

# Crony scanners
from scanners.polymarket_expanded import scan_polymarket_expanded   # expanded (all categories)
from scanners.polymarket          import scan_polymarket             # original (politics, keep as fallback)
from scanners.kalshi              import scan_kalshi
from scanners.edgar               import scan_edgar
from scanners.truthsocial         import scan_truthsocial
from scanners.social              import scan_reddit

# New reliable scanners (v7.2)
from scanners.capitol_trades_and_openinsider import scan_capitol_trades, scan_openinsider
from scanners.benzinga_rss                   import scan_benzinga
from scanners.news_feeds                     import scan_news_feeds

# Macro scanners
from scanners.macro import scan_macro

# Stock enrichment (v7.1)
from scanners.stock_analyzer import enrich_with_stock_data

# Core engines
from convergence     import build_convergence
from output.advice   import build_advice, log_advice_for_scoring, run_advice_backcheck
from output.analysts import build_analyst_panel
from portfolio       import open_position, update_positions

# Output
from output.page_builder import generate_live_html, generate_history_html, generate_index_html, generate_sources_html
from output.mail_builder import send_email


def main():
    print(f"=== Stocazzo v7.2 started: {now_utc()} ===")

    seen_data = load_seen()
    print(f"Previously seen: {len(seen_data.get('ids', []))} items | "
          f"Pending checks: {len(seen_data.get('pending_checks', []))} | "
          f"Advice checks: {len(seen_data.get('advice_checks', []))}")

    # 1. Run all backchecks first
    seen_data, backcheck_results = run_backcheck(seen_data)
    if backcheck_results:
        print(f"Signal backcheck: {len(backcheck_results)} verified")
        update_history_backcheck(backcheck_results, seen_data)

    seen_data, advice_backcheck = run_advice_backcheck(seen_data)
    if advice_backcheck:
        print(f"Advice backcheck: {len(advice_backcheck)} results")

    # 2. Run all scanners
    all_alerts = []

    # ── Crony signals (pre-news, highest weight) ───────────────────────────────
    pm_expanded = scan_polymarket_expanded(seen_data)
    if pm_expanded:
        all_alerts += pm_expanded
    else:
        # Fallback to original if expanded fails
        all_alerts += scan_polymarket(seen_data)

    all_alerts += scan_kalshi(seen_data)
    all_alerts += scan_edgar(seen_data)
    all_alerts += scan_capitol_trades(seen_data)
    all_alerts += scan_openinsider(seen_data)

    # ── Social / real-time ────────────────────────────────────────────────────
    all_alerts += scan_truthsocial(seen_data)
    all_alerts += scan_reddit(seen_data)

    # ── Macro + news feeds (volume layer) ────────────────────────────────────
    all_alerts += scan_macro(seen_data)          # existing GDELT + RSS + Fear&Greed
    all_alerts += scan_news_feeds(seen_data)     # 20+ additional RSS feeds
    all_alerts += scan_benzinga(seen_data)       # market-moving news for Tape Reader

    print(f"Raw signals before enrichment: {len(all_alerts)}")

    # 3. Enrich detected tickers with technical analysis (yfinance)
    stock_data = enrich_with_stock_data(all_alerts)
    print(f"Stock enrichment: {len(stock_data)} tickers analysed")

    # 4. Convergence analysis (multi-source signal overlap)
    convergence = build_convergence(all_alerts, seen_data)
    if convergence:
        all_alerts = [convergence] + all_alerts
        print(f"Convergence alert: {convergence['title']}")

    print(f"Total signals: {len(all_alerts)}")

    # 5. Build cumulative advice from ALL signals
    advice_cards = build_advice(all_alerts, seen_data)
    print(f"Advice cards generated: {len(advice_cards)}")

    # 5b. Build analyst panel verdict (with stock enrichment context)
    analyst_verdicts, panel_advice = build_analyst_panel(all_alerts, seen_data, stock_data)
    active = sum(1 for v in analyst_verdicts if v["verdict"] != "NEUTRAL")
    print(f"Analyst panel: {active}/5 analysts with verdict — {panel_advice['direction']} ({panel_advice['confidence']}%)")

    # 6. Open virtual positions based on PANEL verdict
    panel_dir  = panel_advice.get("direction", "NEUTRAL")
    panel_conf = panel_advice.get("confidence", 0)
    panel_etfs = panel_advice.get("top_etfs", [])

    if panel_dir in ("BULLISH", "BEARISH") and panel_conf >= 40 and panel_etfs:
        etf_to_sector = {
            # Energy
            "XLE":"Energy","IEO":"Energy","XOM":"Energy","CVX":"Energy",
            "USO":"Oil","BNO":"Oil","UNG":"Natural Gas","VDE":"Energy",
            "OIH":"Oil Services","MLPA":"Energy Pipelines",
            # Defense
            "ITA":"Defense","XAR":"Defense","LMT":"Defense",
            "RTX":"Defense","NOC":"Defense","BA":"Defense","GD":"Defense",
            # Renewables
            "INRG":"Renewables","ICLN":"Renewables","TAN":"Solar","FAN":"Wind",
            "KRBN":"Carbon",
            # Precious metals
            "GLD":"Gold","IAU":"Gold","IGLN":"Gold","GDX":"Gold Miners",
            "SLV":"Silver","SIVR":"Silver",
            # Tech
            "QQQ":"Tech","XLK":"Tech","VGT":"Tech",
            "SOXX":"Semiconductors","SMH":"Semiconductors",
            "NVDA":"Semiconductors","TSM":"Semiconductors","INTC":"Semiconductors",
            "BOTZ":"AI/Robotics","AIQ":"AI","ROBO":"Robotics",
            "CLOU":"Cloud","IGV":"Software",
            "CIBR":"Cybersecurity","HACK":"Cybersecurity","BUG":"Cybersecurity",
            # Crypto
            "IBIT":"Crypto","FBTC":"Crypto","GBTC":"Crypto",
            "ETHA":"Ethereum","COIN":"Crypto","MSTR":"Crypto",
            # Bonds/Rates
            "TLT":"Bonds","IEF":"Bonds","EDV":"Bonds","SHY":"Short Bonds",
            "TBT":"Short Bonds","TIP":"TIPS","IBTM":"Euro Bonds",
            "HYG":"High Yield","LQD":"Investment Grade",
            # Commodities
            "GSG":"Commodities","DBC":"Commodities","PDBC":"Commodities",
            "LIT":"Lithium","COPX":"Copper","REMX":"Rare Earth",
            "URA":"Uranium","URNM":"Uranium",
            "DBA":"Agriculture","MOO":"Agriculture","WEAT":"Wheat",
            # Financials
            "XLF":"Financials","VFH":"Financials","KBE":"Banking",
            "KRE":"Regional Banks","JPM":"Financials","GS":"Financials",
            # Healthcare
            "XLV":"Healthcare","VHT":"Healthcare","IBB":"Biotech",
            "XBI":"Biotech","IHE":"Pharma","ARKG":"Genomics",
            # Broad market
            "SPY":"Broad Market","VOO":"Broad Market","IWM":"Small Cap",
            "EEM":"Emerging Markets","VWO":"Emerging Markets",
            "MCHI":"China","KWEB":"China Tech","FXI":"China",
            "INDA":"India","EWJ":"Japan","VGK":"Europe","EZU":"Eurozone",
            "KSA":"Saudi Arabia","AFK":"Africa","EZA":"South Africa",
            # Real estate
            "VNQ":"Real Estate","IYR":"Real Estate",
            # Infrastructure
            "IGF":"Infrastructure","PAVE":"Infrastructure",
            # Individual stocks
            "TSLA":"EV/Tech","PLTR":"AI/Defense","AMZN":"Tech",
            "AAPL":"Tech","META":"Tech","GOOGL":"Tech","MSFT":"Tech",
        }
        active_analysts = [v["name"] for v in (analyst_verdicts or [])
                           if v.get("verdict") == panel_dir and v.get("conviction", 0) >= 40]
        analyst_str = " + ".join(active_analysts[:2]) if active_analysts else "Panel"
        for ticker in panel_etfs[:2]:
            sector = etf_to_sector.get(ticker, ticker)
            panel_card = {
                "direction":  "BUY" if panel_dir == "BULLISH" else "SELL",
                "etfs":       [(ticker, ticker, None)],
                "confidence": panel_conf,
                "theme":      f"{sector} — {analyst_str}",
                "uid":        f"panel-{ticker}-{panel_advice.get('generated_be','')[:10]}",
            }
            open_position(panel_card, seen_data)

    if advice_cards:
        log_advice_for_scoring(advice_cards, seen_data)

    # 6b. Update existing portfolio positions
    portfolio_checks = update_positions(seen_data)
    if portfolio_checks:
        print(f"Portfolio checks: {len(portfolio_checks)} position updates")

    # 7. Queue signals for backcheck + add to history
    # Deduplicate by ticker — only queue first signal per ticker per run to avoid
    # flooding pending_checks with the same ticker from 20 different news articles
    backchecked_tickers = set()
    for a in all_alerts:
        if a["source"] != "CONVERGENCE":
            etfs = a.get("etfs", [])
            ticker = etfs[0][0] if etfs and isinstance(etfs[0], (list, tuple)) else None
            if ticker and ticker not in backchecked_tickers:
                queue_for_backcheck(a, seen_data)
                backchecked_tickers.add(ticker)
        add_to_history(a, seen_data)

    # 8. Generate HTML pages
    generate_history_html(seen_data)
    generate_live_html(seen_data, all_alerts, advice_cards, analyst_verdicts, panel_advice)
    generate_sources_html(seen_data)
    generate_index_html()

    # 9. Send email — only on meaningful events
    priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_alerts.sort(key=lambda x: (
        0 if x["source"] == "CONVERGENCE"
        else priority.get(x.get("urgency", "LOW"), 2)
    ))

    high_alerts        = [a for a in all_alerts if a.get("urgency") == "HIGH" or a.get("source") == "CONVERGENCE"]
    medium_alerts      = [a for a in all_alerts if a.get("urgency") == "MEDIUM"]
    portfolio_closings = [c for c in portfolio_checks if c.get("window") == "5d"]

    should_mail = (
        len(high_alerts) > 0 or
        len(medium_alerts) >= 5 or
        len(backcheck_results) > 0 or
        len(portfolio_closings) > 0
    )

    if should_mail:
        print(f"Sending email: {len(high_alerts)} HIGH, {len(medium_alerts)} MEDIUM, "
              f"{len(backcheck_results)} backchecks, {len(portfolio_closings)} closed positions")
        send_email(all_alerts, backcheck_results, seen_data, advice_cards)
    else:
        print(f"No email — {len(all_alerts)} low-priority signals only")

    # 10. Save and commit
    commit_seen(seen_data)
    print("=== Done ===")


if __name__ == "__main__":
    main()
