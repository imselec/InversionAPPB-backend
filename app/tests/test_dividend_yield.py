"""
Unit tests for dividend yield calculation.
Tests yield calculation for various stock prices and dividend amounts.

**Validates: Requirements 3.5**
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.dividend_service import DividendService


class TestDividendYieldCalculation:
    """Test dividend yield calculation logic."""
    
    def test_basic_yield_calculation(self):
        """Test basic dividend yield calculation."""
        service = DividendService()
        
        # Mock get_dividends to return known yield
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {'AAPL': {'yield': 0.005, 'payout': 0.15}}
            mock_prices.return_value = {'AAPL': 150.00}
            
            annual_dividend = service.get_annual_dividend('AAPL')
            
            # Expected: 150.00 * 0.005 = 0.75
            assert abs(annual_dividend - 0.75) < 0.01
    
    def test_high_yield_stock(self):
        """Test calculation for high dividend yield stock."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            # High yield stock (5%)
            mock_dividends.return_value = {'O': {'yield': 0.05, 'payout': 0.80}}
            mock_prices.return_value = {'O': 60.00}
            
            annual_dividend = service.get_annual_dividend('O')
            
            # Expected: 60.00 * 0.05 = 3.00
            assert abs(annual_dividend - 3.00) < 0.01
    
    def test_low_yield_stock(self):
        """Test calculation for low dividend yield stock."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            # Low yield stock (0.5%)
            mock_dividends.return_value = {'GOOGL': {'yield': 0.005, 'payout': 0.10}}
            mock_prices.return_value = {'GOOGL': 2800.00}
            
            annual_dividend = service.get_annual_dividend('GOOGL')
            
            # Expected: 2800.00 * 0.005 = 14.00
            assert abs(annual_dividend - 14.00) < 0.01
    
    def test_zero_yield_stock(self):
        """Test calculation for stock with no dividend."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            # No dividend
            mock_dividends.return_value = {'TSLA': {'yield': 0, 'payout': 0}}
            mock_prices.return_value = {'TSLA': 250.00}
            
            annual_dividend = service.get_annual_dividend('TSLA')
            
            # Expected: 0
            assert annual_dividend == 0
    
    def test_zero_price_returns_zero(self):
        """Test that zero price returns zero dividend."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {'TEST': {'yield': 0.03, 'payout': 0.50}}
            mock_prices.return_value = {'TEST': 0}
            
            annual_dividend = service.get_annual_dividend('TEST')
            
            # Expected: 0 (price is zero)
            assert annual_dividend == 0
    
    def test_missing_dividend_data_returns_zero(self):
        """Test that missing dividend data returns zero."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {}
            mock_prices.return_value = {'UNKNOWN': 100.00}
            
            annual_dividend = service.get_annual_dividend('UNKNOWN')
            
            # Expected: 0 (no dividend data)
            assert annual_dividend == 0
    
    def test_exception_handling_returns_zero(self):
        """Test that exceptions are handled gracefully."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends:
            # Simulate exception
            mock_dividends.side_effect = Exception("API Error")
            
            annual_dividend = service.get_annual_dividend('ERROR')
            
            # Expected: 0 (exception handled)
            assert annual_dividend == 0
    
    def test_various_price_points(self):
        """Test yield calculation at various price points."""
        service = DividendService()
        
        test_cases = [
            # (price, yield, expected_dividend)
            (10.00, 0.10, 1.00),      # $10 stock, 10% yield
            (50.00, 0.04, 2.00),      # $50 stock, 4% yield
            (100.00, 0.03, 3.00),     # $100 stock, 3% yield
            (500.00, 0.02, 10.00),    # $500 stock, 2% yield
            (1000.00, 0.01, 10.00),   # $1000 stock, 1% yield
        ]
        
        for price, div_yield, expected in test_cases:
            with patch.object(service, 'get_dividends') as mock_dividends, \
                 patch('app.services.market_data_service.get_prices') as mock_prices:
                
                mock_dividends.return_value = {'TEST': {'yield': div_yield, 'payout': 0.50}}
                mock_prices.return_value = {'TEST': price}
                
                annual_dividend = service.get_annual_dividend('TEST')
                
                assert abs(annual_dividend - expected) < 0.01, \
                    f"Price {price}, yield {div_yield}: expected {expected}, got {annual_dividend}"
    
    def test_yield_percentage_to_dollar_conversion(self):
        """Test that yield percentage is correctly converted to dollar amount."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            # 2.5% yield on $80 stock
            mock_dividends.return_value = {'PG': {'yield': 0.025, 'payout': 0.60}}
            mock_prices.return_value = {'PG': 80.00}
            
            annual_dividend = service.get_annual_dividend('PG')
            
            # Expected: 80.00 * 0.025 = 2.00
            assert abs(annual_dividend - 2.00) < 0.01
            
            # Verify it's a dollar amount, not percentage
            assert annual_dividend < 100, "Should be dollar amount, not percentage"
    
    def test_fractional_share_yield(self):
        """Test yield calculation works with fractional results."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            # Yield that results in fractional dollar amount
            mock_dividends.return_value = {'JNJ': {'yield': 0.0275, 'payout': 0.45}}
            mock_prices.return_value = {'JNJ': 163.50}
            
            annual_dividend = service.get_annual_dividend('JNJ')
            
            # Expected: 163.50 * 0.0275 = 4.49625
            assert abs(annual_dividend - 4.49625) < 0.01


class TestDividendYieldEdgeCases:
    """Test edge cases in dividend yield calculation."""
    
    def test_very_small_yield(self):
        """Test calculation with very small yield (0.1%)."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {'LOW': {'yield': 0.001, 'payout': 0.05}}
            mock_prices.return_value = {'LOW': 1000.00}
            
            annual_dividend = service.get_annual_dividend('LOW')
            
            # Expected: 1000.00 * 0.001 = 1.00
            assert abs(annual_dividend - 1.00) < 0.01
    
    def test_very_high_yield(self):
        """Test calculation with very high yield (15%)."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {'HIGH': {'yield': 0.15, 'payout': 0.95}}
            mock_prices.return_value = {'HIGH': 20.00}
            
            annual_dividend = service.get_annual_dividend('HIGH')
            
            # Expected: 20.00 * 0.15 = 3.00
            assert abs(annual_dividend - 3.00) < 0.01
    
    def test_penny_stock_yield(self):
        """Test calculation for penny stock."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {'PENNY': {'yield': 0.08, 'payout': 0.70}}
            mock_prices.return_value = {'PENNY': 0.50}
            
            annual_dividend = service.get_annual_dividend('PENNY')
            
            # Expected: 0.50 * 0.08 = 0.04
            assert abs(annual_dividend - 0.04) < 0.01
    
    def test_expensive_stock_yield(self):
        """Test calculation for expensive stock."""
        service = DividendService()
        
        with patch.object(service, 'get_dividends') as mock_dividends, \
             patch('app.services.market_data_service.get_prices') as mock_prices:
            
            mock_dividends.return_value = {'BRK.A': {'yield': 0.0001, 'payout': 0.01}}
            mock_prices.return_value = {'BRK.A': 500000.00}
            
            annual_dividend = service.get_annual_dividend('BRK.A')
            
            # Expected: 500000.00 * 0.0001 = 50.00
            assert abs(annual_dividend - 50.00) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
