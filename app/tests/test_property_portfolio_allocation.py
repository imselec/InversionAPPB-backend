"""
Property-based tests for portfolio allocation calculation.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.rebalancing_service import RebalancingService
from app.database import get_connection, init_database


# Property 22: Target Allocation Calculation
# Validates: Requirements 8.3
@given(num_stocks=st.integers(min_value=1, max_value=100))
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_target_allocation_calculation(num_stocks):
    """
    **Validates: Requirements 8.3**
    
    Property: For any portfolio with N stocks, the target allocation percentage 
    for each stock SHALL be calculated as 100 / N.
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing portfolio
    cursor.execute("DELETE FROM portfolio")
    
    # Use real ticker symbols cyclically to avoid Yahoo Finance errors
    real_tickers = ['AVGO', 'PG', 'NEE', 'JNJ', 'UPS', 'CVX', 'XOM', 'ABBV']
    test_tickers = [real_tickers[i % len(real_tickers)] + f"_{i}" 
                    for i in range(num_stocks)]
    
    for ticker in test_tickers:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES (?, ?, ?, ?)
        """, (ticker, 10.0, 100.0, 100.0))
    
    conn.commit()
    conn.close()
    
    # Mock get_prices to return test data without calling Yahoo Finance
    mock_prices = {ticker: 100.0 for ticker in test_tickers}
    
    with patch('app.services.rebalancing_service.get_prices', return_value=mock_prices):
        # Get balance status which calculates target allocation
        service = RebalancingService()
        result = service.check_balance_status()
    
    # Calculate expected target allocation
    expected_target = 100.0 / num_stocks
    
    # Property 1: Target allocation matches expected calculation
    actual_target = result.get('target_allocation', 0)
    assert abs(actual_target - expected_target) < 0.01, \
        f"Target {actual_target} != expected {expected_target}"
    
    # Property 2: All stocks have the same target allocation
    allocations = result.get('allocations', [])
    assert len(allocations) == num_stocks, \
        f"Expected {num_stocks} allocations, got {len(allocations)}"
    
    for allocation in allocations:
        stock_target = allocation['target_allocation']
        assert abs(stock_target - expected_target) < 0.01, \
            f"Stock target {stock_target} != expected {expected_target}"
    
    # Property 3: Sum of all target allocations equals 100%
    total_target = sum(alloc['target_allocation'] for alloc in allocations)
    assert abs(total_target - 100.0) < 0.5, \
        f"Sum {total_target} != 100%"
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM rebalancing_alerts")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Initialize database
    init_database()
    
    # Run property test
    print("Running Property 22: Target Allocation Calculation...")
    test_property_target_allocation_calculation()
    print("✓ Property 22 passed!")

