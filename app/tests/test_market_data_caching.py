"""
Unit tests for market data caching functionality.
Tests cache hit/miss scenarios and staleness indicator logic.

**Validates: Requirements 7.6, 7.7**
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import market_data_service


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the cache before each test."""
    market_data_service._price_cache.clear()
    market_data_service._cache_timestamp.clear()
    yield
    market_data_service._price_cache.clear()
    market_data_service._cache_timestamp.clear()


class TestCacheHitMiss:
    """Test cache hit and miss scenarios."""
    
    def test_cache_miss_fetches_from_api(self):
        """Test that a cache miss fetches data from the API."""
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Mock yfinance response
            mock_data = MagicMock()
            mock_data.__getitem__.return_value.iloc = MagicMock()
            mock_data.__getitem__.return_value.iloc.__getitem__.return_value = 150.00
            mock_download.return_value = mock_data
            
            prices = market_data_service.get_prices(['AAPL'])
            
            # Verify API was called
            assert mock_download.called
            assert 'AAPL' in prices
            assert prices['AAPL'] == 150.00
    
    def test_cache_stores_fetched_prices(self):
        """Test that fetched prices are stored in cache."""
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Mock yfinance response
            mock_data = MagicMock()
            mock_data.__getitem__.return_value.iloc = MagicMock()
            mock_data.__getitem__.return_value.iloc.__getitem__.return_value = 150.00
            mock_download.return_value = mock_data
            
            market_data_service.get_prices(['AAPL'])
            
            # Verify cache was populated
            assert 'AAPL' in market_data_service._price_cache
            assert market_data_service._price_cache['AAPL'] == 150.00
            assert 'AAPL' in market_data_service._cache_timestamp
    
    def test_cache_hit_returns_cached_data_on_api_failure(self):
        """Test that cached data is returned when API fails."""
        # Pre-populate cache
        market_data_service._price_cache['MSFT'] = 300.00
        market_data_service._cache_timestamp['MSFT'] = datetime.now()
        
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Simulate API failure
            mock_download.side_effect = Exception("API Error")
            
            prices = market_data_service.get_prices(['MSFT'])
            
            # Verify cached data was returned
            assert 'MSFT' in prices
            assert prices['MSFT'] == 300.00
    
    def test_empty_ticker_list_returns_empty_dict(self):
        """Test that empty ticker list returns empty dictionary."""
        prices = market_data_service.get_prices([])
        assert prices == {}
    
    def test_multiple_tickers_cache_population(self):
        """Test that multiple tickers are all cached."""
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Mock yfinance response for multiple tickers
            mock_data = MagicMock()
            mock_close = MagicMock()
            
            # Setup mock for multiple tickers
            def mock_getitem(ticker):
                mock_ticker_data = MagicMock()
                mock_ticker_data.iloc = MagicMock()
                if ticker == 'AAPL':
                    mock_ticker_data.iloc.__getitem__.return_value = 150.00
                elif ticker == 'GOOGL':
                    mock_ticker_data.iloc.__getitem__.return_value = 2800.00
                return mock_ticker_data
            
            mock_close.__getitem__.side_effect = mock_getitem
            mock_data.__getitem__.return_value = mock_close
            mock_download.return_value = mock_data
            
            prices = market_data_service.get_prices(['AAPL', 'GOOGL'])
            
            # Verify both tickers are cached
            assert 'AAPL' in market_data_service._price_cache
            assert 'GOOGL' in market_data_service._price_cache
            assert 'AAPL' in market_data_service._cache_timestamp
            assert 'GOOGL' in market_data_service._cache_timestamp


