"""
Property-based tests for dividend functionality.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.dividend_service import DividendService
from app.database import get_connection, init_database


# Property 6: Dividend Aggregation Correctness
# Validates: Requirements 3.3, 3.4
@given(
    num_payments=st.integers(min_value=1, max_value=50),
    payment_amount=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_dividend_aggregation_correctness(num_payments, payment_amount):
    """
    **Validates: Requirements 3.3, 3.4**
    
    Property: Sum of individual dividend payments MUST equal aggregated totals.
    
    This validates that:
    - Monthly total = sum of payments in last 30 days
    - Yearly total = sum of payments in last 365 days
    - Total all time = sum of all payments
    - No payments are double-counted or missed
    
    Validates Requirements:
    - 3.3: Display monthly dividend income total
    - 3.4: Display yearly dividend income total
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing dividend payments
    cursor.execute("DELETE FROM dividend_payments")
    
    # Insert test dividend payments
    # Distribute payments across different time periods
    today = datetime.now()
    payments_data = []
    
    for i in range(num_payments):
        # Distribute payments: some recent, some old
        if i < num_payments // 3:
            # Recent payments (last 30 days)
            days_ago = i % 30
        elif i < 2 * num_payments // 3:
            # Older payments (31-365 days ago)
            days_ago = 31 + (i % 335)
        else:
            # Very old payments (>365 days ago)
            days_ago = 366 + (i % 100)
        
        payment_date = (today - timedelta(days=days_ago)).date().isoformat()
        
        cursor.execute("""
            INSERT INTO dividend_payments 
            (ticker, payment_date, amount, shares_owned, per_share_amount, reinvested)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('TEST', payment_date, payment_amount, 10.0, payment_amount / 10.0, False))
        
        payments_data.append({
            'date': payment_date,
            'amount': payment_amount,
            'days_ago': days_ago
        })
    
    conn.commit()
    conn.close()
    
    # Get dividend summary
    service = DividendService()
    summary = service.get_dividend_summary()
    
    # Calculate expected totals
    expected_monthly = sum(p['amount'] for p in payments_data if p['days_ago'] < 30)
    expected_yearly = sum(p['amount'] for p in payments_data if p['days_ago'] < 365)
    expected_total = sum(p['amount'] for p in payments_data)
    
    # Property 1: Monthly total matches sum of recent payments
    assert abs(summary['monthly_total'] - expected_monthly) < 0.01, \
        f"Monthly total {summary['monthly_total']} != expected {expected_monthly}"
    
    # Property 2: Yearly total matches sum of yearly payments
    assert abs(summary['yearly_total'] - expected_yearly) < 0.01, \
        f"Yearly total {summary['yearly_total']} != expected {expected_yearly}"
    
    # Property 3: Total all time matches sum of all payments
    assert abs(summary['total_all_time'] - expected_total) < 0.01, \
        f"Total all time {summary['total_all_time']} != expected {expected_total}"
    
    # Property 4: Monthly total <= Yearly total <= Total all time
    assert summary['monthly_total'] <= summary['yearly_total'] + 0.01, \
        "Monthly total should not exceed yearly total"
    assert summary['yearly_total'] <= summary['total_all_time'] + 0.01, \
        "Yearly total should not exceed total all time"
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dividend_payments")
    conn.commit()
    conn.close()


# Property 7: Dividend Per-Ticker Aggregation
# Validates: Requirements 3.3, 3.4
@given(
    num_tickers=st.integers(min_value=1, max_value=10),
    payments_per_ticker=st.integers(min_value=1, max_value=10)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_dividend_per_ticker_aggregation(num_tickers, payments_per_ticker):
    """
    **Validates: Requirements 3.3, 3.4**
    
    Property: Per-ticker dividend totals MUST sum to overall total.
    
    This validates that:
    - Sum of per-ticker totals = total all time
    - Each ticker's total is correctly calculated
    - No ticker data is lost or duplicated
    
    Validates Requirements:
    - 3.3: Display monthly dividend income total
    - 3.4: Display yearly dividend income total
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing dividend payments
    cursor.execute("DELETE FROM dividend_payments")
    
    # Create test tickers
    tickers = [f'TICK{i}' for i in range(num_tickers)]
    
    # Insert payments for each ticker
    expected_totals = {}
    today = datetime.now()
    
    for ticker in tickers:
        ticker_total = 0
        for i in range(payments_per_ticker):
            amount = 10.0 + i  # Varying amounts
            days_ago = i * 10  # Spread over time
            payment_date = (today - timedelta(days=days_ago)).date().isoformat()
            
            cursor.execute("""
                INSERT INTO dividend_payments 
                (ticker, payment_date, amount, shares_owned, per_share_amount, reinvested)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ticker, payment_date, amount, 10.0, amount / 10.0, False))
            
            ticker_total += amount
        
        expected_totals[ticker] = ticker_total
    
    conn.commit()
    conn.close()
    
    # Get per-ticker dividend data
    service = DividendService()
    by_ticker = service.get_dividends_by_ticker()
    summary = service.get_dividend_summary()
    
    # Property 1: Number of tickers matches
    assert len(by_ticker) == num_tickers, \
        f"Expected {num_tickers} tickers, got {len(by_ticker)}"
    
    # Property 2: Each ticker's total is correct
    for ticker_data in by_ticker:
        ticker = ticker_data['ticker']
        actual_total = ticker_data['total_dividends']
        expected_total = expected_totals[ticker]
        
        assert abs(actual_total - expected_total) < 0.01, \
            f"Ticker {ticker} total {actual_total} != expected {expected_total}"
    
    # Property 3: Sum of per-ticker totals equals overall total
    sum_of_ticker_totals = sum(t['total_dividends'] for t in by_ticker)
    assert abs(sum_of_ticker_totals - summary['total_all_time']) < 0.01, \
        f"Sum of ticker totals {sum_of_ticker_totals} != overall total {summary['total_all_time']}"
    
    # Property 4: Payment counts are correct
    for ticker_data in by_ticker:
        assert ticker_data['payment_count'] == payments_per_ticker, \
            f"Ticker {ticker_data['ticker']} has {ticker_data['payment_count']} payments, expected {payments_per_ticker}"
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dividend_payments")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Initialize database
    init_database()
    
    # Run property tests
    print("Running Property 6: Dividend Aggregation Correctness...")
    test_property_dividend_aggregation_correctness()
    print("✓ Property 6 passed!")
    
    print("\nRunning Property 7: Dividend Per-Ticker Aggregation...")
    test_property_dividend_per_ticker_aggregation()
    print("✓ Property 7 passed!")
    
    print("\nRunning Property 8: Dividend Reinvestment Recording...")
    test_property_dividend_reinvestment_recording()
    print("✓ Property 8 passed!")
    
    print("\nRunning Property 11: Dividend Reinvestment Idempotency...")
    test_property_dividend_reinvestment_idempotency()
    print("✓ Property 11 passed!")



# Property 8: Dividend Reinvestment Recording
# Validates: Requirements 3.6
@given(
    dividend_amount=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    reinvestment_price=st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    initial_shares=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_dividend_reinvestment_recording(dividend_amount, reinvestment_price, initial_shares):
    """
    **Validates: Requirements 3.6**
    
    Property: Dividend reinvestment MUST correctly update portfolio shares.
    
    This validates that:
    - Shares purchased = dividend_amount / reinvestment_price
    - New total shares = initial_shares + shares_purchased
    - Transaction is recorded in transactions table
    - Portfolio is updated correctly
    
    Validates Requirement 3.6: Record dividend reinvestment transactions
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM transactions")
    
    # Setup initial portfolio
    ticker = 'REINVEST_TEST'
    if initial_shares > 0:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, initial_shares, 100.0, 100.0, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    # Calculate expected values
    expected_shares_purchased = dividend_amount / reinvestment_price
    expected_new_total = initial_shares + expected_shares_purchased
    
    # Record dividend reinvestment
    service = DividendService()
    result = service.record_dividend_reinvestment(ticker, dividend_amount, reinvestment_price)
    
    # Property 1: Shares purchased calculation is correct
    assert abs(result['shares_purchased'] - expected_shares_purchased) < 0.0001, \
        f"Shares purchased {result['shares_purchased']} != expected {expected_shares_purchased}"
    
    # Property 2: New total shares is correct
    assert abs(result['new_total_shares'] - expected_new_total) < 0.0001, \
        f"New total {result['new_total_shares']} != expected {expected_new_total}"
    
    # Property 3: Result contains all required fields
    assert 'ticker' in result
    assert 'dividend_amount' in result
    assert 'reinvestment_price' in result
    assert 'shares_purchased' in result
    assert 'new_total_shares' in result
    
    # Property 4: Values in result match inputs
    assert result['ticker'] == ticker
    assert abs(result['dividend_amount'] - dividend_amount) < 0.01
    assert abs(result['reinvestment_price'] - reinvestment_price) < 0.01
    
    # Verify database state
    conn = get_connection()
    cursor = conn.cursor()
    
    # Property 5: Portfolio was updated
    cursor.execute("SELECT shares FROM portfolio WHERE ticker = ?", (ticker,))
    row = cursor.fetchone()
    assert row is not None, "Portfolio entry should exist"
    assert abs(row['shares'] - expected_new_total) < 0.0001, \
        f"Portfolio shares {row['shares']} != expected {expected_new_total}"
    
    # Property 6: Transaction was recorded
    cursor.execute("""
        SELECT * FROM transactions 
        WHERE ticker = ? AND transaction_type = 'DIVIDEND_REINVESTMENT'
    """, (ticker,))
    transaction = cursor.fetchone()
    assert transaction is not None, "Transaction should be recorded"
    assert transaction['action'] == 'BUY'
    assert abs(transaction['shares'] - expected_shares_purchased) < 0.0001
    assert abs(transaction['price'] - reinvestment_price) < 0.01
    assert abs(transaction['total_amount'] - dividend_amount) < 0.01
    
    conn.close()
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()


# Property 11: Dividend Reinvestment Idempotency
# Validates: Requirements 3.6
@given(
    dividend_amount=st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    reinvestment_price=st.floats(min_value=10.0, max_value=200.0, allow_nan=False, allow_infinity=False)
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_dividend_reinvestment_idempotency(dividend_amount, reinvestment_price):
    """
    **Validates: Requirements 3.6**
    
    Property: Multiple reinvestments MUST accumulate shares correctly.
    
    This validates that:
    - Each reinvestment adds shares independently
    - Total shares = sum of all reinvestment shares
    - No shares are lost or duplicated
    
    Validates Requirement 3.6: Record dividend reinvestment transactions
    """
    # Initialize database
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
    
    ticker = 'MULTI_REINVEST'
    service = DividendService()
    
    # Perform first reinvestment
    result1 = service.record_dividend_reinvestment(ticker, dividend_amount, reinvestment_price)
    shares_after_first = result1['new_total_shares']
    
    # Perform second reinvestment
    result2 = service.record_dividend_reinvestment(ticker, dividend_amount, reinvestment_price)
    shares_after_second = result2['new_total_shares']
    
    # Property 1: Second reinvestment adds to first
    expected_total = shares_after_first + result2['shares_purchased']
    assert abs(shares_after_second - expected_total) < 0.001, \
        f"Total after second {shares_after_second} != expected {expected_total}"
    
    # Property 2: Both transactions are recorded
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count FROM transactions 
        WHERE ticker = ? AND transaction_type = 'DIVIDEND_REINVESTMENT'
    """, (ticker,))
    row = cursor.fetchone()
    assert row['count'] == 2, f"Expected 2 transactions, got {row['count']}"
    
    # Property 3: Portfolio has correct final shares
    cursor.execute("SELECT shares FROM portfolio WHERE ticker = ?", (ticker,))
    portfolio_row = cursor.fetchone()
    assert abs(portfolio_row['shares'] - shares_after_second) < 0.001
    
    conn.close()
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()

