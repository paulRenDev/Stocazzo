"""
etf_mapper.py — CronyPony v7
Thema → ETF mapping en bijbehorende hulpfuncties.
Geen scanlogica, geen state, geen output.
"""

# ── ETF MAP ───────────────────────────────────────────────────────────────────
# Formaat: "thema": [("TICKER", "Naam", "EXCHANGE"), ...]
# Exchanges: AMS, NYSE, NASDAQ, PAR, BRU, LSE, CBOE

ETF_MAP = {
    "defence":       [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],
    "defense":       [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],
    "aerospace":     [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("XAR","SPDR S&P Aerospace & Defense ETF","NYSE")],
    "military":      [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "lockheed":      [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("LMT","Lockheed Martin","NYSE")],
    "lmt":           [("LMT","Lockheed Martin","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "raytheon":      [("RTX","RTX Corporation","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "northrop":      [("NOC","Northrop Grumman","NYSE"), ("ITA","iShares U.S. Aerospace & Defense ETF","NYSE")],
    "geopolitics":   [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE")],
    "war":           [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE")],
    "ukraine":       [("ITA","iShares U.S. Aerospace & Defense ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE")],
    "iran":          [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE")],
    "oil":           [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("IEO","iShares U.S. Oil & Gas E&P ETF","NYSE")],
    "gas":           [("UNG","United States Natural Gas Fund","NYSE"), ("IEO","iShares U.S. Oil & Gas E&P ETF","NYSE")],
    "energy":        [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("VDE","Vanguard Energy ETF","NYSE")],
    "lng":           [("UNG","United States Natural Gas Fund","NYSE")],
    "opec":          [("XLE","Energy Select Sector SPDR ETF","NYSE"), ("USO","United States Oil Fund","NYSE")],
    "renewable":     [("INRG","iShares Global Clean Energy UCITS ETF","AMS"), ("ICLN","iShares Global Clean Energy ETF","NASDAQ")],
    "solar":         [("TAN","Invesco Solar ETF","NASDAQ"), ("INRG","iShares Global Clean Energy UCITS ETF","AMS")],
    "wind":          [("FAN","First Trust Global Wind Energy ETF","NASDAQ"), ("INRG","iShares Global Clean Energy UCITS ETF","AMS")],
    "clean energy":  [("INRG","iShares Global Clean Energy UCITS ETF","AMS"), ("ICLN","iShares Global Clean Energy ETF","NASDAQ")],
    "gold":          [("IGLN","iShares Physical Gold ETC","AMS"), ("GLD","SPDR Gold Shares","NYSE")],
    "silver":        [("SLV","iShares Silver Trust","NYSE")],
    "copper":        [("COPX","Global X Copper Miners ETF","NYSE")],
    "commodities":   [("GSG","iShares S&P GSCI Commodity ETF","NYSE"), ("DBC","Invesco DB Commodity Index Fund","NYSE")],
    "inflation":     [("TIP","iShares TIPS Bond ETF","NYSE"), ("GLD","SPDR Gold Shares","NYSE")],
    "uranium":       [("URA","Global X Uranium ETF","NYSE"), ("URNM","Sprott Uranium Miners ETF","NYSE")],
    "semiconductor": [("SOXX","iShares Semiconductor ETF","NASDAQ"), ("SMH","VanEck Semiconductor ETF","NASDAQ")],
    "chip":          [("SOXX","iShares Semiconductor ETF","NASDAQ"), ("SMH","VanEck Semiconductor ETF","NASDAQ")],
    "nvidia":        [("NVDA","NVIDIA Corporation","NASDAQ"), ("SOXX","iShares Semiconductor ETF","NASDAQ")],
    "nvda":          [("NVDA","NVIDIA Corporation","NASDAQ"), ("SOXX","iShares Semiconductor ETF","NASDAQ")],
    "ai":            [("BOTZ","Global X Robotics & AI ETF","NASDAQ"), ("ROBO","ROBO Global Robotics & Automation ETF","NYSE")],
    "tech":          [("QQQ","Invesco QQQ Trust","NASDAQ"), ("EQQQ","Invesco EQQQ Nasdaq-100 UCITS ETF","AMS")],
    "cybersecurity": [("CIBR","First Trust Nasdaq Cybersecurity ETF","NASDAQ"), ("HACK","ETFMG Prime Cyber Security ETF","NYSE")],
    "crypto":        [("IBIT","iShares Bitcoin Trust","NASDAQ")],
    "bitcoin":       [("IBIT","iShares Bitcoin Trust","NASDAQ")],
    "coinbase":      [("COIN","Coinbase Global","NASDAQ"), ("IBIT","iShares Bitcoin Trust","NASDAQ")],
    "rate cut":      [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ")],
    "fed":           [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ")],
    "interest rate": [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IEF","iShares 7-10 Year Treasury Bond ETF","NASDAQ")],
    "ecb":           [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("IBTM","iShares Euro Govt Bond 7-10yr ETF","AMS")],
    "recession":     [("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ"), ("GLD","SPDR Gold Shares","NYSE")],
    "tariff":        [("IWDA","iShares Core MSCI World UCITS ETF","AMS"), ("SPY","SPDR S&P 500 ETF","NYSE")],
    "trade deal":    [("EEM","iShares MSCI Emerging Markets ETF","NYSE"), ("IWDA","iShares Core MSCI World UCITS ETF","AMS")],
    "trade war":     [("GLD","SPDR Gold Shares","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ")],
    "china":         [("MCHI","iShares MSCI China ETF","NASDAQ"), ("KWEB","KraneShares CSI China Internet ETF","NYSE")],
    "healthcare":    [("XLV","Health Care Select Sector SPDR ETF","NYSE"), ("IBB","iShares Nasdaq Biotechnology ETF","NASDAQ")],
    "pharma":        [("IHE","iShares U.S. Pharmaceuticals ETF","NYSE"), ("XLV","Health Care Select Sector SPDR ETF","NYSE")],
    "biotech":       [("IBB","iShares Nasdaq Biotechnology ETF","NASDAQ"), ("XBI","SPDR S&P Biotech ETF","NYSE")],
    "agriculture":   [("DBA","Invesco DB Agriculture Fund","NYSE"), ("MOO","VanEck Agribusiness ETF","NYSE")],
    "infrastructure":[("IGF","iShares Global Infrastructure ETF","NYSE"), ("IFRA","iShares U.S. Infrastructure ETF","NYSE")],
    "tesla":         [("TSLA","Tesla Inc","NASDAQ"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "tsla":          [("TSLA","Tesla Inc","NASDAQ")],
    "palantir":      [("PLTR","Palantir Technologies","NASDAQ")],
    "buy":           [("IWDA","iShares Core MSCI World UCITS ETF","AMS"), ("SPY","SPDR S&P 500 ETF","NYSE")],
    "ceasefire":     [("IWDA","iShares Core MSCI World UCITS ETF","AMS"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "risk off":      [("GLD","SPDR Gold Shares","NYSE"), ("TLT","iShares 20+ Year Treasury Bond ETF","NASDAQ")],
    "risk on":       [("SPY","SPDR S&P 500 ETF","NYSE"), ("QQQ","Invesco QQQ Trust","NASDAQ")],
    "sanctions":     [("GLD","SPDR Gold Shares","NYSE"), ("XLE","Energy Select Sector SPDR ETF","NYSE")],
    "trump":         [("IWDA","iShares Core MSCI World UCITS ETF","AMS"), ("GLD","SPDR Gold Shares","NYSE")],
}

# ── EXCHANGE LINKS ────────────────────────────────────────────────────────────
YAHOO_SUFFIX = {"AMS": ".AS", "PAR": ".PA", "BRU": ".BR", "LSE": ".L"}
GOOGLE_EXCHANGE = {
    "AMS": "AMS", "PAR": "EPA", "BRU": "EBR", "LSE": "LON",
    "NYSE": "NYSE", "NASDAQ": "NASDAQ", "CBOE": "CBOE",
}


def get_etfs(text, max_results=4):
    """
    Geeft lijst van relevante ETFs op basis van tekst.
    Retourneert: [("TICKER", "Naam", "EXCHANGE"), ...]
    """
    text = text.lower()
    matched = {}
    for theme, etfs in ETF_MAP.items():
        if theme in text:
            for etf in etfs:
                if etf[0] not in matched:
                    matched[etf[0]] = etf
    return list(matched.values())[:max_results]


def etf_yahoo_url(ticker, exchange):
    """Geeft Yahoo Finance URL voor een ETF."""
    suffix = YAHOO_SUFFIX.get(exchange, "")
    return f"https://finance.yahoo.com/quote/{ticker}{suffix}"


def etf_google_url(ticker, exchange):
    """Geeft Google Finance URL voor een ETF."""
    gf_ex = GOOGLE_EXCHANGE.get(exchange, exchange)
    return f"https://www.google.com/finance/quote/{ticker}:{gf_ex}"


# ── WATCHLIST (voor live dashboard) ──────────────────────────────────────────
KEY_ETFS = [
    ("XLE",  "Energy Select SPDR",       "NYSE",    "Energie"),
    ("IEO",  "Oil & Gas E&P",            "NYSE",    "Energie"),
    ("INRG", "Global Clean Energy",      "AMS",     "Renewables"),
    ("ICLN", "Clean Energy",             "NASDAQ",  "Renewables"),
    ("GLD",  "SPDR Gold",                "NYSE",    "Goud"),
    ("IGLN", "Physical Gold ETC",        "AMS",     "Goud"),
    ("ITA",  "US Aerospace & Defense",   "NYSE",    "Defensie"),
    ("SOXX", "Semiconductors",           "NASDAQ",  "Tech"),
    ("QQQ",  "Nasdaq-100",               "NASDAQ",  "Tech"),
    ("IBIT", "Bitcoin Trust",            "NASDAQ",  "Crypto"),
    ("TLT",  "20yr Treasury Bond",       "NASDAQ",  "Obligaties"),
    ("IWDA", "MSCI World",               "AMS",     "Breed"),
]
