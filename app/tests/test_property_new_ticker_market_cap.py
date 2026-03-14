"""
Property-based tests for new ticker market cap constraint.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.new_ticker_discovery_service import NewTickerDiscoveryService


# Helper strategy: generate a list of ticker symbols
ticker_strategy = st.lists(
    st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=5),
    min_size=1,
    max_size=10,
    unique=True,
)

# Strategy for market cap values (mix of below and above $10B)
market_cap_strategy = st.floats(
    min_value=0,
    max_value=3_000_000_000_000,  # up to $3T
    allow_nan=False,
    allow_infinity=False,
)


# Property 35: New Ticker Market Cap Constraint
# Validates: Requirements 11.6
@given(
    tickers=ticker_strategy,
    market_caps=st.lists(
        market_cap_strategy,
        min_size=1,
        max_size=10,
    )
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_new_ticker_market_cap_constraint(tickers, market_caps):
    """
    **Validates: Requirements 11.6**

    Property 35: New Ticker Market Cap Constraint

    For any new ticker recommendation, the stock's market capitalization shall be
    greater than $10 billion. screen_by_fundamentals must never return a ticker
    whose market cap is below the $10B threshold.
    """
    MIN_MARKET_CAP = 10_000_000_000  # $10 billion

    # Align market_caps list length with tickers
    caps = (market_caps * (len(tickers) // len(market_caps) + 1))[:len(tickers)]

    # Build per-ticker mock info
    ticker_info = {}
    for ticker, cap in zip(tickers, caps):
        ticker_info[ticker] = {
            'quoteType': 'EQUITY',
            'marketCap': cap,
        }

    # All tickers pass dividend/valuation/payout checks so only market cap is the filter
    mock_dividends = {t: {'yield': 0.03, 'payout': 0.50} for t in tickers}
    mock_valuations = {t: 15.0 for t in tickers}

    def make_mock_ticker(ticker):
        mock = MagicMock()
        mock.info = ticker_info.get(ticker, {'quoteType': 'EQUITY', 'marketCap': 0})
        return mock

    service = NewTickerDiscoveryService()

    with patch('app.services.new_ticker_discovery_service.yf.Ticker', side_effect=make_mock_ticker), \
         patch.object(service.dividend_service, 'get_dividends', return_value=mock_dividends), \
         patch.object(service.valuation_service, 'get_valuation', return_value=mock_valuations):

        result = service.screen_by_fundamentals(
            list(tickers),
            min_market_cap=MIN_MARKET_CAP,
            min_dividend_yield=0.02,
            max_pe_ratio=25,
            max_payout_ratio=0.70,
        )

    # Core property: every returned ticker must have market cap >= $10B
    for ticker in result:
        cap = ticker_info[ticker]['marketCap']
        assert cap >= MIN_MARKET_CAP, (
            f"Ticker {ticker} with market cap ${cap:,.0f} was returned "
            f"but is below the $10B minimum threshold"
        )

    # Inverse: tickers with cap < $10B must NOT appear in results
    below_threshold = {t for t, c in zip(tickers, caps) if c < MIN_MARKET_CAP}
    for ticker in below_threshold:
        assert ticker not in result, (
            f"Ticker {ticker} with market cap below $10B should have been filtered out"
        )