class TestStalenessIndicator:
    """Test staleness indicator logic."""
    
    def test_fresh_cache_not_stale(self):
        """Test that recently cached data is not marked as stale."""
        # Populate cache with fresh data
        market_data_service._price_cache['JNJ'] = 160.00
        market_data_service._cache_timestamp['JNJ'] = datetime.now()
        
        result = market_data_service.get_cached_price('JNJ')
        
        assert result['ticker'] == 'JNJ'
        assert result['price'] == 160.00
        assert result['is_stale'] is False
        assert result['cached_at'] is not None
    
    def test_old_cache_is_stale(self):
        """Test that old cached data (>15 minutes) is marked as stale."""
        # Populate cache with old data
        market_data_service._price_cache['PG'] = 140.00
        old_timestamp = datetime.now() - timedelta(minutes=20)
        market_data_service._cache_timestamp['PG'] = old_timestamp
        
        result = market_data_service.get_cached_price('PG')
        
        assert result['ticker'] == 'PG'
        assert result['price'] == 140.00
        assert result['is_stale'] is True
        assert result['cached_at'] is not None
    
    def test_cache_at_15_minute_boundary(self):
        """Test staleness at exactly 15 minutes."""
        # Populate cache with data exactly 15 minutes old
        market_data_service._price_cache['NEE'] = 70.00
        boundary_timestamp = datetime.now() - timedelta(minutes=15)
        market_data_service._cache_timestamp['NEE'] = boundary_timestamp
        
        result = market_data_service.get_cached_price('NEE')
        
        assert result['ticker'] == 'NEE'
        assert result['price'] == 70.00
        # At exactly 15 minutes, should not be stale (age_minutes = 15, condition is > 15)
        assert result['is_stale'] is False
    
    def test_cache_just_over_15_minutes_is_stale(self):
        """Test that cache just over 15 minutes is marked as stale."""
        # Populate cache with data 16 minutes old
        market_data_service._price_cache['CVX'] = 155.00
        old_timestamp = datetime.now() - timedelta(minutes=16)
        market_data_service._cache_timestamp['CVX'] = old_timestamp
        
        result = market_data_service.get_cached_price('CVX')
        
        assert result['ticker'] == 'CVX'
        assert result['price'] == 155.00
        assert result['is_stale'] is True
    
    def test_missing_cache_returns_stale(self):
        """Test that missing cache entry returns stale indicator."""
        result = market_data_service.get_cached_price('UNKNOWN')
        
        assert result['ticker'] == 'UNKNOWN'
        assert result['price'] is None
        assert result['cached_at'] is None
        assert result['is_stale'] is True
    
    def test_cache_without_timestamp_not_stale(self):
        """Test that cache entry without timestamp is not marked as stale."""
        # Populate cache without timestamp (edge case)
        market_data_service._price_cache['TXN'] = 180.00
        # Don't set timestamp
        
        result = market_data_service.get_cached_price('TXN')
        
        assert result['ticker'] == 'TXN'
        assert result['price'] == 180.00
        assert result['cached_at'] is None
        assert result['is_stale'] is False


class TestCachePerformance:
    """Test cache performance and API call minimization."""
    
    def test_api_called_once_for_initial_fetch(self):
        """Test that API is called only once for initial data fetch."""
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Mock yfinance response
            mock_data = MagicMock()
            mock_data.__getitem__.return_value.iloc = MagicMock()
            mock_data.__getitem__.return_value.iloc.__getitem__.return_value = 150.00
            mock_download.return_value = mock_data
            
            # First call
            market_data_service.get_prices(['AAPL'])
            
            # Verify API was called exactly once
            assert mock_download.call_count == 1
    
    def test_cache_timestamp_updated_on_fetch(self):
        """Test that cache timestamp is updated when data is fetched."""
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Mock yfinance response
            mock_data = MagicMock()
            mock_data.__getitem__.return_value.iloc = MagicMock()
            mock_data.__getitem__.return_value.iloc.__getitem__.return_value = 150.00
            mock_download.return_value = mock_data
            
            before_fetch = datetime.now()
            market_data_service.get_prices(['AAPL'])
            after_fetch = datetime.now()
            
            # Verify timestamp is within expected range
            cached_time = market_data_service._cache_timestamp['AAPL']
            assert before_fetch <= cached_time <= after_fetch
    
    def test_fallback_to_cache_on_api_error(self):
        """Test that system falls back to cache when API fails."""
        # Pre-populate cache
        market_data_service._price_cache['UPS'] = 175.00
        market_data_service._cache_timestamp['UPS'] = datetime.now()
        
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Simulate API error
            mock_download.side_effect = Exception("Network error")
            
            prices = market_data_service.get_prices(['UPS'])
            
            # Verify cached data was used
            assert prices['UPS'] == 175.00
    
    def test_zero_price_for_uncached_ticker_on_api_error(self):
        """Test that zero price is returned for uncached ticker when API fails."""
        with patch('app.services.market_data_service.yf.download') as mock_download:
            # Simulate API error
            mock_download.side_effect = Exception("Network error")
            
            prices = market_data_service.get_prices(['NEWSTOCK'])
            
            # Verify zero price is returned
            assert prices['NEWSTOCK'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
