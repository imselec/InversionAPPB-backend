"""
Property-based tests for budget validation.
Tests universal correctness properties using Hypothesis.
"""
import sys
from pathlib import Path
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.settings_service import SettingsService
from app.database import get_connection, init_database


# Property 37: Budget Validation
# Validates: Requirements 12.2
@given(budget=st.floats(min_value=-1000000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False))
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_budget_validation(budget):
    """
    **Validates: Requirements 12.2**
    
    Property: For any monthly budget input, the system shall validate that 
    the value is a positive number greater than $50.
    
    This validates that:
    - Budget values less than $50 are rejected with ValueError
    - Budget values greater than or equal to $50 are accepted
    - The validation is consistent across all input values
    
    Validates Requirement 12.2: THE Frontend_Application SHALL validate that 
    the Monthly_Budget is a positive number greater than $50
    """
    settings_service = SettingsService()
    
    if budget < 50:
        # Budget below minimum should raise ValueError
        with pytest.raises(ValueError, match="Monthly budget must be at least \\$50"):
            settings_service.update_monthly_budget(budget)
    else:
        # Budget at or above minimum should succeed
        try:
            result = settings_service.update_monthly_budget(budget)
            
            # Verify the result structure
            assert "monthly_budget" in result
            assert result["monthly_budget"] == budget
            assert "updated_at" in result
            assert "message" in result
            
            # Verify the budget was actually stored
            retrieved_budget = settings_service.get_monthly_budget()
            assert abs(retrieved_budget - budget) < 0.01, \
                f"Budget validation succeeded but storage failed: expected {budget}, got {retrieved_budget}"
        finally:
            # Cleanup: remove the test budget setting
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
            conn.commit()
            conn.close()


# Additional edge case tests for specific boundary values
def test_budget_validation_edge_cases():
    """
    Test specific edge cases for budget validation.
    """
    settings_service = SettingsService()
    
    # Test exactly $50 (minimum valid value)
    result = settings_service.update_monthly_budget(50.0)
    assert result["monthly_budget"] == 50.0
    
    # Cleanup
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
    conn.commit()
    
    # Test $49.99 (just below minimum)
    with pytest.raises(ValueError, match="Monthly budget must be at least \\$50"):
        settings_service.update_monthly_budget(49.99)
    
    # Test $50.01 (just above minimum)
    result = settings_service.update_monthly_budget(50.01)
    assert result["monthly_budget"] == 50.01
    
    # Cleanup
    cursor.execute("DELETE FROM user_settings WHERE setting_key = 'monthly_budget'")
    conn.commit()
    
    # Test zero
    with pytest.raises(ValueError, match="Monthly budget must be at least \\$50"):
        settings_service.update_monthly_budget(0.0)
    
    # Test negative value
    with pytest.raises(ValueError, match="Monthly budget must be at least \\$50"):
        settings_service.update_monthly_budget(-100.0)
    
    conn.close()


if __name__ == "__main__":
    # Initialize database if needed
    init_database()
    
    # Run the property test
    print("Running Property 37: Budget Validation...")
    test_property_budget_validation()
    print("✓ Property 37 passed!")
    
    print("\nRunning edge case tests...")
    test_budget_validation_edge_cases()
    print("✓ Edge case tests passed!")

