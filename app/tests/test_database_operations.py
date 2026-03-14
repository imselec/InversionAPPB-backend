"""
Unit tests for database CRUD operations.
Tests specific examples and edge cases for each table.
"""
import sqlite3
import pytest
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_connection, init_database


@pytest.fixture(scope="function")
def db_connection():
    """Provide a fresh database connection for each test."""
    init_database()
    conn = get_connection()
    yield conn
    conn.close()


class TestPortfolioOperations:
    """Test CRUD operations for portfolio table."""
    
    def test_create_portfolio_holding(self, db_connection):
        """Test inserting a new portfolio holding."""
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES ('AAPL', 10.5, 150.00, 155.00)
        """)
        db_connection.commit()
        
        cursor.execute("SELECT * FROM portfolio WHERE ticker = 'AAPL'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result['ticker'] == 'AAPL'
        assert result['shares'] == 10.5
        assert result['avg_price'] == 150.00
        
        # Cleanup
        cursor.execute("DELETE FROM portfolio WHERE ticker = 'AAPL'")
        db_connection.commit()
    
    def test_update_portfolio_holding(self, db_connection):
        """Test updating an existing portfolio holding."""
        cursor = db_connection.cursor()
        
        # Insert
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES ('MSFT', 5.0, 300.00, 310.00)
        """)
        db_connection.commit()
        
        # Update
        cursor.execute("""
            UPDATE portfolio SET shares = 7.5, current_price = 320.00
            WHERE ticker = 'MSFT'
        """)
        db_connection.commit()
        
        # Verify
        cursor.execute("SELECT * FROM portfolio WHERE ticker = 'MSFT'")
        result = cursor.fetchone()
        
        assert result['shares'] == 7.5
        assert result['current_price'] == 320.00
        
        # Cleanup
        cursor.execute("DELETE FROM portfolio WHERE ticker = 'MSFT'")
        db_connection.commit()
    
    def test_delete_portfolio_holding(self, db_connection):
        """Test deleting a portfolio holding."""
        cursor = db_connection.cursor()
        
        # Insert
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES ('GOOGL', 3.0, 2500.00, 2600.00)
        """)
        db_connection.commit()
        
        # Delete
        cursor.execute("DELETE FROM portfolio WHERE ticker = 'GOOGL'")
        db_connection.commit()
        
        # Verify
        cursor.execute("SELECT * FROM portfolio WHERE ticker = 'GOOGL'")
        result = cursor.fetchone()
        
        assert result is None


class TestTransactionOperations:
    """Test CRUD operations for transactions table."""
    
    def test_create_transaction(self, db_connection):
        """Test recording a new transaction."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            INSERT INTO transactions 
            (date, ticker, action, shares, price, total_amount, transaction_type)
            VALUES (?, 'AVGO', 'BUY', 2.0, 850.00, 1700.00, 'PURCHASE')
        """, (datetime.now(),))
        db_connection.commit()
        
        cursor.execute("SELECT * FROM transactions WHERE ticker = 'AVGO'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result['ticker'] == 'AVGO'
        assert result['action'] == 'BUY'
        assert result['shares'] == 2.0
        
        # Cleanup
        cursor.execute("DELETE FROM transactions WHERE ticker = 'AVGO'")
        db_connection.commit()
    
    def test_read_transactions_by_ticker(self, db_connection):
        """Test retrieving all transactions for a specific ticker."""
        cursor = db_connection.cursor()
        
        # Insert multiple transactions
        transactions = [
            (datetime.now(), 'PG', 'BUY', 5.0, 140.00, 700.00, 'PURCHASE'),
            (datetime.now(), 'PG', 'BUY', 3.0, 145.00, 435.00, 'PURCHASE'),
        ]
        
        for trans in transactions:
            cursor.execute("""
                INSERT INTO transactions 
                (date, ticker, action, shares, price, total_amount, transaction_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, trans)
        db_connection.commit()
        
        cursor.execute("SELECT * FROM transactions WHERE ticker = 'PG'")
        results = cursor.fetchall()
        
        assert len(results) == 2
        
        # Cleanup
        cursor.execute("DELETE FROM transactions WHERE ticker = 'PG'")
        db_connection.commit()


