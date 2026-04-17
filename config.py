"""
config.py — CronyPony v7
All keys, constants and thresholds in one place.
No logic, no imports from own modules.
"""
import os

# ── SECRETS (via GitHub Secrets) ─────────────────────────────────────────────
GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")
ALERT_EMAIL    = os.environ.get("ALERT_EMAIL", GMAIL_USER)
FINNHUB_KEY    = os.environ.get("FINNHUB_KEY", "")
TWELVEDATA_KEY = os.environ.get("TWELVEDATA_KEY", "")
GOVGREED_KEY   = os.environ.get("GOVGREED_KEY", "")

# ── FILES ─────────────────────────────────────────────────────────────────────
SEEN_FILE    = "seen_signals.json"
MAX_HISTORY  = 200
MAX_SEEN_IDS = 500

# ── SCORING THRESHOLDS ────────────────────────────────────────────────────────
CONVERGENCE_MIN_SCORE  = 5
CONVERGENCE_HIGH_SCORE = 10
BACKCHECK_DAYS_DEFAULT = 5
BACKCHECK_DAYS_FAST    = 1
HIT_THRESHOLD_PCT      = 2.0

# ── POLYMARKET FILTERS ────────────────────────────────────────────────────────
POLYMARKET_MIN_VOLUME = 30_000
POLYMARKET_HIGH_VOLUME = 200_000
POLYMARKET_MIN_PROB   = 0.72
POLYMARKET_MAX_PROB   = 0.10

# ── KALSHI FILTERS ────────────────────────────────────────────────────────────
KALSHI_MIN_VOLUME  = 5_000
KALSHI_HIGH_VOLUME = 100_000
KALSHI_MIN_PROB    = 0.75
KALSHI_MAX_PROB    = 0.10

# ── SOURCE CREDIBILITY ────────────────────────────────────────────────────────
SOURCE_CREDIBILITY = {
    "Polymarket": {
        "weight": 3,
        "historical_hit_rate": 0.80,
        "verified_count": 4,
        "type": "Prediction market — crowd wisdom + possible insider",
        "avg_lead_time": "15 min – 4 hours",
        "note": "4/5 verified correct (Mar-Apr 2026). Anonymous — cannot confirm insider vs retail.",
    },
    "Kalshi": {
        "weight": 3,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "CFTC-regulated prediction market",
        "avg_lead_time": "Hours – days",
        "note": "Regulated = harder to manipulate. Less insider activity. No verified data yet.",
    },
    "Dark Pool": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Institutional order flow (Whalestream)",
        "avg_lead_time": "Hours – days (no directional info)",
        "note": "Shows WHERE institutions trade, not BUY/SELL. Needs confirmation from other sources.",
    },
    "Congress": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "STOCK Act mandatory disclosure",
        "avg_lead_time": "Up to 45 days after trade",
        "note": "Always delayed 45 days by law. Use for sector trend, not timing.",
    },
    "Pelosi Tracker": {
        "weight": 3,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Real-time Pelosi trade tracking",
        "avg_lead_time": "Up to 45 days after trade",
        "note": "Pelosi portfolio outperformed S&P by 3-5% annually. Deep-in-money calls = signature move.",
    },
    "Options Flow": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Unusual Whales options + dark pool news",
        "avg_lead_time": "Hours (flow precedes news)",
        "note": "Institutional footprint. Direction unclear — hedge vs speculation. Best combined with Polymarket.",
    },
    "Social Signal": {
        "weight": 1,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Reddit top posts (WSB, r/stocks, r/options)",
        "avg_lead_time": "Variable — hours to days",
        "note": "Very noisy. Only useful when confirmed by other sources. Never act alone.",
    },
    "Truth Social": {
        "weight": 4,
        "historical_hit_rate": 0.85,
        "verified_count": 1,
        "type": "Trump posts via CNN archive (5-min updates)",
        "avg_lead_time": "15-30 min",
        "note": "Fastest market mover. 9 Apr 2026: buy signal → +9.5% Nasdaq in 23 min. High signal/noise ratio with keyword filter.",
    },
    "SEC EDGAR": {
        "weight": 3,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Form 3/4/5 insider transactions (Finnhub)",
        "avg_lead_time": "2 business days",
        "note": "2-day lag vs STOCK Act 45 days. CEO/CFO buys = strongest signal. Sells often = diversification.",
    },
    "Lobbying": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Senate/House lobbying disclosures (Finnhub)",
        "avg_lead_time": "Weeks to months",
        "note": "High spend precedes regulation or contract. Background context only.",
    },
    "Gov Contracts": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "USASpending government contracts (Finnhub)",
        "avg_lead_time": "Days to weeks after award",
        "note": "Defense contract wins = revenue catalyst. Most valuable for LMT/RTX/NOC/GD.",
    },
    "Macro RSS": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Reuters, FT, ECB, Fed, WSJ, CNBC RSS",
        "avg_lead_time": "Reactive — after news breaks",
        "note": "Confirms trends. Not predictive. Use to validate crony signals.",
    },
    "GDELT": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "GDELT geopolitical news tone analysis",
        "avg_lead_time": "Reactive",
        "note": "Aggregates thousands of sources. Tone score indicates geopolitical direction.",
    },
    "Fear & Greed": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "CNN Fear & Greed Index (composite of 7 indicators)",
        "avg_lead_time": "Contrarian — extremes signal reversals",
        "note": "Extreme Fear (<20) = buy signal historically. Extreme Greed (>80) = caution.",
    },
}

