"""
Property-based tests for budget change history recording.
Tests universal correctness properties using Hypothesis.
"""
import sys
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.settings_service import SettingsService
from app.database import get_connection, init_database


# Property 39: Budget Change History Recording
# Validates: Requirements 12.8
@given(
    budget_changes=st.lists(
        st.floats(min_value=50.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=10
    )
)
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_budget_change_history_recording(budget_changes):
    """
    **Validates: Requirements 12.8**
    
    Property: For any monthly budget change, the system shall record the change 
    with the effective date.
    
    This validates that:
    - Each budget change is recorded in the history
    - Each history entry includes the effective date
    - The history can be retrieved in chronological order
    - The recorded budget values match the changes made
    
    Validates Requirement 12.8: THE Frontend_Application SHALL display a history 
    of Monthly_Budget changes with effective dates
    """
    settings_service = SettingsService()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clean up any existing budget history
        cursor.execute("DELETE FROM transactions WHERE transaction_type = 'BUDGET_CHANGE'")
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        
        # Apply each budget change
        for budget in budget_changes:
            settings_service.update_monthly_budget(budget)
        
        # Retrieve the budget change history
        history = settings_service.get_budget_change_history(limit=len(budget_changes))
        
        # Verify that the number of history entries matches the number of changes
        assert len(history) == len(budget_changes), \
            f"Expected {len(budget_changes)} history entries, got {len(history)}"
        
        # Verify each history entry has required fields
        for entry in history:
            assert "date" in entry, "History entry missing 'date' field"
            assert "new_budget" in entry, "History entry missing 'new_budget' field"
            assert "notes" in entry, "History entry missing 'notes' field"
            
            # Verify date is a valid ISO format timestamp
            try:
                datetime.fromisoformat(entry["date"])
            except (ValueError, TypeError):
                pytest.fail(f"Invalid date format in history entry: {entry['date']}")
            
            # Verify new_budget is a valid number
            assert isinstance(entry["new_budget"], (int, float)), \
                f"Budget value should be numeric, got {type(entry['new_budget'])}"
            assert entry["new_budget"] >= 50.0, \
                f"Budget value in history should be >= 50, got {entry['new_budget']}"
        
        # Verify history is in reverse chronological order (most recent first)
        for i in range(len(history) - 1):
            date1 = datetime.fromisoformat(history[i]["date"])
            date2 = datetime.fromisoformat(history[i + 1]["date"])
            assert date1 >= date2, \
                "History entries should be in reverse chronological order"
        
        # Verify the budget values in history match the changes made (in reverse order)
        for i, entry in enumerate(history):
            expected_budget = budget_changes[-(i + 1)]  # Reverse order
            assert abs(entry["new_budget"] - expected_budget) < 0.01, \
                f"Budget mismatch: expected {expected_budget}, got {entry['new_budget']}"
    
    finally:
        # Cleanup
        cursor.execute("DELETE FROM transactions WHERE transaction_type = 'BUDGET_CHANGE'")
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        conn.close()


def test_budget_history_single_change():
    """
    Test that a single budget change is recorded correctly.
    """
    settings_service = SettingsService()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clean up
        cursor.execute("DELETE FROM transactions WHERE transaction_type = 'BUDGET_CHANGE'")
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        
        # Make a single budget change
        test_budget = 500.0
        result = settings_service.update_monthly_budget(test_budget)
        
        # Retrieve history
        history = settings_service.get_budget_change_history(limit=10)
        
        # Verify single entry exists
        assert len(history) == 1, f"Expected 1 history entry, got {len(history)}"
        
        # Verify the entry details
        entry = history[0]
        assert abs(entry["new_budget"] - test_budget) < 0.01
        assert "date" in entry
        assert "notes" in entry
        assert f"${test_budget}" in entry["notes"]
        
    finally:
        # Cleanup
        cursor.execute("DELETE FROM transactions WHERE transaction_type = 'BUDGET_CHANGE'")
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        conn.close()


def test_budget_history_limit():
    """
    Test that the history limit parameter works correctly.
    """
    settings_service = SettingsService()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clean up
        cursor.execute("DELETE FROM transactions WHERE transaction_type = 'BUDGET_CHANGE'")
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        
        # Make multiple budget changes
        budgets = [100.0, 200.0, 300.0, 400.0, 500.0]
        for budget in budgets:
            settings_service.update_monthly_budget(budget)
        
        # Retrieve with limit
        history = settings_service.get_budget_change_history(limit=3)
        
        # Verify only 3 entries returned
        assert len(history) == 3, f"Expected 3 history entries, got {len(history)}"
        
        # Verify they are the most recent 3 (in reverse order)
        assert abs(history[0]["new_budget"] - 500.0) < 0.01
        assert abs(history[1]["new_budget"] - 400.0) < 0.01
        assert abs(history[2]["new_budget"] - 300.0) < 0.01
        
    finally:
        # Cleanup
        cursor.execute("DELETE FROM transactions WHERE transaction_type = 'BUDGET_CHANGE'")
        cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    # Initialize database if needed
    init_database()
    
    # Run the property test
    print("Running Property 39: Budget Change History Recording...")
    test_property_budget_change_history_recording()
    print("✓ Property 39 passed!")
    
    print("\nRunning single change test...")
    test_budget_history_single_change()
    print("✓ Single change test passed!")
    
    print("\nRunning history limit test...")
    test_budget_history_limit()
    print("✓ History limit test passed!")

