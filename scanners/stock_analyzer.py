"""
scanners/stock_analyzer.py — Stocazzo v7
Enriches detected tickers with technical analysis data from yfinance.
Called after all scanners run, before the analyst panel.
Returns a dict of {ticker: stock_context} for use by analysts.
Light integration: price, trend, RSI, MACD signal, recommendation.
"""

import json
import os
import hashlib
import time
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("stock_analyzer: yfinance not available — skipping enrichment")


CACHE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "stocazzo_stock_cache"
CACHE_TTL = 900  # 15 minutes


# ── CACHE ──────────────────────────────────────────────────────────────────────
def _cache_get(ticker: str):
    path = CACHE_DIR / f"{ticker.replace('.', '_')}.json"
    if path.exists() and (time.time() - path.stat().st_mtime) < CACHE_TTL:
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def _cache_set(ticker: str, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{ticker.replace('.', '_')}.json"
    path.write_text(json.dumps(data))


# ── INDICATORS ─────────────────────────────────────────────────────────────────
def _calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if not np.isnan(val) else None


def _calc_macd_signal(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = (macd - signal).iloc[-1]
    if np.isnan(hist):
        return "neutral"
    return "bullish" if hist > 0 else "bearish"


def _calc_trend(close):
    if len(close) < 50:
        return "unknown"
    cur = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    if cur > sma20 > sma50:
        return "uptrend"
    elif cur < sma20 < sma50:
        return "downtrend"
    else:
        return "sideways"


def _overall_signal(rsi, macd_signal, trend):
    """Light scoring → buy / sell / hold / watch"""
    score = 0
    if rsi is not None:
        if rsi < 30:
            score += 2
        elif rsi > 70:
            score -= 2
    if macd_signal == "bullish":
        score += 2
    elif macd_signal == "bearish":
        score -= 2
    if trend == "uptrend":
        score += 1
    elif trend == "downtrend":
        score -= 1

    if score >= 3:
        return "strong_buy"
    elif score >= 1:
        return "buy"
    elif score <= -3:
        return "strong_sell"
    elif score <= -1:
        return "sell"
    return "hold"


# ── FETCH ONE TICKER ───────────────────────────────────────────────────────────
def fetch_stock_context(ticker: str) -> dict | None:
    """
    Returns a light stock context dict for a single ticker.
    Used by analysts as additional context, not as a primary signal source.
    """
    if not YFINANCE_AVAILABLE:
        return None

    cached = _cache_get(ticker)
    if cached:
        cached["cached"] = True
        return cached

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 20:
            return None

        close = hist["Close"]
        latest = hist.iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else latest["Close"]

        change_pct = round(float((latest["Close"] - prev) / prev * 100), 2)
        rsi = _calc_rsi(close)
        macd_signal = _calc_macd_signal(close)
        trend = _calc_trend(close)
        recommendation = _overall_signal(rsi, macd_signal, trend)

        # 52w range
        high_52w = round(float(close.tail(252).max()), 2)
        low_52w = round(float(close.tail(252).min()), 2)
        cur_price = round(float(latest["Close"]), 2)
        pct_from_high = round((cur_price - high_52w) / high_52w * 100, 1)

        # Basic fundamentals
        try:
            info = stock.info
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap")
            name = info.get("longName", ticker)
        except Exception:
            pe, market_cap, name = None, None, ticker

        context = {
            "ticker":         ticker,
            "name":           name,
            "price":          cur_price,
            "change_pct":     change_pct,
            "rsi":            rsi,
            "macd_signal":    macd_signal,
            "trend":          trend,
            "recommendation": recommendation,
            "52w_high":       high_52w,
            "52w_low":        low_52w,
            "pct_from_high":  pct_from_high,
            "pe_ratio":       round(float(pe), 1) if pe else None,
            "market_cap":     market_cap,
            "cached":         False,
        }

        _cache_set(ticker, context)
        return context

    except Exception as e:
        print(f"stock_analyzer: failed for {ticker}: {e}")
        return None


# ── EXTRACT TICKERS FROM ALERTS ────────────────────────────────────────────────
def extract_tickers(all_alerts: list) -> list:
    """
    Pulls unique tickers from alert ETF lists.
    Filters out broad market ETFs that don't need individual stock analysis.
    """
    SKIP = {"SPY", "QQQ", "TLT", "IEF", "SHY", "BND", "AGG", "VXX"}
    seen = set()
    tickers = []
    for alert in all_alerts:
        for etf_tuple in alert.get("etfs", []):
            ticker = etf_tuple[0] if isinstance(etf_tuple, (list, tuple)) else etf_tuple
            if ticker and ticker not in seen and ticker not in SKIP:
                seen.add(ticker)
                tickers.append(ticker)
    return tickers[:10]  # cap at 10 to avoid long runs


# ── MAIN ENTRY POINT ───────────────────────────────────────────────────────────
def enrich_with_stock_data(all_alerts: list) -> dict:
    """
    Called from main.py after scanners run.
    Returns {ticker: stock_context} for all tickers found in alerts.
    Analysts receive this as additional context.
    """
    tickers = extract_tickers(all_alerts)
    if not tickers:
        return {}

    print(f"stock_analyzer: enriching {len(tickers)} tickers: {', '.join(tickers)}")
    stock_data = {}

    for ticker in tickers:
        ctx = fetch_stock_context(ticker)
        if ctx:
            stock_data[ticker] = ctx
            cached_str = " (cached)" if ctx.get("cached") else ""
            print(f"  {ticker}: {ctx['recommendation'].upper()} | "
                  f"RSI {ctx['rsi']} | {ctx['trend']} | "
                  f"{ctx['change_pct']:+.1f}%{cached_str}")

    return stock_data
