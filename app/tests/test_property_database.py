"""
Property-based tests for database schema integrity.
Tests universal correctness properties using Hypothesis.
"""
import sqlite3
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_connection, init_database, DATABASE_PATH


# Property 38: Budget Persistence Round-Trip
# Validates: Requirements 12.3
@given(budget=st.floats(min_value=50.0, max_value=100000.0, allow_nan=False, allow_infinity=False))
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_budget_persistence_round_trip(budget):
    """
    Property: Any valid budget value persisted to the database can be retrieved 
    with the same value (round-trip property).
    
    This validates that:
    - Budget values are stored correctly in the database
    - Budget values can be retrieved without data loss
    - The persistence mechanism maintains data integrity
    
    Validates Requirement 12.3: WHEN the Monthly_Budget is changed, 
    THE Frontend_Application SHALL persist the new value for future sessions
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Store the budget value
        cursor.execute("""
            INSERT OR REPLACE INTO user_settings (setting_key, setting_value)
            VALUES ('monthly_budget', ?)
        """, (str(budget),))
        conn.commit()
        
        # Retrieve the budget value
        cursor.execute("""
            SELECT setting_value FROM user_settings 
            WHERE setting_key = 'monthly_budget'
        """)
        result = cursor.fetchone()
        
        # Verify round-trip property
        assert result is not None, "Budget value was not persisted"
        retrieved_budget = float(result[0])
        
        # Allow for minimal floating point precision differences
        assert abs(retrieved_budget - budget) < 0.01, \
            f"Budget round-trip failed: stored {budget}, retrieved {retrieved_budget}"
        
    finally:
        # Cleanup
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    # Initialize database if needed
    init_database()
    
    # Run the property test
    print("Running Property 38: Budget Persistence Round-Trip...")
    test_property_budget_persistence_round_trip()
    print("✓ Property 38 passed!")

