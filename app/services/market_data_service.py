"""
Market data service for fetching stock prices and market information.
"""
import yfinance as yf
from datetime import datetime, time
from typing import Dict, List
import pytz
import warnings
import logging

# Suppress yfinance warnings and errors
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)


# Market data cache
_price_cache = {}
_cache_timestamp = {}


def is_market_open() -> bool:
    """Determine if US markets are currently open."""
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    
    # Check if weekend
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = now.time()
    
    return market_open <= current_time <= market_close


def get_prices(tickers: List[str]) -> Dict[str, float]:
    """Get current prices for list of tickers."""
    prices = {}

    if not tickers:
        return prices

    try:
        data = yf.download(
            tickers=tickers,
            period="1d",
            interval="1d",
            progress=False,
            threads=False
        )

        if len(tickers) == 1:
            prices[tickers[0]] = float(data["Close"].iloc[-1])
        else:
            for t in tickers:
                try:
                    prices[t] = float(data["Close"][t].iloc[-1])
                except:
                    prices[t] = 0

        # Update cache
        for ticker, price in prices.items():
            _price_cache[ticker] = price
            _cache_timestamp[ticker] = datetime.now()

    except Exception as e:
        print("MarketDataService error:", e)
        
        # Try to use cached prices
        for t in tickers:
            if t in _price_cache:
                prices[t] = _price_cache[t]
            else:
                prices[t] = 0

    return prices


def get_price_changes(tickers: List[str]) -> Dict[str, Dict]:
    """Get daily price changes and percentage changes."""
    changes = {}
    
    if not tickers:
        return changes
    
    try:
        data = yf.download(
            tickers=tickers,
            period="2d",
            interval="1d",
            progress=False,
            threads=False
        )
        
        if len(tickers) == 1:
            ticker = tickers[0]
            if len(data) >= 2:
                current = float(data["Close"].iloc[-1])
                previous = float(data["Close"].iloc[-2])
                change = current - previous
                change_pct = (change / previous) * 100 if previous > 0 else 0
                
                changes[ticker] = {
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2)
                }
        else:
            for ticker in tickers:
                try:
                    if len(data) >= 2:
                        current = float(data["Close"][ticker].iloc[-1])
                        previous = float(data["Close"][ticker].iloc[-2])
                        change = current - previous
                        change_pct = (
                            (change / previous) * 100 if previous > 0 else 0
                        )
                        
                        changes[ticker] = {
                            "price": round(current, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2)
                        }
                except:
                    changes[ticker] = {
                        "price": 0,
                        "change": 0,
                        "change_pct": 0
                    }
    
    except Exception as e:
        print("MarketDataService price changes error:", e)
        for ticker in tickers:
            changes[ticker] = {"price": 0, "change": 0, "change_pct": 0}
    
    return changes


def get_cached_price(ticker: str) -> Dict:
    """Get cached price with staleness indicator."""
    if ticker in _price_cache:
        cache_time = _cache_timestamp.get(ticker)
        is_stale = False
        
        if cache_time:
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            is_stale = age_minutes > 15  # Stale if older than 15 minutes
        
        return {
            "ticker": ticker,
            "price": _price_cache[ticker],
            "cached_at": cache_time.isoformat() if cache_time else None,
            "is_stale": is_stale
        }
    
    return {
        "ticker": ticker,
        "price": None,
        "cached_at": None,
        "is_stale": True
    }
