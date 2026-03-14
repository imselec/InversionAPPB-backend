"""
Pytest configuration and fixtures for tests.
"""
import sys
import os
import warnings
import logging
import pytest
from io import StringIO

# Suppress all warnings
warnings.filterwarnings('ignore')

# Suppress yahooquery and yfinance logging
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)

# Global cache for market data
_market_data_cache = {
    'prices': {
        'AVGO': 900.00, 'PG': 145.00, 'NEE': 70.00,
        'JNJ': 165.00, 'UPS': 185.00, 'CVX': 155.00,
        'XOM': 115.00, 'ABBV': 175.00
    },
    'dividends': {
        'AVGO': {'yield': 0.015, 'payout': 0.45},
        'PG': {'yield': 0.025, 'payout': 0.60},
        'NEE': {'yield': 0.030, 'payout': 0.55},
        'JNJ': {'yield': 0.028, 'payout': 0.50},
        'UPS': {'yield': 0.035, 'payout': 0.55},
        'CVX': {'yield': 0.032, 'payout': 0.48},
        'XOM': {'yield': 0.030, 'payout': 0.45},
        'ABBV': {'yield': 0.038, 'payout': 0.52}
    },
    'valuations': {
        'AVGO': 25.0, 'PG': 18.0, 'NEE': 22.0,
        'JNJ': 16.0, 'UPS': 19.0, 'CVX': 12.0,
        'XOM': 11.0, 'ABBV': 15.0
    }
}


def get_cached_market_data():
    """Get the preloaded market data cache"""
    return _market_data_cache


# Store original stderr
_original_stderr = sys.stderr
_suppressed_stderr = StringIO()


@pytest.fixture(scope="function", autouse=True)
def suppress_stderr():
    """Suppress stderr for each test to hide yahooquery error messages"""
    sys.stderr = _suppressed_stderr
    yield
    sys.stderr = _original_stderr


def pytest_configure(config):
    """Configure pytest to suppress stderr globally"""
    sys.stderr = _suppressed_stderr


def pytest_unconfigure(config):
    """Restore stderr after all tests"""
    sys.stderr = _original_stderr
