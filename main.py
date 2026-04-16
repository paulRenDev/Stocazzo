"""
main.py — CronyPony v7
Orchestrator. Calls everything, does nothing else itself.
"""
from helpers import now_utc
from state import load_seen, add_to_history, commit_seen
from scoring import run_backcheck, queue_for_backcheck, update_history_backcheck

from scanners.polymarket import scan_polymarket
from scanners.kalshi     import scan_kalshi
from scanners.congress   import scan_congress, scan_pelosi
from scanners.darkpool   import scan_dark_pool
from scanners.options    import scan_unusual_whales
from scanners.social     import scan_reddit

from convergence         import build_convergence
from output.page_builder import generate_live_html, generate_history_html, generate_index_html
from output.mail_builder import send_email


def main():
    print(f"=== Stocazzo v7 started: {now_utc()} ===")

    seen_data = load_seen()
    print(f"Previously seen: {len(seen_data.get('ids', []))} items | Pending checks: {len(seen_data.get('pending_checks', []))}")

    # 1. Run backcheck first
    seen_data, backcheck_results = run_backcheck(seen_data)
    if backcheck_results:
        print(f"Backcheck: {len(backcheck_results)} signals verified")
        update_history_backcheck(backcheck_results, seen_data)

    # 2. Run all scanners
    all_alerts = []
    all_alerts += scan_polymarket(seen_data)
    all_alerts += scan_kalshi(seen_data)
    all_alerts += scan_congress(seen_data)
    all_alerts += scan_pelosi(seen_data)
    all_alerts += scan_dark_pool(seen_data)
    all_alerts += scan_unusual_whales(seen_data)
    all_alerts += scan_reddit(seen_data)

    # 3. Convergence analysis
    convergence = build_convergence(all_alerts, seen_data)
    if convergence:
        all_alerts = [convergence] + all_alerts
        print(f"Convergence alert fired: {convergence['title']}")

    print(f"New signals: {len(all_alerts)}")

    # 4. Queue for backcheck + add to history
    for a in all_alerts:
        if a["source"] != "CONVERGENCE":
            queue_for_backcheck(a, seen_data)
        add_to_history(a, seen_data)

    # 5. Generate HTML pages
    generate_history_html(seen_data)
    generate_live_html(seen_data, all_alerts)
    generate_index_html()

    # 6. Send email if anything to report
    if all_alerts or backcheck_results:
        priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        all_alerts.sort(key=lambda x: (
            0 if x["source"] == "CONVERGENCE"
            else priority.get(x.get("urgency", "LOW"), 2)
        ))
        send_email(all_alerts, backcheck_results, seen_data)

    # 7. Save and commit
    commit_seen(seen_data)
    print("=== Done ===")


if __name__ == "__main__":
    main()
