"""
main.py — Stocazzo v7
Orchestrator. Calls everything, does nothing else itself.
"""
from helpers import now_utc
from state import load_seen, add_to_history, commit_seen
from scoring import run_backcheck, queue_for_backcheck, update_history_backcheck

# Crony scanners
from scanners.polymarket import scan_polymarket
from scanners.kalshi     import scan_kalshi
from scanners.congress   import scan_congress, scan_pelosi
from scanners.darkpool   import scan_dark_pool
from scanners.options    import scan_unusual_whales
from scanners.social     import scan_reddit
from scanners.edgar      import scan_edgar
from scanners.truthsocial import scan_truthsocial

# Macro scanners
from scanners.macro      import scan_macro

# Core engines
from convergence         import build_convergence
from output.advice       import build_advice, log_advice_for_scoring, run_advice_backcheck
from portfolio           import open_position, update_positions

# Output
from output.page_builder import generate_live_html, generate_history_html, generate_index_html, generate_sources_html
from output.mail_builder import send_email


def main():
    print(f"=== Stocazzo v7 started: {now_utc()} ===")

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

    # Crony signals (pre-news, higher weight)
    all_alerts += scan_polymarket(seen_data)
    all_alerts += scan_kalshi(seen_data)
    all_alerts += scan_congress(seen_data)
    all_alerts += scan_pelosi(seen_data)
    all_alerts += scan_dark_pool(seen_data)
    all_alerts += scan_unusual_whales(seen_data)
    all_alerts += scan_edgar(seen_data)
    all_alerts += scan_reddit(seen_data)

    # Real-time social
    all_alerts += scan_truthsocial(seen_data)

    # Macro signals (post-news, lower weight but broader context)
    all_alerts += scan_macro(seen_data)

    # 3. Convergence analysis (multi-source signal overlap)
    convergence = build_convergence(all_alerts, seen_data)
    if convergence:
        all_alerts = [convergence] + all_alerts
        print(f"Convergence alert: {convergence['title']}")

    print(f"Total signals: {len(all_alerts)}")

    # 4. Build cumulative advice from ALL signals
    advice_cards = build_advice(all_alerts, seen_data)
    print(f"Advice cards generated: {len(advice_cards)}")

    # 5. Log advice + open virtual positions
    if advice_cards:
        log_advice_for_scoring(advice_cards, seen_data)
        for card in advice_cards:
            open_position(card, seen_data)

    # 5b. Update existing portfolio positions
    portfolio_checks = update_positions(seen_data)
    if portfolio_checks:
        print(f"Portfolio checks: {len(portfolio_checks)} position updates")

    # 6. Queue signals for backcheck + add to history
    for a in all_alerts:
        if a["source"] != "CONVERGENCE":
            queue_for_backcheck(a, seen_data)
        add_to_history(a, seen_data)

    # 7. Generate HTML pages
    generate_history_html(seen_data)
    generate_live_html(seen_data, all_alerts, advice_cards)
    generate_sources_html(seen_data)
    generate_index_html()

    # 8. Send email if anything to report
    if all_alerts or backcheck_results or advice_cards:
        priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        all_alerts.sort(key=lambda x: (
            0 if x["source"] == "CONVERGENCE"
            else priority.get(x.get("urgency", "LOW"), 2)
        ))
        send_email(all_alerts, backcheck_results, seen_data, advice_cards)

    # 9. Save and commit
    commit_seen(seen_data)
    print("=== Done ===")


if __name__ == "__main__":
    main()
