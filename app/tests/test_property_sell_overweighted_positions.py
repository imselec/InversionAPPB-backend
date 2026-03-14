"""
Property-based tests for sell recommendation on overweighted positions.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.sell_recommendation_service import (
    SellRecommendationService,
    REBALANCING_OVERWEIGHT_THRESHOLD,
    REBALANCING_TARGET_ALLOCATION,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Allocation fraction strictly above the 20% overweight threshold
overweight_allocation_strategy = st.floats(
    min_value=0.201,
    max_value=0.99,
    allow_nan=False,
    allow_infinity=False,
)

# Allocation fraction at or below the 20% threshold (not overweight)
normal_allocation_strategy = st.floats(
    min_value=0.01,
    max_value=0.20,
    allow_nan=False,
    allow_infinity=False,
)

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
    max_value=10_000.0,
    allow_nan=False,
    allow_infinity=False,
)


def _build_holdings(ticker, shares, price, allocation_pct, other_count=4):
    """
    Build a holdings list where `ticker` has the given allocation_pct.

    total_value = (shares * price) / allocation_pct
    The remaining value is split equally among `other_count` dummy stocks.
    """
    stock_value = shares * price
    total_value = stock_value / allocation_pct
    other_value = total_value - stock_value
    other_price = 100.0
    other_shares = (other_value / other_count) / other_price

    holdings = [{'ticker': ticker, 'shares': shares, 'avg_price': price * 0.8}]
    for i in range(other_count):
        dummy = f"DUMMY{i}"
        holdings.append({
            'ticker': dummy,
            'shares': other_shares,
            'avg_price': other_price * 0.9,
        })
    return holdings, total_value, other_price


# ---------------------------------------------------------------------------
# Property 41: Sell Recommendation for Overweighted Positions
# Validates: Requirements 13.5
# ---------------------------------------------------------------------------

@given(
    shares=shares_strategy,
    price=price_strategy,
    allocation_pct=overweight_allocation_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_sell_candidate_generated_for_overweight_position(
    shares, price, allocation_pct
):
    """
    **Validates: Requirements 13.5**

    Property 41: Sell Recommendation for Overweighted Positions

    For any portfolio where a stock's allocation exceeds 20% of total value,
    identify_sell_candidates shall include that stock in the returned list
    with reason='REBALANCING'.
    """
    ticker = "OVER"
    holdings, total_value, other_price = _build_holdings(
        ticker, shares, price, allocation_pct
    )

    all_tickers = [h['ticker'] for h in holdings]
    prices_map = {ticker: price}
    for t in all_tickers:
        if t != ticker:
            prices_map[t] = other_price

    service = SellRecommendationService()

    # Suppress valuation / fundamental checks so only REBALANCING fires
    no_valuation = {
        'overvalued': False,
        'significantly_overvalued': False,
        'current_pe': 15.0,
        'historical_avg_pe': 15.0,
        'reasoning': 'ok',
    }
    no_fundamentals = {
        'should_sell': False,
        'issues': [],
        'reasoning': 'ok',
    }

    with patch(
        'app.services.sell_recommendation_service.get_prices',
        return_value=prices_map,
    ), patch.object(
        service, 'analyze_valuation_exit', return_value=no_valuation
    ), patch.object(
        service, 'analyze_fundamental_deterioration', return_value=no_fundamentals
    ):
        candidates = service.identify_sell_candidates(holdings)

    tickers_in_result = [c['ticker'] for c in candidates]
    assert ticker in tickers_in_result, (
        f"Expected '{ticker}' in sell candidates for allocation "
        f"{allocation_pct:.1%} > {REBALANCING_OVERWEIGHT_THRESHOLD:.0%}, "
        f"but got candidates: {tickers_in_result}"
    )

    # The matching candidate must carry the REBALANCING reason
    matching = next(c for c in candidates if c['ticker'] == ticker)
    assert matching['reason'] == 'REBALANCING', (
        f"Expected reason='REBALANCING' for overweight position "
        f"(allocation={allocation_pct:.1%}), got reason='{matching['reason']}'"
    )


@given(
    shares=shares_strategy,
    price=price_strategy,
    allocation_pct=overweight_allocation_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_rebalancing_sell_quantity_reduces_to_target(
    shares, price, allocation_pct
):
    """
    **Validates: Requirements 13.5**

    Property 41 (quantity branch): Sell Recommendation for Overweighted Positions

    For any overweighted position, recommend_sell_quantity with reason='REBALANCING'
    shall return a positive number of shares that, when sold, brings the allocation
    down to the 18% target (REBALANCING_TARGET_ALLOCATION).
    """
    assume(allocation_pct > REBALANCING_OVERWEIGHT_THRESHOLD)

    stock_value = shares * price
    total_value = stock_value / allocation_pct

    service = SellRecommendationService()

    shares_to_sell = service.recommend_sell_quantity(
        ticker="OVER",
        reason='REBALANCING',
        shares=shares,
        current_price=price,
        total_value=total_value,
    )

    assert shares_to_sell > 0, (
        f"Expected shares_to_sell > 0 for overweight allocation "
        f"{allocation_pct:.1%}, got {shares_to_sell}"
    )
    assert shares_to_sell <= shares, (
        f"Cannot sell more shares ({shares_to_sell:.4f}) than held ({shares:.4f})"
    )

    # After selling, allocation should be at or below the 18% target
    remaining_value = (shares - shares_to_sell) * price
    new_allocation = remaining_value / total_value
    assert new_allocation <= REBALANCING_TARGET_ALLOCATION + 1e-9, (
        f"After selling {shares_to_sell:.4f} shares, allocation "
        f"{new_allocation:.4%} still exceeds target "
        f"{REBALANCING_TARGET_ALLOCATION:.0%}. "
        f"original_allocation={allocation_pct:.4%}, "
        f"shares={shares:.4f}, price={price:.2f}"
    )


@given(
    shares=shares_strategy,
    price=price_strategy,
    allocation_pct=normal_allocation_strategy,
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_no_rebalancing_sell_when_not_overweight(
    shares, price, allocation_pct
):
    """
    **Validates: Requirements 13.5**

    Property 41 (inverse): Sell Recommendation for Overweighted Positions

    For any portfolio where a stock's allocation is at or below 20%, that stock
    shall NOT appear in identify_sell_candidates with reason='REBALANCING'
    (assuming no valuation or fundamental issues).
    """
    ticker = "NORMAL"
    holdings, total_value, other_price = _build_holdings(
        ticker, shares, price, allocation_pct
    )

    all_tickers = [h['ticker'] for h in holdings]
    prices_map = {ticker: price}
    for t in all_tickers:
        if t != ticker:
            prices_map[t] = other_price

    service = SellRecommendationService()

    no_valuation = {
        'overvalued': False,
        'significantly_overvalued': False,
        'current_pe': 15.0,
        'historical_avg_pe': 15.0,
        'reasoning': 'ok',
    }
    no_fundamentals = {
        'should_sell': False,
        'issues': [],
        'reasoning': 'ok',
    }

    with patch(
        'app.services.sell_recommendation_service.get_prices',
        return_value=prices_map,
    ), patch.object(
        service, 'analyze_valuation_exit', return_value=no_valuation
    ), patch.object(
        service, 'analyze_fundamental_deterioration', return_value=no_fundamentals
    ):
        candidates = service.identify_sell_candidates(holdings)

    rebalancing_tickers = [
        c['ticker'] for c in candidates if c['reason'] == 'REBALANCING'
    ]
    assert ticker not in rebalancing_tickers, (
        f"Did not expect '{ticker}' in REBALANCING candidates for "
        f"allocation {allocation_pct:.1%} (<= "
        f"{REBALANCING_OVERWEIGHT_THRESHOLD:.0%}), "
        f"but found it. candidates={candidates}"
    )