DEFAULT_STATS = {
    "Polymarket":     {"hits": 4, "misses": 0, "pending": 0},
    "Kalshi":         {"hits": 0, "misses": 0, "pending": 0},
    "Dark Pool":      {"hits": 1, "misses": 0, "pending": 1},
    "Congress":       {"hits": 0, "misses": 0, "pending": 0},
    "Pelosi Tracker": {"hits": 0, "misses": 0, "pending": 0},
    "Options Flow":   {"hits": 0, "misses": 0, "pending": 0},
    "Social Signal":  {"hits": 0, "misses": 0, "pending": 0},
    "SEC EDGAR":      {"hits": 0, "misses": 0, "pending": 0},
    "Lobbying":       {"hits": 0, "misses": 0, "pending": 0},
    "Gov Contracts":  {"hits": 0, "misses": 0, "pending": 0},
    "Truth Social":   {"hits": 0, "misses": 0, "pending": 0},
    "Macro RSS":      {"hits": 0, "misses": 0, "pending": 0},
    "GDELT":          {"hits": 0, "misses": 0, "pending": 0},
    "Fear & Greed":   {"hits": 0, "misses": 0, "pending": 0},
}

# ── URGENCY DEFINITIONS ───────────────────────────────────────────────────────
URGENCY_DEFS = {
    "HIGH":   "Act within 30 min. Direct trigger (Truth Social buy post, Polymarket spike >$200k, oil futures spike). Lead time: 15-30 min.",
    "MEDIUM": "Monitor and verify before acting. Strong signal but not time-critical. Window: hours to 1 day.",
    "LOW":    "Background intelligence. 45-day STOCK Act lag or broad institutional flow. Use for sector confirmation only.",
}

# ── KEYWORDS ──────────────────────────────────────────────────────────────────
POLYMARKET_KEYWORDS = [
    "trump", "tariff", "fed", "rate", "iran", "crypto", "bitcoin",
    "china", "trade", "sanction", "ceasefire", "oil", "energy",
    "defense", "ukraine", "recession", "inflation", "gdp",
]

CONGRESS_KEYWORDS = [
    "nvidia", "nvda", "semiconductor", "intel", "amd", "tsmc",
    "coinbase", "bitcoin", "crypto", "microstrategy",
    "exxon", "xom", "chevron", "cvx", "energy", "oil", "gas", "lng",
    "lockheed", "lmt", "raytheon", "rtx", "northrop", "noc", "boeing", "defense", "defence",
    "nextera", "solar", "wind", "renewable",
    "palantir", "pltr", "tesla", "tsla",
    "healthcare", "pharma", "biotech",
]

DARK_POOL_TICKERS = [
    "SPY", "QQQ", "IWM", "XLE", "XLF", "XLK", "XLV",
    "XOM", "CVX", "COP", "OXY",
    "LMT", "RTX", "NOC", "GD",
    "NVDA", "AMD", "INTC", "QCOM", "TSM",
    "COIN", "MSTR", "MARA",
    "GLD", "SLV", "GDX",
    "TLT", "HYG", "LQD",
    "USO", "UNG",
    "TSLA", "AMZN", "MSFT", "AAPL", "META",
]

OPTION_KEYWORDS = [
    "unusual", "sweep", "large call", "large put", "block trade",
    "dark pool", "flow alert", "whale", "massive", "bullish flow",
    "bearish flow", "options activity",
]

REDDIT_STRONG_KEYWORDS = [
    "trump", "tariff", "ceasefire", "iran", "fed rate", "rate cut",
    "crypto bill", "bitcoin reserve", "sanctions", "trade deal",
    "pelosi", "congress bought", "insider", "unusual options",
]

REDDIT_TICKER_KEYWORDS = [
    "spy", "qqq", "nvda", "tsla", "coin", "mstr", "xom", "lmt", "rtx",
    "gld", "tlt", "iogp", "inrg", "dfen",
]

# ── SITE URL ──────────────────────────────────────────────────────────────────
SITE_URL = "https://paulrendev.github.io/Stocazzo"
