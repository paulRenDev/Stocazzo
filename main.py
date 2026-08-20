### `main.py`

```python
"""
main.py — Stocazzo v8
Orchestrator. Calls everything, does nothing else itself.

v8: Crony-signal pivot. Polymarket/Kalshi/Truth Social/SEC EDGAR/Capitol
    Trades/OpenInsider/Reddit/Benzinga scanners are switched off — Stocazzo
    as an insider-signal tracker is retired. The macro/geopolitical layer
    (GDELT + RSS + Fear&Greed + broad news feeds) is now the primary
    function, feeding a real-portfolio advice engine (output/portfolio_advice.py)
    that maps signals onto Paul's actual ME-DIRECT holdings (real_portfolio.py)
    instead of a generic virtual portfolio. Dashboard/virtual-portfolio
    machinery is left in place but now runs on a much smaller signal set.
v7.1: Stock enrichment — yfinance technical context passed to analyst panel.
v7.2: Signal volume expansion (scan_news_feeds, expanded scanners) — see git history.
"""
from helpers import now_utc
from state import load_seen, add_to_history, commit_seen
from scoring import run_backcheck, queue_for_backcheck, update_history_backcheck

# Macro / geopolitical scanners — the only signal sources since v8
from scanners.macro       import scan_macro
from scanners.news_feeds  import scan_news_feeds

# Stock enrichment (v7.1)
from scanners.stock_analyzer import enrich_with_stock_data

# Core engines
from convergence     import build_convergence
from output.advice   import build_advice, log_advice_for_scoring, run_advice_backcheck
from output.analysts import build_analyst_panel
from portfolio       import open_position, update_positions
from output.portfolio_advice import build_portfolio_advice

# Output
from output.page_builder import generate_live_html, generate_history_html, generate_index_html, generate_sources_html
from output.mail_builder import send_portfolio_email


def main():
    print(f"=== Stocazzo v8 started: {now_utc()} ===")

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

    # 2. Run scanners — macro/geopolitical only since v8 (crony scanners retired)
    all_alerts = []
    all_alerts += scan_macro(seen_data)          # GDELT + RSS + Fear&Greed
    all_alerts += scan_news_feeds(seen_data)     # broader macro/geopolitical RSS

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

    # 6a. Build advice for Paul's real ME-DIRECT holdings — the primary output since v8
    portfolio_cards = build_portfolio_advice(all_alerts, seen_data)
    print(f"Portfolio advice: {len(portfolio_cards)} holdings have an active signal this run")

    # 6b. Update existing (virtual) portfolio positions
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

    # 9. Send email — only when a real holding has an active geopolitical signal
    if portfolio_cards:
        print(f"Sending portfolio advice email: {len(portfolio_cards)} holdings affected")
        send_portfolio_email(portfolio_cards, advice_cards, seen_data)
    else:
        print("No email — no real holding was hit by a geopolitical signal this run")

    # 10. Save and commit
    commit_seen(seen_data)
    print("=== Done ===")


if __name__ == "__main__":
    main()
```
