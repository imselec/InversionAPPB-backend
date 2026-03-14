"""
Property-based tests for rebalancing functionality.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.rebalancing_service import RebalancingService
from app.database import get_connection, init_database


# Property 20: Overweight Rebalancing Alert
# Validates: Requirements 8.1
@given(
    overweight_pct=st.floats(min_value=0.21, max_value=0.50, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_overweight_rebalancing_alert(overweight_pct):
    """
    **Validates: Requirements 8.1**
    
    Property: Stocks >20% above target allocation MUST trigger overweight alert.
    
    This validates that:
    - Overweight threshold is 20% above target
    - Alert is generated when threshold is exceeded
    - Alert severity is marked as "high"
    - Alert type is "OVERWEIGHT"
    
    Validates Requirement 8.1: Alert when stock is >20% above target allocation
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM rebalancing_alerts")
    
    # Create portfolio with 2 stocks
    # Stock 1: Normal allocation
    # Stock 2: Overweight allocation
    
    # For 2 stocks, target allocation is 50% each
    # We want stock 2 to be overweight_pct above target
    # So stock 2 should have (50% + 50% * overweight_pct) allocation
    
    target_allocation = 50.0
    stock2_allocation = target_allocation * (1 + overweight_pct)
    stock1_allocation = 100.0 - stock2_allocation
    
    # Calculate share values to achieve these allocations
    # Let's say total portfolio value is $10,000
    total_value = 10000.0
    stock1_value = total_value * (stock1_allocation / 100)
    stock2_value = total_value * (stock2_allocation / 100)
    
    # Use price of $100 per share for simplicity
    price = 100.0
    stock1_shares = stock1_value / price
    stock2_shares = stock2_value / price
    
    cursor.execute("""
        INSERT INTO portfolio (ticker, shares, avg_price, current_price)
        VALUES (?, ?, ?, ?)
    """, ('STOCK1', stock1_shares, price, price))
    
    cursor.execute("""
        INSERT INTO portfolio (ticker, shares, avg_price, current_price)
        VALUES (?, ?, ?, ?)
    """, ('STOCK2', stock2_shares, price, price))
    
    conn.commit()
    conn.close()
    
    # Mock get_prices to return consistent prices
    mock_prices = {'STOCK1': price, 'STOCK2': price}
    
    with patch('app.services.rebalancing_service.get_prices', return_value=mock_prices):
        service = RebalancingService()
        
        # Generate rebalancing alerts
        alerts = service.generate_rebalancing_alerts()
        
        # Property 1: At least one alert should be generated
        assert len(alerts) > 0, "Should generate at least one alert for overweight stock"
        
        # Property 2: There should be an overweight alert for STOCK2
        overweight_alerts = [a for a in alerts if a['ticker'] == 'STOCK2' and a['alert_type'] == 'OVERWEIGHT']
        assert len(overweight_alerts) > 0, "Should generate OVERWEIGHT alert for STOCK2"
        
        # Property 3: Overweight alert should have high severity
        overweight_alert = overweight_alerts[0]
        assert overweight_alert['severity'] == 'high', \
            f"Overweight alert should have 'high' severity, got '{overweight_alert['severity']}'"
        
        # Property 4: Deviation should be positive
        assert overweight_alert['deviation'] > 0, \
            "Overweight stock should have positive deviation"
        
        # Property 5: Current allocation should exceed target
        assert overweight_alert['current_allocation'] > overweight_alert['target_allocation'], \
            "Current allocation should exceed target for overweight stock"
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM rebalancing_alerts")
    conn.commit()
    conn.close()


