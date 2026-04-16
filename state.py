"""
state.py — CronyPony v7
Manages persistent state in seen_signals.json.
Read, write and commit only. No business logic.
"""
import json
import os

from config import SEEN_FILE, MAX_HISTORY, MAX_SEEN_IDS, DEFAULT_STATS
from helpers import now_utc, now_be, now_utc_iso


# ── LOAD / SAVE ───────────────────────────────────────────────────────────────
def load_seen():
    """
    Load seen_signals.json.
    Always returns a valid dict with ids, stats, pending_checks and history.
    """
    try:
        with open(SEEN_FILE) as f:
            data = json.load(f)
            if isinstance(data, list):
                # old format: was just a list of IDs
                return {
                    "ids": data,
                    "stats": DEFAULT_STATS.copy(),
                    "pending_checks": [],
                    "history": [],
                }
            data.setdefault("ids", [])
            data.setdefault("stats", DEFAULT_STATS.copy())
            data.setdefault("pending_checks", [])
            data.setdefault("history", [])
            return data
    except Exception:
        return {
            "ids": [],
            "stats": DEFAULT_STATS.copy(),
            "pending_checks": [],
            "history": [],
        }


def save_seen(seen_data):
    """Save seen_signals.json. Limits IDs to MAX_SEEN_IDS."""
    seen_data["ids"] = list(set(seen_data.get("ids", [])))[-MAX_SEEN_IDS:]
    with open(SEEN_FILE, "w") as f:
        json.dump(seen_data, f, indent=2)


# ── DEDUPLICATION ─────────────────────────────────────────────────────────────
def is_seen(uid, seen_data):
    """Check if a signal has been seen before."""
    return uid in seen_data.get("ids", [])


def mark_seen(uid, seen_data):
    """Mark a signal as seen."""
    ids = seen_data.get("ids", [])
    if uid not in ids:
        ids.append(uid)
    seen_data["ids"] = ids


# ── HISTORY ───────────────────────────────────────────────────────────────────
def add_to_history(alert, seen_data):
    """
    Add an alert to history.
    Stores reasoning for later display in history.html.
    """
    history = seen_data.setdefault("history", [])
    existing_uids = {h.get("uid") for h in history}
    if alert.get("uid") in existing_uids:
        return

    history.append({
        "uid":              alert.get("uid", ""),
        "date":             now_utc(),
        "date_be":          now_be(),
        "source":           alert.get("source", ""),
        "type":             alert.get("type", ""),
        "direction":        alert.get("direction", ""),
        "title":            alert.get("title", "")[:120],
        "detail":           alert.get("detail", "")[:200],
        "urgency":          alert.get("urgency", ""),
        "keywords":         alert.get("keywords", ""),
        "etfs":             [(t, n, e) for t, n, e in alert.get("etfs", [])[:3]],
        "link":             alert.get("link", ""),
        "confidence":       alert.get("reasoning", {}).get("confidence", 0),
        "hit_rate":         alert.get("reasoning", {}).get("hit_rate", ""),
        "reasoning_stored": alert.get("reasoning", {}),
        # Backcheck fields — filled in by scoring.py
        "verified":         None,
        "pct_change":       None,
        "verified_date":    None,
        "price_entry":      None,
        "price_now":        None,
    })

    seen_data["history"] = history[-MAX_HISTORY:]


# ── GIT COMMIT ────────────────────────────────────────────────────────────────
def commit_seen(seen_data):
    """Save and commit to git."""
    save_seen(seen_data)
    try:
        os.system('git config user.email "crony-scanner@github-actions"')
        os.system('git config user.name "Crony Scanner"')
        os.system(f'git add {SEEN_FILE} live.html history.html sources.html index.html')
        changed = os.popen('git diff --cached --quiet || echo "yes"').read().strip()
        if changed == "yes":
            os.system('git commit -m "chore: update signals [skip ci]"')
            os.system('git push')
            print("Committed and pushed.")
        else:
            print("No changes to commit.")
    except Exception as e:
        print(f"Git commit error: {e}")
