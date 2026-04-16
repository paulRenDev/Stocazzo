"""
helpers.py — CronyPony v7
Pure utilities: HTTP, datetime, hashing, text.
No business logic, no imports from own modules except config.
"""
import hashlib
import re
import requests
from datetime import datetime, timezone, timedelta


# ── HTTP ──────────────────────────────────────────────────────────────────────
def safe_get(url, timeout=10, extra_headers=None):
    """GET with user-agent rotation. Returns response or None."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    ]
    headers = {"Accept": "application/json,text/html,*/*"}
    if extra_headers:
        headers.update(extra_headers)

    for agent in agents:
        headers["User-Agent"] = agent
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            if r.status_code == 200:
                return r
            print(f"  {url[:70]} → HTTP {r.status_code}")
            return None
        except Exception as e:
            print(f"  {url[:70]} → {str(e)[:60]}")
    return None


# ── DATETIME ──────────────────────────────────────────────────────────────────
def now_utc():
    """Current time as UTC string."""
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def now_utc_iso():
    """Current time as ISO string for storage."""
    return datetime.now(timezone.utc).isoformat()


def now_be():
    """Current time in Belgian timezone (CET/CEST)."""
    try:
        from zoneinfo import ZoneInfo
        be = datetime.now(ZoneInfo("Europe/Brussels"))
        return be.strftime(f"%d/%m/%Y %H:%M {be.strftime('%Z')}")
    except Exception:
        now = datetime.now(timezone.utc)
        offset = 2 if 3 < now.month < 10 else 1
        label = "CEST" if offset == 2 else "CET"
        return (now + timedelta(hours=offset)).strftime(f"%d/%m/%Y %H:%M {label}")


def convert_et_to_cet(text):
    """Converts ET/EST/EDT times in text to CET notation."""
    try:
        from zoneinfo import ZoneInfo
        et_zone = ZoneInfo("America/New_York")
        be_zone = ZoneInfo("Europe/Brussels")
    except Exception:
        return text

    def replace_time(m):
        hour, minute = int(m.group(1)), int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm:
            if ampm.upper() == "PM" and hour != 12:
                hour += 12
            elif ampm.upper() == "AM" and hour == 12:
                hour = 0
        try:
            et_dt = datetime.now(et_zone).replace(hour=hour, minute=minute, second=0, microsecond=0)
            be_dt = et_dt.astimezone(be_zone)
            return f"{m.group(0)} ({be_dt.strftime('%H:%M')} {be_dt.strftime('%Z')})"
        except Exception:
            return m.group(0)

    return re.sub(
        r'(\d{1,2}):?(\d{2})?\s*(AM|PM)?\s*(ET|EST|EDT)',
        replace_time, text, flags=re.IGNORECASE
    )


# ── HASHING / IDs ─────────────────────────────────────────────────────────────
def make_id(text):
    """Short unique ID based on text."""
    return hashlib.md5(str(text).encode()).hexdigest()[:12]


# ── TEXT ──────────────────────────────────────────────────────────────────────
def clean_html(text):
    """Strip HTML tags from text."""
    return re.sub(r'<[^>]+>', '', str(text)).strip()


def truncate(text, length=120):
    """Truncate text to given length."""
    text = str(text)
    return text[:length] + "…" if len(text) > length else text


def urgency_color(urgency):
    """Hex color for urgency level."""
    return {
        "HIGH":   "#cc2222",
        "MEDIUM": "#b06000",
        "LOW":    "#007a5e",
    }.get(urgency, "#6b6b6b")
