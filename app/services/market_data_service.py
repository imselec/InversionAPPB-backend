"""
Market data service - per-ticker fetch with persistent cache.
Uses yf.Ticker().fast_info to avoid bulk download failures on Render.
"""
import yfinance as yf
from datetime import datetime, time, timedelta
from typing import Dict, List
import pytz
import warnings
import logging

warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)

# In-memory price cache: {ticker: (price, timestamp)}
_price_cache: Dict[str, tuple] = {}
CACHE_TTL_MINUTES = 20


def is_market_open() -> bool:
    """Determine if US markets are currently open (DST-aware)."""
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    if now.weekday() >= 5:
        return False
    market_open = time(9, 30)
    market_close = time(16, 0)
    return market_open <= now.time() <= market_close


def _fetch_price_single(ticker: str) -> float:
    """Fetch price for a single ticker using fast_info, fallback to history."""
    try:
        t = yf.Ticker(ticker)
        price = getattr(t.fast_info, 'last_price', None)
        if price and float(price) > 0:
            return float(price)
        # fallback: last close from 5d history
        hist = t.history(period="5d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception as e:
        print(f"Price fetch error {ticker}: {e}")
    return 0.0


def get_prices(tickers: List[str]) -> Dict[str, float]:
    """Get current prices per ticker with cache fallback."""
    if not tickers:
        return {}

    prices: Dict[str, float] = {}
    now = datetime.now()
    ttl = timedelta(minutes=CACHE_TTL_MINUTES)

    for ticker in tickers:
        cached = _price_cache.get(ticker)
        if cached:
            cached_price, cached_time = cached
            if now - cached_time < ttl and cached_price > 0:
                prices[ticker] = cached_price
                continue

        price = _fetch_price_single(ticker)
        if price > 0:
            _price_cache[ticker] = (price, now)
            prices[ticker] = price
        elif cached:
            # Use stale cache rather than returning 0
            prices[ticker] = cached[0]
        else:
            prices[ticker] = 0.0

    return prices


def get_price_changes(tickers: List[str]) -> Dict[str, Dict]:
    """Get daily price changes per ticker."""
    changes: Dict[str, Dict] = {}
    if not tickers:
        return changes

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                current = float(hist['Close'].iloc[-1])
                previous = float(hist['Close'].iloc[-2])
                change = current - previous
                change_pct = (change / previous * 100) if previous > 0 else 0
                changes[ticker] = {
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2)
                }
            else:
                changes[ticker] = {"price": 0, "change": 0, "change_pct": 0}
        except Exception as e:
            print(f"Price change error {ticker}: {e}")
            changes[ticker] = {"price": 0, "change": 0, "change_pct": 0}

    return changes


def get_cached_price(ticker: str) -> Dict:
    """Get cached price with staleness indicator."""
    cached = _price_cache.get(ticker)
    if cached:
        cached_price, cached_time = cached
        age_minutes = (datetime.now() - cached_time).total_seconds() / 60
        return {
            "ticker": ticker,
            "price": cached_price,
            "cached_at": cached_time.isoformat(),
            "is_stale": age_minutes > CACHE_TTL_MINUTES
        }
    return {
        "ticker": ticker,
        "price": None,
        "cached_at": None,
        "is_stale": True
    }
