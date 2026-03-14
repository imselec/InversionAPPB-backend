"""
Property-based tests for sell recommendation on deteriorating fundamentals.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.sell_recommendation_service import SellRecommendationService


# Strategies for generating fundamental data

# Payout ratio above the 80% unsustainable threshold
high_payout_ratio_strategy = st.floats(
    min_value=0.81,
    max_value=2.0,
    allow_nan=False,
    allow_infinity=False,
)

# Payout ratio below the threshold (healthy)
healthy_payout_ratio_strategy = st.floats(
    min_value=0.0,
    max_value=0.79,
    allow_nan=False,
    allow_infinity=False,
)

# Dividend yield decline > 20% (deteriorating)
# current_yield = historical_yield * (1 - decline_fraction), decline_fraction > 0.20
declining_yield_fraction_strategy = st.floats(
    min_value=0.21,
    max_value=0.99,
    allow_nan=False,
    allow_infinity=False,
)

# Debt-to-equity increase > 50% (risky)
high_debt_change_strategy = st.floats(
    min_value=0.51,
    max_value=5.0,
    allow_nan=False,
    allow_infinity=False,
)

# Positive base dividend yield for historical reference
base_yield_strategy = st.floats(
    min_value=0.01,
    max_value=0.15,
    allow_nan=False,
    allow_infinity=False,
)


# Property 40: Sell Recommendation for Deteriorating Fundamentals
# Validates: Requirements 13.3
@given(payout_ratio=high_payout_ratio_strategy)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_sell_on_high_payout_ratio(payout_ratio):
    """
    **Validates: Requirements 13.3**

    Property 40 (payout ratio branch): Sell Recommendation for Deteriorating Fundamentals

    For any stock with payout_ratio > 80%, analyze_fundamental_deterioration shall
    set should_sell=True and include 'HIGH_PAYOUT_RATIO' in issues.
    """
    ticker = "TEST"

    mock_div_data = {
        ticker: {
            'yield': 0.03,   # healthy yield — only payout ratio is the trigger
            'payout': payout_ratio,
        }
    }

    service = SellRecommendationService()

    with patch.object(service.dividend_service, 'get_dividends', return_value=mock_div_data), \
         patch.object(service, '_get_historical_dividend_yield', return_value=0.0), \
         patch.object(service, '_get_debt_change', return_value=0.0):

        result = service.analyze_fundamental_deterioration(ticker)

    assert result['should_sell'] is True, (
        f"Expected should_sell=True for payout_ratio={payout_ratio:.2%} (>80%), "
        f"but got should_sell={result['should_sell']}"
    )
    assert 'HIGH_PAYOUT_RATIO' in result['issues'], (
        f"Expected 'HIGH_PAYOUT_RATIO' in issues for payout_ratio={payout_ratio:.2%}, "
        f"got issues={result['issues']}"
    )


@given(
    base_yield=base_yield_strategy,
    decline_fraction=declining_yield_fraction_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_sell_on_declining_dividend_yield(base_yield, decline_fraction):
    """
    **Validates: Requirements 13.3**

    Property 40 (dividend yield branch): Sell Recommendation for Deteriorating Fundamentals

    For any stock where dividend yield has declined by more than 20% year-over-year,
    analyze_fundamental_deterioration shall set should_sell=True and include
    'DECLINING_DIVIDEND' in issues.
    """
    ticker = "TEST"

    # current_yield is decline_fraction below historical (e.g. 30% decline)
    current_yield = base_yield * (1.0 - decline_fraction)
    assume(current_yield > 0)

    mock_div_data = {
        ticker: {
            'yield': current_yield,
            'payout': 0.50,   # healthy payout — only yield decline is the trigger
        }
    }

    service = SellRecommendationService()

    with patch.object(service.dividend_service, 'get_dividends', return_value=mock_div_data), \
         patch.object(service, '_get_historical_dividend_yield', return_value=base_yield), \
         patch.object(service, '_get_debt_change', return_value=0.0):

        result = service.analyze_fundamental_deterioration(ticker)

    assert result['should_sell'] is True, (
        f"Expected should_sell=True for dividend yield decline of "
        f"{decline_fraction:.1%} (>{20}%), but got should_sell={result['should_sell']}. "
        f"historical_yield={base_yield:.4f}, current_yield={current_yield:.4f}"
    )
    assert 'DECLINING_DIVIDEND' in result['issues'], (
        f"Expected 'DECLINING_DIVIDEND' in issues for yield decline={decline_fraction:.1%}, "
        f"got issues={result['issues']}"
    )


@given(debt_change=high_debt_change_strategy)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_sell_on_increased_debt(debt_change):
    """
    **Validates: Requirements 13.3**

    Property 40 (debt-to-equity branch): Sell Recommendation for Deteriorating Fundamentals

    For any stock where debt-to-equity ratio has increased by more than 50%
    year-over-year, analyze_fundamental_deterioration shall set should_sell=True
    and include 'INCREASED_DEBT' in issues.
    """
    ticker = "TEST"

    mock_div_data = {
        ticker: {
            'yield': 0.03,   # healthy yield
            'payout': 0.50,  # healthy payout — only debt change is the trigger
        }
    }

    service = SellRecommendationService()

    with patch.object(service.dividend_service, 'get_dividends', return_value=mock_div_data), \
         patch.object(service, '_get_historical_dividend_yield', return_value=0.0), \
         patch.object(service, '_get_debt_change', return_value=debt_change):

        result = service.analyze_fundamental_deterioration(ticker)

    assert result['should_sell'] is True, (
        f"Expected should_sell=True for debt_change={debt_change:.1%} (>50%), "
        f"but got should_sell={result['should_sell']}"
    )
    assert 'INCREASED_DEBT' in result['issues'], (
        f"Expected 'INCREASED_DEBT' in issues for debt_change={debt_change:.1%}, "
        f"got issues={result['issues']}"
    )


@given(
    payout_ratio=healthy_payout_ratio_strategy,
    base_yield=base_yield_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_no_sell_on_healthy_fundamentals(payout_ratio, base_yield):
    """
    **Validates: Requirements 13.3**

    Property 40 (inverse): Sell Recommendation for Deteriorating Fundamentals

    For any stock with healthy fundamentals (payout_ratio <= 80%, no dividend
    yield decline > 20%, no debt increase > 50%), analyze_fundamental_deterioration
    shall NOT set should_sell=True.
    """
    ticker = "TEST"

    # current_yield is the same as historical (no decline)
    mock_div_data = {
        ticker: {
            'yield': base_yield,
            'payout': payout_ratio,
        }
    }

    service = SellRecommendationService()

    with patch.object(service.dividend_service, 'get_dividends', return_value=mock_div_data), \
         patch.object(service, '_get_historical_dividend_yield', return_value=base_yield), \
         patch.object(service, '_get_debt_change', return_value=0.0):

        result = service.analyze_fundamental_deterioration(ticker)

    assert result['should_sell'] is False, (
        f"Expected should_sell=False for healthy fundamentals "
        f"(payout_ratio={payout_ratio:.2%}, no yield decline, no debt increase), "
        f"but got should_sell={result['should_sell']}, issues={result['issues']}"
    )
    assert result['issues'] == [], (
        f"Expected no issues for healthy fundamentals, got issues={result['issues']}"
    )

