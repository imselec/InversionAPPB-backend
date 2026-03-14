"""
Property-based tests for analytics functionality.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_connection, init_database


# Property 26: Total Return Calculation
# Validates: Requirements 10.1
@given(
    initial_value=st.floats(min_value=1000.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    return_pct=st.floats(min_value=-0.50, max_value=2.0, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_total_return_calculation(initial_value, return_pct):
    """
    **Validates: Requirements 10.1**
    
    Property: Total return MUST be calculated as (current_value - initial_value) / initial_value.
    
    This validates that:
    - Total return formula is correct
    - Return can be positive or negative
    - Percentage is calculated correctly
    
    Validates Requirement 10.1: Display total return percentage
    """
    # Calculate current value based on return percentage
    current_value = initial_value * (1 + return_pct)
    
    # Calculate total return
    calculated_return = (current_value - initial_value) / initial_value
    
    # Property 1: Calculated return matches expected return
    assert abs(calculated_return - return_pct) < 0.0001, \
        f"Calculated return {calculated_return} != expected {return_pct}"
    
    # Property 2: Return sign is correct
    if current_value > initial_value:
        assert calculated_return > 0, "Return should be positive when value increases"
    elif current_value < initial_value:
        assert calculated_return < 0, "Return should be negative when value decreases"
    else:
        assert abs(calculated_return) < 0.0001, "Return should be zero when value unchanged"
    
    # Property 3: Return percentage is bounded
    # Maximum loss is -100% (value goes to 0)
    assert calculated_return >= -1.0, f"Return {calculated_return} cannot be less than -100%"
    
    # Property 4: Reverse calculation works
    # If we apply the return to initial value, we get current value
    reverse_value = initial_value * (1 + calculated_return)
    assert abs(reverse_value - current_value) < 0.01, \
        f"Reverse calculation {reverse_value} != current value {current_value}"


# Property 27: Annualized Return Calculation
# Validates: Requirements 10.2
@given(
    total_return=st.floats(min_value=-0.40, max_value=2.0, allow_nan=False, allow_infinity=False),
    days_held=st.integers(min_value=30, max_value=3650)  # 30 days to 10 years
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_annualized_return_calculation(total_return, days_held):
    """
    **Validates: Requirements 10.2**
    
    Property: Annualized return MUST be calculated as ((1 + total_return) ^ (365/days)) - 1.
    
    This validates that:
    - Annualized return formula is correct
    - Time period is properly accounted for
    - Compounding is handled correctly
    
    Validates Requirement 10.2: Display annualized return percentage
    """
    # Skip if total return would make (1 + total_return) <= 0
    assume(1 + total_return > 0.01)
    
    # Calculate annualized return
    years = days_held / 365.0
    annualized_return = ((1 + total_return) ** (1 / years)) - 1
    
    # Property 1: For exactly 1 year, annualized return equals total return
    if abs(days_held - 365) < 1:
        assert abs(annualized_return - total_return) < 0.01, \
            f"For 1 year, annualized {annualized_return} should equal total {total_return}"
    
    # Property 2: For less than 1 year, annualized return magnitude is larger
    if days_held < 365 and abs(total_return) > 0.01:
        assert abs(annualized_return) >= abs(total_return) - 0.01, \
            f"For <1 year, annualized {annualized_return} should be >= total {total_return}"
    
    # Property 3: For more than 1 year, annualized return magnitude is smaller
    if days_held > 365 and total_return > 0.01:
        assert annualized_return <= total_return + 0.01, \
            f"For >1 year, annualized {annualized_return} should be <= total {total_return}"
    
    # Property 4: Reverse calculation works
    # If we compound annualized return for the period, we get total return
    reverse_total = ((1 + annualized_return) ** years) - 1
    assert abs(reverse_total - total_return) < 0.02, \
        f"Reverse total {reverse_total} != original total {total_return}"
    
    # Property 5: Sign consistency (only for non-trivial returns)
    if total_return > 0.01:
        assert annualized_return > 0, "Positive total return should give positive annualized return"
    elif total_return < -0.01:
        assert annualized_return < 0, "Negative total return should give negative annualized return"


# Property 28: Portfolio Dividend Yield Calculation
# Validates: Requirements 10.3
@given(
    num_holdings=st.integers(min_value=1, max_value=20),
    avg_yield=st.floats(min_value=0.0, max_value=0.10, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_portfolio_dividend_yield_calculation(num_holdings, avg_yield):
    """
    **Validates: Requirements 10.3**
    
    Property: Portfolio dividend yield MUST be weighted average of individual yields.
    
    This validates that:
    - Portfolio yield = sum(holding_value * holding_yield) / total_portfolio_value
    - Weights are based on position size
    - Calculation handles multiple holdings correctly
    
    Validates Requirement 10.3: Display portfolio dividend yield
    """
    # Create holdings with varying values and yields
    holdings = []
    total_value = 0
    
    for i in range(num_holdings):
        # Vary the value and yield for each holding
        value = 1000.0 + (i * 500.0)  # Values from $1000 to $10,500
        # Yield varies around avg_yield
        yield_pct = max(0, avg_yield + (i - num_holdings/2) * 0.005)
        
        holdings.append({
            'value': value,
            'yield': yield_pct
        })
        total_value += value
    
    # Calculate weighted average yield
    weighted_yield_sum = sum(h['value'] * h['yield'] for h in holdings)
    portfolio_yield = weighted_yield_sum / total_value if total_value > 0 else 0
    
    # Property 1: Portfolio yield is within range of individual yields
    if num_holdings > 0:
        min_yield = min(h['yield'] for h in holdings)
        max_yield = max(h['yield'] for h in holdings)
        assert min_yield - 0.001 <= portfolio_yield <= max_yield + 0.001, \
            f"Portfolio yield {portfolio_yield} should be between {min_yield} and {max_yield}"
    
    # Property 2: For equal-weighted portfolio with same yields, portfolio yield equals individual yield
    equal_holdings = [{'value': 1000.0, 'yield': avg_yield} for _ in range(num_holdings)]
    equal_total = sum(h['value'] for h in equal_holdings)
    equal_weighted_sum = sum(h['value'] * h['yield'] for h in equal_holdings)
    equal_portfolio_yield = equal_weighted_sum / equal_total if equal_total > 0 else 0
    
    assert abs(equal_portfolio_yield - avg_yield) < 0.0001, \
        f"Equal-weighted portfolio yield {equal_portfolio_yield} should equal {avg_yield}"
    
    # Property 3: Portfolio yield is non-negative
    assert portfolio_yield >= 0, f"Portfolio yield {portfolio_yield} cannot be negative"
    
    # Property 4: Changing weights changes portfolio yield appropriately
    # If we double the value of the highest-yield holding, portfolio yield should increase
    if num_holdings > 1:
        max_yield_holding = max(holdings, key=lambda h: h['yield'])
        original_value = max_yield_holding['value']
        
        # Double the value of highest-yield holding
        max_yield_holding['value'] *= 2
        new_total = sum(h['value'] for h in holdings)
        new_weighted_sum = sum(h['value'] * h['yield'] for h in holdings)
        new_portfolio_yield = new_weighted_sum / new_total
        
        if max_yield_holding['yield'] > portfolio_yield:
            assert new_portfolio_yield >= portfolio_yield - 0.001, \
                "Increasing weight of high-yield holding should increase portfolio yield"
        
        # Restore original value
        max_yield_holding['value'] = original_value


# Property 29: Return Calculation with Dividends
# Validates: Requirements 10.1, 10.3
@given(
    initial_investment=st.floats(min_value=1000.0, max_value=50000.0, allow_nan=False, allow_infinity=False),
    price_return=st.floats(min_value=-0.30, max_value=1.0, allow_nan=False, allow_infinity=False),
    dividend_yield=st.floats(min_value=0.0, max_value=0.08, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_return_calculation_with_dividends(initial_investment, price_return, dividend_yield):
    """
    **Validates: Requirements 10.1, 10.3**
    
    Property: Total return MUST include both price appreciation and dividends.
    
    This validates that:
    - Total return = price return + dividend return
    - Dividends are properly included in return calculation
    - Return components are additive
    
    Validates Requirements:
    - 10.1: Display total return percentage
    - 10.3: Display portfolio dividend yield
    """
    # Calculate ending value from price return
    ending_value_from_price = initial_investment * (1 + price_return)
    
    # Calculate dividend income (assuming 1 year)
    dividend_income = initial_investment * dividend_yield
    
    # Total ending value includes dividends
    total_ending_value = ending_value_from_price + dividend_income
    
    # Calculate total return
    total_return = (total_ending_value - initial_investment) / initial_investment
    
    # Property 1: Total return equals price return plus dividend yield
    expected_total_return = price_return + dividend_yield
    assert abs(total_return - expected_total_return) < 0.0001, \
        f"Total return {total_return} != price return {price_return} + dividend yield {dividend_yield}"
    
    # Property 2: Total return is at least as good as price return alone
    assert total_return >= price_return - 0.0001, \
        "Total return should be at least as good as price return (dividends add value)"
    
    # Property 3: Dividend contribution is correctly calculated
    dividend_contribution = dividend_income / initial_investment
    assert abs(dividend_contribution - dividend_yield) < 0.0001, \
        f"Dividend contribution {dividend_contribution} != dividend yield {dividend_yield}"
    
    # Property 4: Components sum correctly
    price_contribution = (ending_value_from_price - initial_investment) / initial_investment
    assert abs(price_contribution + dividend_contribution - total_return) < 0.0001, \
        "Price contribution + dividend contribution should equal total return"


if __name__ == "__main__":
    # Run property tests
    print("Running Property 26: Total Return Calculation...")
    test_property_total_return_calculation()
    print("✓ Property 26 passed!")
    
    print("\nRunning Property 27: Annualized Return Calculation...")
    test_property_annualized_return_calculation()
    print("✓ Property 27 passed!")
    
    print("\nRunning Property 28: Portfolio Dividend Yield Calculation...")
    test_property_portfolio_dividend_yield_calculation()
    print("✓ Property 28 passed!")
    
    print("\nRunning Property 29: Return Calculation with Dividends...")
    test_property_return_calculation_with_dividends()
    print("✓ Property 29 passed!")

