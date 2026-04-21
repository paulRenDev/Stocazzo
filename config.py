"""
config.py — Stocazzo v7.2
All keys, constants and thresholds in one place.
No logic, no imports from own modules.

v7.2: Added new sources (Capitol Trades, OpenInsider, news feeds, Benzinga).
      Dead sources kept in SOURCE_CREDIBILITY for historical scoring continuity
      but removed from active scanners in main.py.
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
POLYMARKET_MIN_VOLUME  = 30_000
POLYMARKET_HIGH_VOLUME = 200_000
POLYMARKET_MIN_PROB    = 0.72
POLYMARKET_MAX_PROB    = 0.10

# ── KALSHI FILTERS ────────────────────────────────────────────────────────────
KALSHI_MIN_VOLUME  = 5_000
KALSHI_HIGH_VOLUME = 100_000
KALSHI_MIN_PROB    = 0.75
KALSHI_MAX_PROB    = 0.10

# ── SOURCE CREDIBILITY ────────────────────────────────────────────────────────
SOURCE_CREDIBILITY = {
    # ── CRONY SOURCES (pre-news, highest alpha) ────────────────────────────────
    "Polymarket": {
        "weight": 5,
        "historical_hit_rate": 0.80,
        "verified_count": 4,
        "type": "Prediction market — crowd wisdom + possible insider",
        "avg_lead_time": "15 min – 4 hours",
        "note": "4/5 verified correct (Mar-Apr 2026). Anonymous — cannot confirm insider vs retail.",
    },
    "Kalshi": {
        "weight": 5,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "CFTC-regulated prediction market",
        "avg_lead_time": "Hours – days",
        "note": "Regulated = harder to manipulate. Less insider activity. No verified data yet.",
    },
    "Truth Social": {
        "weight": 4,
        "historical_hit_rate": 0.85,
        "verified_count": 1,
        "type": "Trump posts via CNN archive (5-min updates)",
        "avg_lead_time": "15-30 min",
        "note": "Fastest market mover. 9 Apr 2026: buy signal → +9.5% Nasdaq in 23 min.",
    },
    "SEC EDGAR": {
        "weight": 3,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Form 3/4/5 insider transactions (Finnhub)",
        "avg_lead_time": "2 business days",
        "note": "2-day lag vs STOCK Act 45 days. CEO/CFO buys = strongest signal. Sells often = diversification.",
    },
    "Capitol Trades": {
        "weight": 3,
        "historical_hit_rate": 0.52,
        "verified_count": 0,
        "type": "Congressional trading RSS (free, reliable)",
        "avg_lead_time": "Up to 45 days (STOCK Act delay)",
        "note": "Real congressional trade disclosures. Replaces broken Pelosi Tracker + 403 Finnhub congress endpoint.",
    },
    "OpenInsider": {
        "weight": 3,
        "historical_hit_rate": 0.58,
        "verified_count": 0,
        "type": "C-suite insider buying RSS (free, reliable)",
        "avg_lead_time": "2-4 days",
        "note": "CEO/CFO purchases >$100k. Strong signal especially when multiple insiders buy in same period.",
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

    # ── MACRO / NEWS SOURCES ──────────────────────────────────────────────────
    "Reuters RSS": {
        "weight": 2,
        "historical_hit_rate": 0.45,
        "verified_count": 0,
        "type": "Breaking news RSS (business, tech, world)",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "Fast and accurate. Business, tech and world feeds. Macro context signal.",
    },
    "AP RSS": {
        "weight": 2,
        "historical_hit_rate": 0.44,
        "verified_count": 0,
        "type": "Breaking news RSS",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "Associated Press business news. Reliable factual reporting.",
    },
    "MarketWatch RSS": {
        "weight": 2,
        "historical_hit_rate": 0.43,
        "verified_count": 0,
        "type": "Financial news RSS",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "MarketWatch real-time headlines and bulletins.",
    },
    "Yahoo Finance RSS": {
        "weight": 2,
        "historical_hit_rate": 0.42,
        "verified_count": 0,
        "type": "Financial news RSS",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "Yahoo Finance top stories and S&P 500 news.",
    },
    "Seeking Alpha RSS": {
        "weight": 2,
        "historical_hit_rate": 0.44,
        "verified_count": 0,
        "type": "Financial analysis RSS",
        "avg_lead_time": "Reactive — hours after event",
        "note": "Seeking Alpha market currents — mix of news and analysis.",
    },
    "Investing.com RSS": {
        "weight": 2,
        "historical_hit_rate": 0.43,
        "verified_count": 0,
        "type": "Financial news RSS",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "Investing.com news and macro overview.",
    },
    "Motley Fool RSS": {
        "weight": 1,
        "historical_hit_rate": 0.40,
        "verified_count": 0,
        "type": "Financial analysis RSS",
        "avg_lead_time": "Reactive — hours after event",
        "note": "More analysis than news — slower signal. Low weight.",
    },
    "Barrons RSS": {
        "weight": 2,
        "historical_hit_rate": 0.45,
        "verified_count": 0,
        "type": "Financial news RSS",
        "avg_lead_time": "Reactive — hours after event",
        "note": "Barron's financial news. High quality, institutional focus.",
    },
    "Google News RSS": {
        "weight": 2,
        "historical_hit_rate": 0.43,
        "verified_count": 0,
        "type": "Aggregated news RSS (7 financial queries)",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "Fed, tariffs, energy, crypto, semis, China, defense queries.",
    },
    "Macro RSS": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Reuters, FT, ECB, Fed, WSJ, CNBC RSS",
        "avg_lead_time": "Reactive — after news breaks",
        "note": "Confirms trends. Not predictive. Use to validate crony signals.",
    },
    "Benzinga RSS": {
        "weight": 2,
        "historical_hit_rate": 0.44,
        "verified_count": 0,
        "type": "Market-moving news RSS (free tier)",
        "avg_lead_time": "Reactive — minutes after event",
        "note": "Good for earnings, upgrades, breaking corporate news. Feeds Tape Reader analyst.",
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

    # ── SENTIMENT ─────────────────────────────────────────────────────────────
    "Social Signal": {
        "weight": 1,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Reddit top posts (WSB, r/stocks, r/options)",
        "avg_lead_time": "Variable — hours to days",
        "note": "Very noisy. Only useful when confirmed by other sources. Never act alone.",
    },

    # ── DEAD SOURCES (kept for historical scoring continuity) ─────────────────
    "Dark Pool": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Institutional order flow (Whalestream) — INACTIVE: cloud IP blocked",
        "avg_lead_time": "Hours – days",
        "note": "Blocked from GitHub Actions cloud IPs. Replaced by OpenInsider.",
    },
    "Congress": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "STOCK Act disclosure (Finnhub) — INACTIVE: 403 premium endpoint",
        "avg_lead_time": "Up to 45 days after trade",
        "note": "Requires paid Finnhub tier. Replaced by Capitol Trades RSS.",
    },
    "Pelosi Tracker": {
        "weight": 3,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Pelosi trade tracker — INACTIVE: site structure changed",
        "avg_lead_time": "Up to 45 days after trade",
        "note": "Regex broken after site redesign. Replaced by Capitol Trades RSS.",
    },
    "Options Flow": {
        "weight": 2,
        "historical_hit_rate": None,
        "verified_count": 0,
        "type": "Unusual Whales options flow — INACTIVE: cloud IP blocked",
        "avg_lead_time": "Hours",
        "note": "Blocked from GitHub Actions cloud IPs. Replaced by Benzinga RSS.",
    },
}

# ── DEFAULT STATS ─────────────────────────────────────────────────────────────
DEFAULT_STATS = {
    # Active crony
    "Polymarket":     {"hits": 4, "misses": 0, "pending": 0},
    "Kalshi":         {"hits": 0, "misses": 0, "pending": 0},
    "Truth Social":   {"hits": 0, "misses": 0, "pending": 0},
    "SEC EDGAR":      {"hits": 0, "misses": 0, "pending": 0},
    "Capitol Trades": {"hits": 0, "misses": 0, "pending": 0},
    "OpenInsider":    {"hits": 0, "misses": 0, "pending": 0},
    "Lobbying":       {"hits": 0, "misses": 0, "pending": 0},
    "Gov Contracts":  {"hits": 0, "misses": 0, "pending": 0},
    # Active news
    "Reuters RSS":      {"hits": 0, "misses": 0, "pending": 0},
    "AP RSS":           {"hits": 0, "misses": 0, "pending": 0},
    "MarketWatch RSS":  {"hits": 0, "misses": 0, "pending": 0},
    "Yahoo Finance RSS":{"hits": 0, "misses": 0, "pending": 0},
    "Seeking Alpha RSS":{"hits": 0, "misses": 0, "pending": 0},
    "Investing.com RSS":{"hits": 0, "misses": 0, "pending": 0},
    "Motley Fool RSS":  {"hits": 0, "misses": 0, "pending": 0},
    "Barrons RSS":      {"hits": 0, "misses": 0, "pending": 0},
    "Google News RSS":  {"hits": 0, "misses": 0, "pending": 0},
    "Macro RSS":        {"hits": 0, "misses": 0, "pending": 0},
    "Benzinga RSS":     {"hits": 0, "misses": 0, "pending": 0},
    "GDELT":            {"hits": 0, "misses": 0, "pending": 0},
    "Fear & Greed":     {"hits": 0, "misses": 0, "pending": 0},
    # Sentiment
    "Social Signal":    {"hits": 0, "misses": 0, "pending": 0},
    # Dead (kept for history)
    "Dark Pool":        {"hits": 1, "misses": 0, "pending": 1},
    "Congress":         {"hits": 0, "misses": 0, "pending": 0},
    "Pelosi Tracker":   {"hits": 0, "misses": 0, "pending": 0},
    "Options Flow":     {"hits": 0, "misses": 0, "pending": 0},
}

# ── URGENCY DEFINITIONS ───────────────────────────────────────────────────────
URGENCY_DEFS = {
    "HIGH":   "Act within 30 min. Direct trigger (Truth Social buy post, Polymarket spike >$200k, oil futures spike). Lead time: 15-30 min.",
    "MEDIUM": "Monitor and verify before acting. Strong signal but not time-critical. Window: hours to 1 day.",
    "LOW":    "Background intelligence. 45-day STOCK Act lag or broad institutional flow. Use for sector confirmation only.",
}

# ── POLYMARKET / KALSHI FINANCIAL RELEVANCE FILTER ───────────────────────────
POLYMARKET_KEYWORDS = [
    # Macro / geopolitical
    "tariff", "trade war", "trade deal", "sanction", "ceasefire",
    "invasion", "nato", "ukraine", "russia", "iran", "israel",
    "china", "taiwan", "north korea",
    "opec", "oil price", "crude oil", "energy price", "natural gas", "lng", "pipeline",
    "recession", "inflation", "gdp", "unemployment", "cpi", "pce",
    # Political / presidential
    "trump", "executive order", "president signs", "federal election",
    "congress votes", "senate bill", "house vote", "legislation passes",
    "debt ceiling", "government shutdown", "federal budget",
    # Fed / rates
    "federal reserve", "rate cut", "rate hike", "interest rate",
    "fomc", "jerome powell", "ecb rate", "bank of england",
    "yield curve", "us treasury", "us dollar", "currency crisis",
    # Crypto
    "bitcoin", "ethereum", "crypto regulation", "stablecoin",
    "btc price", "eth price", "crypto etf",
    # Equities / sectors
    "stock market", "s&p 500", "nasdaq", "market crash",
    "semiconductor", "nvidia", "chip shortage", "ai regulation",
    "defense spending", "military budget", "arms deal",
    # Commodities
    "gold price", "silver price", "copper price", "lithium",
    "cobalt", "uranium", "commodity", "mineral export", "mining",
    # Climate / energy transition
    "solar energy", "wind energy", "renewable energy", "carbon tax",
    "climate deal", "green deal", "carbon border",
    # Africa / emerging markets
    "africa", "congo", "drc", "zambia", "zimbabwe", "nigeria",
    "saudi arabia", "gulf state", "uae investment", "sovereign fund",
    "critical mineral", "export ban",
]

POLYMARKET_NOISE_KEYWORDS = [
    # Sports leagues
    "nhl", "nba", "nfl", "mlb", "nascar", "ufc", "mma", "boxing",
    "stanley cup", "super bowl", "world series", "world cup",
    "premier league", "champions league", "la liga", "bundesliga",
    "ncaa", "march madness", "olympic", "wimbledon", "french open",
    "grand slam", "formula 1", "f1 race",
    # Sports teams and events
    "championship", "playoffs", "tournament bracket",
    "win the series", "win the cup", "win the bowl",
    "oilers", "maple leafs", "rangers", "bruins", "penguins",
    "chiefs", "eagles", "cowboys", "patriots",
    "lakers", "celtics", "warriors", "bulls",
    # Sports actions
    "score a goal", "win the game", "win the match",
    "home run", "touchdown pass",
    # Entertainment / celebrity
    "oscar", "grammy", "emmy", "golden globe",
    "album release", "movie release", "box office",
    "actor", "actress", "singer", "rapper",
    "kardashian", "taylor swift", "beyonce", "drake",
    "reality show", "reality tv", "tv show", "streamer",
    # Gaming
    "esports", "gaming tournament", "fortnite", "minecraft",
    "video game",
    # Novelty
    "alien", "ufo", "bigfoot", "supernatural",
    "asteroid", "comet",
    "world cup host", "olympic host",
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
