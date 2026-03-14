"""
Property-based tests for ETF exclusion from recommendations.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.new_ticker_discovery_service import NewTickerDiscoveryService


# Strategy for quote types: mix of ETF and non-ETF types
quote_type_strategy = st.sampled_from([
    'ETF',
    'EQUITY',
    'MUTUALFUND',
    'INDEX',
    'CURRENCY',
    'ETF',   # weighted toward ETF to increase coverage
])

# Helper strategy: generate a list of ticker symbols
ticker_strategy = st.lists(
    st.text(
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        min_size=1,
        max_size=5,
    ),
    min_size=1,
    max_size=10,
    unique=True,
)


# Property 25: ETF Exclusion from Recommendations
# Validates: Requirements 9.2, 9.3, 11.7
@given(
    tickers=ticker_strategy,
    quote_types=st.lists(
        quote_type_strategy,
        min_size=1,
        max_size=10,
    )
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_etf_exclusion_from_recommendations(tickers, quote_types):
    """
    **Validates: Requirements 9.2, 9.3, 11.7**

    Property 25: ETF Exclusion from Recommendations

    For any investment recommendation (buy or new ticker), the recommended
    security shall not be an ETF. screen_by_fundamentals must never return
    a ticker whose quoteType is 'ETF', regardless of how well it scores on
    other metrics.
    """
    # Align quote_types list length with tickers
    types = (
        quote_types * (len(tickers) // len(quote_types) + 1)
    )[:len(tickers)]

    # Build per-ticker mock info — all pass every other filter so that
    # quoteType == 'ETF' is the only reason a ticker would be excluded.
    ticker_info = {}
    for ticker, qtype in zip(tickers, types):
        ticker_info[ticker] = {
            'quoteType': qtype,
            'marketCap': 50_000_000_000,  # $50B — well above $10B minimum
        }

    # All tickers pass dividend / valuation / payout checks
    mock_dividends = {t: {'yield': 0.03, 'payout': 0.50} for t in tickers}
    mock_valuations = {t: 15.0 for t in tickers}

    def make_mock_ticker(ticker):
        mock = MagicMock()
        mock.info = ticker_info.get(
            ticker,
            {'quoteType': 'EQUITY', 'marketCap': 50_000_000_000},
        )
        return mock

    service = NewTickerDiscoveryService()

    with (
        patch(
            'app.services.new_ticker_discovery_service.yf.Ticker',
            side_effect=make_mock_ticker,
        ),
        patch.object(
            service.dividend_service,
            'get_dividends',
            return_value=mock_dividends,
        ),
        patch.object(
            service.valuation_service,
            'get_valuation',
            return_value=mock_valuations,
        ),
    ):
        result = service.screen_by_fundamentals(
            list(tickers),
            min_market_cap=10_000_000_000,
            min_dividend_yield=0.02,
            max_pe_ratio=25,
            max_payout_ratio=0.70,
        )

    # Core property: no ETF must ever appear in the results
    for ticker in result:
        qtype = ticker_info[ticker]['quoteType']
        assert qtype != 'ETF', (
            f"Ticker {ticker} with quoteType='ETF' was returned "
            f"but ETFs must be excluded from recommendations "
            f"(Requirements 9.2, 9.3, 11.7)"
        )

    # Inverse: every ticker flagged as ETF must be absent from results
    etf_tickers = {
        t for t, qt in zip(tickers, types) if qt == 'ETF'
    }
    for ticker in etf_tickers:
        assert ticker not in result, (
            f"ETF ticker {ticker} should have been filtered out "
            f"by screen_by_fundamentals"
        )

