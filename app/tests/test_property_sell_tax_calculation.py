"""
Property-based tests for sell recommendation tax calculation.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.sell_recommendation_service import (
    SellRecommendationService,
    CAPITAL_GAINS_RATE,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Positive share counts
shares_strategy = st.floats(
    min_value=0.01,
    max_value=10_000.0,
    allow_nan=False,
    allow_infinity=False,
)

# Positive stock prices
price_strategy = st.floats(
    min_value=1.0,
    max_value=100_000.0,
    allow_nan=False,
    allow_infinity=False,
)

# Average price strictly below current price (gain scenario)
avg_price_below_strategy = st.floats(
    min_value=0.01,
    max_value=99_999.0,
    allow_nan=False,
    allow_infinity=False,
)

# Average price strictly above current price (loss scenario)
avg_price_above_strategy = st.floats(
    min_value=1.01,
    max_value=200_000.0,
    allow_nan=False,
    allow_infinity=False,
)


# ---------------------------------------------------------------------------
# Property 43: Sell Recommendation Tax Calculation
# Validates: Requirements 13.7
# ---------------------------------------------------------------------------

@given(
    current_price=price_strategy,
    avg_price=avg_price_below_strategy,
    shares=shares_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_tax_is_non_negative(current_price, avg_price, shares):
    """
    **Validates: Requirements 13.7**

    Property 43 (non-negativity): Sell Recommendation Tax Calculation

    For any combination of current_price, avg_price, and shares,
    calculate_tax_implications shall always return a non-negative value.
    Tax cannot be negative — losses result in $0 tax.
    """
    service = SellRecommendationService()

    tax = service.calculate_tax_implications(
        ticker="TEST",
        shares=shares,
        avg_price=avg_price,
        current_price=current_price,
    )

    assert tax >= 0, (
        f"Tax must be non-negative, but got tax={tax} for "
        f"current_price={current_price}, avg_price={avg_price}, shares={shares}"
    )


@given(
    current_price=price_strategy,
    premium=st.floats(min_value=0.0, max_value=50_000.0, allow_nan=False, allow_infinity=False),
    shares=shares_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_tax_is_zero_on_losses(current_price, premium, shares):
    """
    **Validates: Requirements 13.7**

    Property 43 (zero on losses): Sell Recommendation Tax Calculation

    For any scenario where current_price <= avg_price (a loss or break-even),
    calculate_tax_implications shall return exactly 0.
    Only gains are taxed; losses result in $0 tax.
    """
    # avg_price is strictly >= current_price (loss or break-even)
    avg_price = current_price + premium

    service = SellRecommendationService()

    tax = service.calculate_tax_implications(
        ticker="TEST",
        shares=shares,
        avg_price=avg_price,
        current_price=current_price,
    )

    assert tax == 0.0, (
        f"Expected tax=0 for a loss/break-even position "
        f"(current_price={current_price}, avg_price={avg_price}, shares={shares}), "
        f"but got tax={tax}"
    )


@given(
    shares=shares_strategy,
    avg_price=avg_price_below_strategy,
    current_price=price_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_tax_equals_20_percent_of_gains(shares, avg_price, current_price):
    """
    **Validates: Requirements 13.7**

    Property 43 (exact 20% of gains): Sell Recommendation Tax Calculation

    For any scenario where current_price > avg_price (a gain),
    calculate_tax_implications shall return exactly:
        tax = (current_price - avg_price) * shares * CAPITAL_GAINS_RATE (0.20)

    This validates the formula: tax = max(0, gain_per_share * shares * 0.20)
    """
    assume(current_price > avg_price)

    expected_tax = (current_price - avg_price) * shares * CAPITAL_GAINS_RATE
    expected_tax = round(expected_tax, 2)

    service = SellRecommendationService()

    tax = service.calculate_tax_implications(
        ticker="TEST",
        shares=shares,
        avg_price=avg_price,
        current_price=current_price,
    )

    assert tax == expected_tax, (
        f"Expected tax={expected_tax} (20% of gains), but got tax={tax}. "
        f"current_price={current_price}, avg_price={avg_price}, shares={shares}, "
        f"gain_per_share={current_price - avg_price:.4f}"
    )

