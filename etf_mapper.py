"""
etf_mapper.py — Stocazzo v7.2
Thema → ETF mapping en bijbehorende hulpfuncties.

v7.2: Expanded from 35 to 60+ themes. More specific sector ETFs.
      European tickers (IWDA, EQQQ, IGLN, INRG, IBTM) kept for dashboard display
      but yfinance_ticker() provides US-equivalent for price enrichment.
      No scan logic, no state, no output.
"""

# ── ETF MAP ───────────────────────────────────────────────────────────────────
# Format: "theme": [("TICKER", "Name", "EXCHANGE"), ...]
# Exchanges: AMS, NYSE, NASDAQ, PAR, BRU, LSE, CBOE

ETF_MAP = {
    # ── DEFENSE & AEROSPACE ───────────────────────────────────────────────────
    "defence":          [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE"), ("DFEN","Direxion Daily Aerospace & Defense Bull 3X","NYSE")],
    "defense":          [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE"), ("DFEN","Direxion Daily Aerospace & Defense Bull 3X","NYSE")],
    "aerospace":        [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],
    "military":         [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],
    "lockheed":         [("LMT","Lockheed Martin","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "lmt":              [("LMT","Lockheed Martin","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "raytheon":         [("RTX","RTX Corporation","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "northrop":         [("NOC","Northrop Grumman","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "boeing":           [("BA","Boeing Company","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "nato":             [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],
    "drone":            [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("UAVS","AgEagle Aerial Systems","NYSE")],
    "weapons":          [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],

    # ── GEOPOLITICS ───────────────────────────────────────────────────────────
    "geopolitics":      [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "war":              [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ")],
    "ukraine":          [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "russia":           [("GLD","SPDR Gold Shares","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "iran":             [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("USO","United States Oil Fund","NYSE")],
    "israel":           [("GLD","SPDR Gold Shares","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "ceasefire":        [("SPY","SPDR S&P 500 ETF","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "sanctions":        [("GLD","SPDR Gold Shares","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ")],
    "trump":            [("SPY","SPDR S&P 500 ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ")],
    "tariff":           [("SPY","SPDR S&P 500 ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("EEM","iShares MSCI Emerging Markets ETF","NYSE")],
    "trade war":        [("GLD","SPDR Gold Shares","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("EEM","iShares MSCI Emerging Markets ETF","NYSE")],
    "trade deal":       [("EEM","iShares MSCI Emerging Markets ETF","NYSE"), ("SPY","SPDR S&P 500 ETF","NYSE"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "executive order":  [("SPY","SPDR S&P 500 ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE")],

    # ── ENERGY ────────────────────────────────────────────────────────────────
    "oil":              [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("USO","United States Oil Fund","NYSE"), ("OIH","VanEck Oil Services ETF","NYSE")],
    "crude":            [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("USO","United States Oil Fund","NYSE")],
    "gas":              [("UNG","United States Natural Gas Fund","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "energy":           [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("VDE","Vanguard Energy ETF","NYSE"), ("OIH","VanEck Oil Services ETF","NYSE")],
    "lng":              [("UNG","United States Natural Gas Fund","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "opec":             [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("USO","United States Oil Fund","NYSE"), ("BNO","United States Brent Oil Fund","NYSE")],
    "pipeline":         [("MLPA","Global X MLP ETF","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "exxon":            [("XOM","Exxon Mobil","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "chevron":          [("CVX","Chevron Corporation","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],

    # ── RENEWABLES ────────────────────────────────────────────────────────────
    "renewable":        [("ICLN","iShares Global Clean Energy ETF","NASDAQ"), ("TAN","Invesco Solar ETF","NASDAQ"), ("INRG","iShares Global Clean Energy UCITS ETF","AMS")],
    "solar":            [("TAN","Invesco Solar ETF","NASDAQ"), ("ICLN","iShares Global Clean Energy ETF","NASDAQ")],
    "wind":             [("FAN","First Trust Global Wind Energy ETF","NASDAQ"), ("ICLN","iShares Global Clean Energy ETF","NASDAQ")],
    "clean energy":     [("ICLN","iShares Global Clean Energy ETF","NASDAQ"), ("TAN","Invesco Solar ETF","NASDAQ")],
    "carbon":           [("KRBN","KraneShares European Carbon Allowance ETF","NYSE"), ("ICLN","iShares Global Clean Energy ETF","NASDAQ")],
    "climate":          [("ICLN","iShares Global Clean Energy ETF","NASDAQ"), ("TAN","Invesco Solar ETF","NASDAQ")],

    # ── COMMODITIES & PRECIOUS METALS ─────────────────────────────────────────
    "gold":             [("GLD","SPDR Gold Shares","NYSE"), ("IAU","iShares Gold Trust","NYSE"), ("GDX","VanEck Gold Miners ETF","NYSE")],
    "silver":           [("SLV","iShares Silver Trust","NYSE"), ("SIVR","abrdn Physical Silver Shares ETF","NYSE")],
    "copper":           [("COPX","Global X Copper Miners ETF","NYSE"), ("JJC","iPath Bloomberg Copper Subindex ETN","NYSE")],
    "lithium":          [("LIT","Global X Lithium & Battery Tech ETF","NYSE"), ("LITP","Invesco Electric Vehicle Battery Tech ETF","NYSE")],
    "uranium":          [("URA","Global X Uranium ETF","NYSE"), ("URNM","Sprott Uranium Miners ETF","NYSE")],
    "commodities":      [("GSG","iShares S&P GSCI Commodity ETF","NYSE"), ("DBC","Invesco DB Commodity Index Fund","NYSE"), ("PDBC","Invesco Optimum Yield Diversified Commodity ETF","NASDAQ")],
    "critical mineral": [("LIT","Global X Lithium & Battery Tech ETF","NYSE"), ("COPX","Global X Copper Miners ETF","NYSE"), ("REMX","VanEck Rare Earth/Strategic Metals ETF","NYSE")],
    "rare earth":       [("REMX","VanEck Rare Earth/Strategic Metals ETF","NYSE"), ("LIT","Global X Lithium & Battery Tech ETF","NYSE")],
    "agriculture":      [("DBA","Invesco DB Agriculture Fund","NYSE"), ("MOO","VanEck Agribusiness ETF","NYSE"), ("CORN","Teucrium Corn Fund","NYSE")],
    "wheat":            [("WEAT","Teucrium Wheat Fund","NYSE"), ("DBA","Invesco DB Agriculture Fund","NYSE")],
    "food":             [("DBA","Invesco DB Agriculture Fund","NYSE"), ("MOO","VanEck Agribusiness ETF","NYSE")],

    # ── TECHNOLOGY ────────────────────────────────────────────────────────────
    "semiconductor":    [("SOXX","iShares Semiconductor ETF","NASDAQ"), ("SMH","VanEck Semiconductor ETF","NASDAQ"), ("SOXS","Direxion Daily Semiconductor Bear 3X","NYSE")],
    "chip":             [("SOXX","iShares Semiconductor ETF","NASDAQ"), ("SMH","VanEck Semiconductor ETF","NASDAQ")],
    "nvidia":           [("NVDA","NVIDIA Corporation","NASDAQ"), ("SOXX","iShares Semiconductor ETF","NASDAQ"), ("SMH","VanEck Semiconductor ETF","NASDAQ")],
    "nvda":             [("NVDA","NVIDIA Corporation","NASDAQ"), ("SOXX","iShares Semiconductor ETF","NASDAQ")],
    "intel":            [("INTC","Intel Corporation","NASDAQ"), ("SOXX","iShares Semiconductor ETF","NASDAQ")],
    "tsmc":             [("TSM","Taiwan Semiconductor","NYSE"), ("SOXX","iShares Semiconductor ETF","NASDAQ")],
    "ai":               [("BOTZ","Global X Robotics & AI ETF","NASDAQ"), ("AIQ","Global X Artificial Intelligence & Technology ETF","NASDAQ"), ("ROBO","ROBO Global Robotics & Automation ETF","NYSE")],
    "tech":             [("QQQ","Invesco QQQ Trust","NASDAQ"), ("XLK","Technology Select Sector SPDR ETF","NYSE"), ("VGT","Vanguard Information Technology ETF","NYSE")],
    "cybersecurity":    [("CIBR","First Trust Nasdaq Cybersecurity ETF","NASDAQ"), ("HACK","ETFMG Prime Cyber Security ETF","NYSE"), ("BUG","Global X Cybersecurity ETF","NASDAQ")],
    "cloud":            [("CLOU","Global X Cloud Computing ETF","NASDAQ"), ("SKYY","First Trust Cloud Computing ETF","NASDAQ")],
    "software":         [("IGV","iShares Expanded Tech-Software Sector ETF","NYSE"), ("XSW","SPDR S&P Software & Services ETF","NYSE")],
    "microsoft":        [("MSFT","Microsoft Corporation","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "apple":            [("AAPL","Apple Inc","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "meta":             [("META","Meta Platforms","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "google":           [("GOOGL","Alphabet Inc","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "amazon":           [("AMZN","Amazon.com","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],

    # ── CRYPTO ────────────────────────────────────────────────────────────────
    "crypto":           [("IBIT","iShares Bitcoin Trust","NASDAQ"), ("FBTC","Fidelity Wise Origin Bitcoin Fund","NYSE"), ("GBTC","Grayscale Bitcoin Trust","NYSE")],
    "bitcoin":          [("IBIT","iShares Bitcoin Trust","NASDAQ"), ("FBTC","Fidelity Wise Origin Bitcoin Fund","NYSE"), ("MSTR","MicroStrategy","NASDAQ")],
    "ethereum":         [("ETHA","iShares Ethereum Trust ETF","NASDAQ"), ("FETH","Fidelity Ethereum Fund","NYSE")],
    "coinbase":         [("COIN","Coinbase Global","NASDAQ"), ("IBIT","iShares Bitcoin Trust","NASDAQ")],
    "stablecoin":       [("IBIT","iShares Bitcoin Trust","NASDAQ"), ("COIN","Coinbase Global","NASDAQ")],
    "defi":             [("IBIT","iShares Bitcoin Trust","NASDAQ"), ("COIN","Coinbase Global","NASDAQ")],

    # ── RATES & BONDS ─────────────────────────────────────────────────────────
    "rate cut":         [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ"), ("EDV","Vanguard Extended Duration Treasury ETF","NYSE")],
    "rate hike":        [("TBT","ProShares UltraShort 20+ Year Treasury","NYSE"), ("SHY","iShares 1-3 Year Treasury Bond ETF","NASDAQ")],
    "fed":              [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ"), ("SHY","iShares 1-3 Year Treasury Bond ETF","NASDAQ")],
    "federal reserve":  [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ")],
    "fomc":             [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ")],
    "interest rate":    [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ")],
    "ecb":              [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IBTM","iShares Euro Govt Bond 7-10yr ETF","AMS")],
    "inflation":        [("TIP","iShares TIPS Bond ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE"), ("PDBC","Invesco Optimum Yield Diversified Commodity ETF","NASDAQ")],
    "recession":        [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("GLD","SPDR Gold Shares","NYSE"), ("XLV","Health Care Select Sector SPDR ETF","NYSE")],
    "dovish":           [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "hawkish":          [("TBT","ProShares UltraShort 20+ Year Treasury","NYSE"), ("SHY","iShares 1-3 Year Treasury Bond ETF","NASDAQ")],

    # ── FINANCIALS & BANKING ──────────────────────────────────────────────────
    "bank":             [("XLF","Financial Select Sector SPDR ETF","NYSE"), ("KBE","SPDR S&P Bank ETF","NYSE"), ("KRE","SPDR S&P Regional Banking ETF","NYSE")],
    "finance":          [("XLF","Financial Select Sector SPDR ETF","NYSE"), ("VFH","Vanguard Financials ETF","NYSE")],
    "jpmorgan":         [("JPM","JPMorgan Chase","NYSE"), ("XLF","Financial Select Sector SPDR ETF","NYSE")],
    "goldman":          [("GS","Goldman Sachs","NYSE"), ("XLF","Financial Select Sector SPDR ETF","NYSE")],
    "credit":           [("HYG","iShares iBoxx High Yield Corporate Bond ETF","NYSE"), ("LQD","iShares iBoxx Investment Grade Corporate Bond ETF","NYSE")],
    "default":          [("HYG","iShares iBoxx High Yield Corporate Bond ETF","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ")],
    "yield":            [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("HYG","iShares iBoxx High Yield Corporate Bond ETF","NYSE")],

    # ── HEALTHCARE & BIOTECH ──────────────────────────────────────────────────
    "healthcare":       [("XLV","Health Care Select Sector SPDR ETF","NYSE"), ("VHT","Vanguard Health Care ETF","NYSE"), ("IBB","iShares Nasdaq Biotechnology ETF","NASDAQ")],
    "pharma":           [("IHE","iShares U.S. Pharmaceuticals ETF","NYSE"), ("XPH","SPDR S&P Pharmaceuticals ETF","NYSE")],
    "biotech":          [("IBB","iShares Nasdaq Biotechnology ETF","NASDAQ"), ("XBI","SPDR S&P Biotech ETF","NYSE"), ("ARKG","ARK Genomic Revolution ETF","NYSE")],
    "fda":              [("XBI","SPDR S&P Biotech ETF","NYSE"), ("IBB","iShares Nasdaq Biotechnology ETF","NASDAQ")],

    # ── EMERGING MARKETS & REGIONS ────────────────────────────────────────────
    "china":            [("MCHI","iShares MSCI China ETF","NASDAQ"), ("KWEB","KraneShares CSI China Internet ETF","NYSE"), ("FXI","iShares China Large-Cap ETF","NYSE")],
    "emerging markets": [("EEM","iShares MSCI Emerging Markets ETF","NYSE"), ("VWO","Vanguard FTSE Emerging Markets ETF","NYSE")],
    "africa":           [("AFK","VanEck Africa ETF","NYSE"), ("EZA","iShares MSCI South Africa ETF","NYSE")],
    "india":            [("INDA","iShares MSCI India ETF","NYSE"), ("PIN","Invesco India ETF","NYSE")],
    "europe":           [("VGK","Vanguard FTSE Europe ETF","NYSE"), ("EZU","iShares MSCI Eurozone ETF","NYSE")],
    "japan":            [("EWJ","iShares MSCI Japan ETF","NYSE"), ("DXJ","WisdomTree Japan Hedged Equity ETF","NYSE")],
    "saudi arabia":     [("KSA","iShares MSCI Saudi Arabia ETF","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],

    # ── BROAD MARKET ──────────────────────────────────────────────────────────
    "buy":              [("SPY","SPDR S&P 500 ETF","NYSE"), ("QQQ","Invesco QQQ Trust","NASDAQ"), ("IWM","iShares Russell 2000 ETF","NYSE")],
    "bullish":          [("SPY","SPDR S&P 500 ETF","NYSE"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "bearish":          [("SH","ProShares Short S&P 500","NYSE"), ("PSQ","ProShares Short QQQ","NASDAQ")],
    "risk on":          [("SPY","SPDR S&P 500 ETF","NYSE"), ("QQQ","Invesco QQQ Trust","NASDAQ"), ("IWM","iShares Russell 2000 ETF","NYSE")],
    "risk off":         [("GLD","SPDR Gold Shares","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("SHY","iShares 1-3 Year Treasury Bond ETF","NASDAQ")],
    "market":           [("SPY","SPDR S&P 500 ETF","NYSE"), ("QQQ","Invesco QQQ Trust","NASDAQ"), ("IWM","iShares Russell 2000 ETF","NYSE")],
    "s&p":              [("SPY","SPDR S&P 500 ETF","NYSE"), ("VOO","Vanguard S&P 500 ETF","NYSE")],
    "nasdaq":           [("QQQ","Invesco QQQ Trust","NASDAQ"), ("ONEQ","Fidelity Nasdaq Composite ETF","NASDAQ")],
    "small cap":        [("IWM","iShares Russell 2000 ETF","NYSE"), ("VBR","Vanguard Small-Cap Value ETF","NYSE")],

    # ── REAL ESTATE & INFRASTRUCTURE ─────────────────────────────────────────
    "real estate":      [("VNQ","Vanguard Real Estate ETF","NYSE"), ("IYR","iShares U.S. Real Estate ETF","NYSE")],
    "reit":             [("VNQ","Vanguard Real Estate ETF","NYSE"), ("SCHH","Schwab U.S. REIT ETF","NYSE")],
    "infrastructure":   [("IGF","iShares Global Infrastructure ETF","NYSE"), ("IFRA","iShares U.S. Infrastructure ETF","NYSE"), ("PAVE","Global X U.S. Infrastructure Development ETF","NYSE")],

    # ── INDIVIDUAL STOCKS ─────────────────────────────────────────────────────
    "tesla":            [("TSLA","Tesla Inc","NASDAQ"), ("DRIV","Global X Autonomous & Electric Vehicles ETF","NASDAQ")],
    "tsla":             [("TSLA","Tesla Inc","NASDAQ")],
    "palantir":         [("PLTR","Palantir Technologies","NASDAQ"), ("BOTZ","Global X Robotics & AI ETF","NASDAQ")],
    "pltr":             [("PLTR","Palantir Technologies","NASDAQ")],
    "microStrategy":    [("MSTR","MicroStrategy","NASDAQ"), ("IBIT","iShares Bitcoin Trust","NASDAQ")],
    "mstr":             [("MSTR","MicroStrategy","NASDAQ")],
}

# ── EXCHANGE LINKS ────────────────────────────────────────────────────────────
YAHOO_SUFFIX   = {"AMS": ".AS", "PAR": ".PA", "BRU": ".BR", "LSE": ".L"}
GOOGLE_EXCHANGE = {
    "AMS": "AMS", "PAR": "EPA", "BRU": "EBR", "LSE": "LON",
    "NYSE": "NYSE", "NASDAQ": "NASDAQ", "CBOE": "CBOE",
}

# ── EUROPEAN TICKER → US EQUIVALENT (for yfinance enrichment) ────────────────
# European ETFs don't resolve on Yahoo Finance without exchange suffix.
# Map them to their closest US equivalent for price/technical enrichment.
# The display ticker remains the European one on the dashboard.
YFINANCE_EQUIVALENT = {
    "IWDA":  "SPY",    # iShares MSCI World → S&P 500 proxy
    "EQQQ":  "QQQ",    # Invesco EQQQ Nasdaq-100 → QQQ
    "IGLN":  "GLD",    # iShares Physical Gold → GLD
    "INRG":  "ICLN",   # iShares Global Clean Energy → ICLN
    "IBTM":  "IEF",    # iShares Euro Govt Bond 7-10yr → IEF
    "LITP":  "LIT",    # Invesco EV Battery Tech → LIT
}


def get_etfs(text, max_results=4):
    """
    Returns list of relevant ETFs based on text.
    Returns: [("TICKER", "Name", "EXCHANGE"), ...]
    """
    text = text.lower()
    matched = {}
    for theme, etfs in ETF_MAP.items():
        if theme in text:
            for etf in etfs:
                if etf[0] not in matched:
                    matched[etf[0]] = etf
    return list(matched.values())[:max_results]


def yfinance_ticker(ticker: str) -> str:
    """
    Returns the Yahoo Finance-compatible ticker for enrichment.
    European tickers are mapped to their US equivalent.
    """
    return YFINANCE_EQUIVALENT.get(ticker, ticker)


def is_european(ticker: str) -> bool:
    """Returns True if ticker is a European ETF that needs exchange suffix."""
    return ticker in YFINANCE_EQUIVALENT


def etf_yahoo_url(ticker, exchange):
    """Returns Yahoo Finance URL for an ETF."""
    suffix = YAHOO_SUFFIX.get(exchange, "")
    return f"https://finance.yahoo.com/quote/{ticker}{suffix}"


def etf_google_url(ticker, exchange):
    """Returns Google Finance URL for an ETF."""
    gf_ex = GOOGLE_EXCHANGE.get(exchange, exchange)
    return f"https://www.google.com/finance/quote/{ticker}:{gf_ex}"


# ── DASHBOARD WATCHLIST ───────────────────────────────────────────────────────
KEY_ETFS = [
    # Energy
    ("XLE",  "Energy Select SPDR",        "NYSE",    "Energie"),
    ("USO",  "US Oil Fund",               "NYSE",    "Energie"),
    ("UNG",  "US Natural Gas Fund",       "NYSE",    "Energie"),
    # Renewables
    ("ICLN", "Clean Energy",              "NASDAQ",  "Renewables"),
    ("TAN",  "Solar ETF",                 "NASDAQ",  "Renewables"),
    # Precious metals
    ("GLD",  "SPDR Gold",                 "NYSE",    "Goud"),
    ("SLV",  "Silver Trust",              "NYSE",    "Zilver"),
    ("GDX",  "Gold Miners",               "NYSE",    "Goud Miners"),
    # Defense
    ("ITA",  "US Aerospace & Defense",    "NYSE",    "Defensie"),
    ("XAR",  "S&P Aerospace & Defense",   "NYSE",    "Defensie"),
    # Technology
    ("SOXX", "Semiconductors",            "NASDAQ",  "Tech"),
    ("SMH",  "VanEck Semiconductors",     "NASDAQ",  "Tech"),
    ("QQQ",  "Nasdaq-100",                "NASDAQ",  "Tech"),
    ("BOTZ", "Robotics & AI",             "NASDAQ",  "AI"),
    # Crypto
    ("IBIT", "Bitcoin Trust",             "NASDAQ",  "Crypto"),
    ("COIN", "Coinbase",                  "NASDAQ",  "Crypto"),
    # Rates & Bonds
    ("TLT",  "20yr Treasury Bond",        "NASDAQ",  "Obligaties"),
    ("IEF",  "7-10yr Treasury Bond",      "NASDAQ",  "Obligaties"),
    ("TIP",  "TIPS Bond",                 "NYSE",    "Inflatie"),
    # Broad market
    ("SPY",  "S&P 500",                   "NYSE",    "Breed"),
    ("IWM",  "Russell 2000",              "NYSE",    "Small Cap"),
    ("EEM",  "Emerging Markets",          "NYSE",    "EM"),
    # Commodities
    ("COPX", "Copper Miners",             "NYSE",    "Koper"),
    ("LIT",  "Lithium & Battery Tech",    "NYSE",    "Lithium"),
    ("REMX", "Rare Earth Metals",         "NYSE",    "Rare Earth"),
    # Financials
    ("XLF",  "Financial Select SPDR",     "NYSE",    "Financieel"),
    # Healthcare
    ("XLV",  "Health Care Select SPDR",   "NYSE",    "Healthcare"),
]