# Property 21: Underweight Rebalancing Alert
# Validates: Requirements 8.2
@given(
    underweight_pct=st.floats(min_value=0.11, max_value=0.40, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_underweight_rebalancing_alert(underweight_pct):
    """
    **Validates: Requirements 8.2**
    
    Property: Stocks >10% below target allocation MUST trigger underweight alert.
    
    This validates that:
    - Underweight threshold is 10% below target
    - Alert is generated when threshold is exceeded
    - Alert severity is marked as "medium"
    - Alert type is "UNDERWEIGHT"
    
    Validates Requirement 8.2: Alert when stock is >10% below target allocation
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM rebalancing_alerts")
    
    # Create portfolio with 2 stocks
    # Stock 1: Underweight allocation
    # Stock 2: Normal/overweight allocation
    
    # For 2 stocks, target allocation is 50% each
    # We want stock 1 to be underweight_pct below target
    # So stock 1 should have (50% - 50% * underweight_pct) allocation
    
    target_allocation = 50.0
    stock1_allocation = target_allocation * (1 - underweight_pct)
    stock2_allocation = 100.0 - stock1_allocation
    
    # Calculate share values to achieve these allocations
    total_value = 10000.0
    stock1_value = total_value * (stock1_allocation / 100)
    stock2_value = total_value * (stock2_allocation / 100)
    
    # Use price of $100 per share for simplicity
    price = 100.0
    stock1_shares = stock1_value / price
    stock2_shares = stock2_value / price
    
    cursor.execute("""
        INSERT INTO portfolio (ticker, shares, avg_price, current_price)
        VALUES (?, ?, ?, ?)
    """, ('STOCK1', stock1_shares, price, price))
    
    cursor.execute("""
        INSERT INTO portfolio (ticker, shares, avg_price, current_price)
        VALUES (?, ?, ?, ?)
    """, ('STOCK2', stock2_shares, price, price))
    
    conn.commit()
    conn.close()
    
    # Mock get_prices to return consistent prices
    mock_prices = {'STOCK1': price, 'STOCK2': price}
    
    with patch('app.services.rebalancing_service.get_prices', return_value=mock_prices):
        service = RebalancingService()
        
        # Generate rebalancing alerts
        alerts = service.generate_rebalancing_alerts()
        
        # Property 1: At least one alert should be generated
        assert len(alerts) > 0, "Should generate at least one alert for underweight stock"
        
        # Property 2: There should be an underweight alert for STOCK1
        underweight_alerts = [a for a in alerts if a['ticker'] == 'STOCK1' and a['alert_type'] == 'UNDERWEIGHT']
        assert len(underweight_alerts) > 0, "Should generate UNDERWEIGHT alert for STOCK1"
        
        # Property 3: Underweight alert should have medium severity
        underweight_alert = underweight_alerts[0]
        assert underweight_alert['severity'] == 'medium', \
            f"Underweight alert should have 'medium' severity, got '{underweight_alert['severity']}'"
        
        # Property 4: Deviation should be negative
        assert underweight_alert['deviation'] < 0, \
            "Underweight stock should have negative deviation"
        
        # Property 5: Current allocation should be below target
        assert underweight_alert['current_allocation'] < underweight_alert['target_allocation'], \
            "Current allocation should be below target for underweight stock"
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM rebalancing_alerts")
    conn.commit()
    conn.close()


# Property 23: Balanced Portfolio No Alerts
# Validates: Requirements 8.1, 8.2
@given(
    num_stocks=st.integers(min_value=2, max_value=10)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_balanced_portfolio_no_alerts(num_stocks):
    """
    **Validates: Requirements 8.1, 8.2**
    
    Property: Perfectly balanced portfolio MUST NOT generate alerts.
    
    This validates that:
    - Equal allocations don't trigger alerts
    - Threshold logic is correct
    - No false positives
    
    Validates Requirements:
    - 8.1: Alert when stock is >20% above target allocation
    - 8.2: Alert when stock is >10% below target allocation
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM rebalancing_alerts")
    
    # Create perfectly balanced portfolio
    price = 100.0
    shares_per_stock = 10.0  # Each stock has same number of shares
    
    tickers = [f'STOCK{i}' for i in range(num_stocks)]
    
    for ticker in tickers:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES (?, ?, ?, ?)
        """, (ticker, shares_per_stock, price, price))
    
    conn.commit()
    conn.close()
    
    # Mock get_prices to return consistent prices
    mock_prices = {ticker: price for ticker in tickers}
    
    with patch('app.services.rebalancing_service.get_prices', return_value=mock_prices):
        service = RebalancingService()
        
        # Generate rebalancing alerts
        alerts = service.generate_rebalancing_alerts()
        
        # Property 1: No alerts should be generated for balanced portfolio
        assert len(alerts) == 0, \
            f"Balanced portfolio should not generate alerts, got {len(alerts)} alerts"
        
        # Verify balance status
        status = service.check_balance_status()
        
        # Property 2: All stocks should have "balanced" status
        for allocation in status['allocations']:
            assert allocation['status'] == 'balanced', \
                f"Stock {allocation['ticker']} should be balanced, got status '{allocation['status']}'"
    
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
    
    # Run property tests
    print("Running Property 20: Overweight Rebalancing Alert...")
    test_property_overweight_rebalancing_alert()
    print("✓ Property 20 passed!")
    
    print("\nRunning Property 21: Underweight Rebalancing Alert...")
    test_property_underweight_rebalancing_alert()
    print("✓ Property 21 passed!")
    
    print("\nRunning Property 23: Balanced Portfolio No Alerts...")
    test_property_balanced_portfolio_no_alerts()
    print("✓ Property 23 passed!")