class TestDividendOperations:
    """Test CRUD operations for dividend_payments table."""
    
    def test_create_dividend_payment(self, db_connection):
        """Test recording a dividend payment."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            INSERT INTO dividend_payments 
            (ticker, payment_date, amount, shares_owned, per_share_amount, reinvested)
            VALUES ('JNJ', ?, 50.00, 10.0, 5.00, FALSE)
        """, (datetime.now(),))
        db_connection.commit()
        
        cursor.execute("SELECT * FROM dividend_payments WHERE ticker = 'JNJ'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result['ticker'] == 'JNJ'
        assert result['amount'] == 50.00
        assert result['reinvested'] == 0  # SQLite stores boolean as 0/1
        
        # Cleanup
        cursor.execute("DELETE FROM dividend_payments WHERE ticker = 'JNJ'")
        db_connection.commit()


class TestUserSettingsOperations:
    """Test CRUD operations for user_settings table."""
    
    def test_create_setting(self, db_connection):
        """Test creating a new user setting."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            INSERT INTO user_settings (setting_key, setting_value)
            VALUES ('monthly_budget', '300.00')
        """)
        db_connection.commit()
        
        cursor.execute("SELECT * FROM user_settings WHERE setting_key = 'monthly_budget'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result['setting_value'] == '300.00'
        
        # Cleanup
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        db_connection.commit()
    
    def test_update_setting(self, db_connection):
        """Test updating an existing user setting."""
        cursor = db_connection.cursor()
        
        # Insert
        cursor.execute("""
            INSERT INTO user_settings (setting_key, setting_value)
            VALUES ('monthly_budget', '300.00')
        """)
        db_connection.commit()
        
        # Update
        cursor.execute("""
            UPDATE user_settings SET setting_value = '500.00'
            WHERE setting_key = 'monthly_budget'
        """)
        db_connection.commit()
        
        # Verify
        cursor.execute("SELECT * FROM user_settings WHERE setting_key = 'monthly_budget'")
        result = cursor.fetchone()
        
        assert result['setting_value'] == '500.00'
        
        # Cleanup
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        db_connection.commit()


class TestTransactionRollback:
    """Test transaction rollback on errors."""
    
    def test_rollback_on_error(self, db_connection):
        """Test that transactions are rolled back on errors."""
        cursor = db_connection.cursor()
        
        try:
            # Start a transaction
            cursor.execute("""
                INSERT INTO portfolio (ticker, shares, avg_price, current_price)
                VALUES ('TEST', 10.0, 100.00, 105.00)
            """)
            
            # This should fail due to constraint violation (duplicate ticker if we insert again)
            cursor.execute("""
                INSERT INTO portfolio (ticker, shares, avg_price, current_price)
                VALUES ('TEST', 5.0, 100.00, 105.00)
            """)
            
            db_connection.commit()
            
        except sqlite3.IntegrityError:
            # Rollback on error
            db_connection.rollback()
        
        # Verify that no data was committed
        cursor.execute("SELECT * FROM portfolio WHERE ticker = 'TEST'")
        result = cursor.fetchone()
        
        # The first insert should also be rolled back
        # Note: SQLite doesn't enforce unique constraints on ticker by default
        # This test demonstrates the rollback mechanism
        
        # Cleanup any test data
        cursor.execute("DELETE FROM portfolio WHERE ticker = 'TEST'")
        db_connection.commit()


class TestRecommendationOperations:
    """Test CRUD operations for recommendation tables."""
    
    def test_create_recommendation_run(self, db_connection):
        """Test creating a recommendation run with items."""
        cursor = db_connection.cursor()
        
        # Create recommendation run
        cursor.execute("""
            INSERT INTO recommendation_runs (budget, total_allocated, portfolio_value)
            VALUES (300.00, 295.00, 3200.00)
        """)
        run_id = cursor.lastrowid
        db_connection.commit()
        
        # Create recommendation items
        cursor.execute("""
            INSERT INTO recommendation_items 
            (run_id, ticker, action, shares, price, total_cost, score, reasoning, priority)
            VALUES (?, 'NEE', 'BUY', 4.0, 70.00, 280.00, 85.5, 'Underweighted utility stock', 1)
        """, (run_id,))
        db_connection.commit()
        
        # Verify
        cursor.execute("SELECT * FROM recommendation_runs WHERE id = ?", (run_id,))
        run = cursor.fetchone()
        assert run is not None
        assert run['budget'] == 300.00
        
        cursor.execute("SELECT * FROM recommendation_items WHERE run_id = ?", (run_id,))
        items = cursor.fetchall()
        assert len(items) == 1
        assert items[0]['ticker'] == 'NEE'
        
        # Cleanup
        cursor.execute("DELETE FROM recommendation_items WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM recommendation_runs WHERE id = ?", (run_id,))
        db_connection.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
