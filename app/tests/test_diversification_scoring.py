"""
Unit tests for diversification scoring in NewTickerDiscoveryService.
Tests sector diversification bonus calculation.

**Validates: Requirements 11.2, 11.5**
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.new_ticker_discovery_service import NewTickerDiscoveryService


def make_ticker_info(sector: str, industry: str = "Test Industry") -> dict:
    """Helper to build a minimal yfinance info dict."""
    return {"sector": sector, "industry": industry}


class TestDiversificationScoreNewSector:
    """Tests for the new-sector case (score = 20)."""

    def test_new_sector_returns_score_20(self):
        """A ticker in a sector not present in current holdings gets score 20."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            # Candidate ticker is in "Healthcare"
            candidate_mock = MagicMock()
            candidate_mock.info = make_ticker_info("Healthcare")

            # Existing holding is in "Technology"
            holding_mock = MagicMock()
            holding_mock.info = make_ticker_info("Technology")

            mock_yf.side_effect = lambda t: candidate_mock if t == "JNJ" else holding_mock

            result = service.evaluate_diversification_benefit("JNJ", ["AAPL"])

        assert result["diversification_score"] == 20

    def test_new_sector_explanation_mentions_sector(self):
        """Explanation for a new sector should mention the sector name."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            candidate_mock = MagicMock()
            candidate_mock.info = make_ticker_info("Utilities")

            holding_mock = MagicMock()
            holding_mock.info = make_ticker_info("Technology")

            mock_yf.side_effect = lambda t: candidate_mock if t == "NEE" else holding_mock

            result = service.evaluate_diversification_benefit("NEE", ["AAPL"])

        assert "Utilities" in result["explanation"]

    def test_new_sector_with_empty_holdings(self):
        """Any ticker is a new sector when the portfolio is empty."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            candidate_mock = MagicMock()
            candidate_mock.info = make_ticker_info("Energy")
            mock_yf.return_value = candidate_mock

            result = service.evaluate_diversification_benefit("XOM", [])

        assert result["diversification_score"] == 20
        assert result["sector_count"] == 0

    def test_new_sector_with_multiple_different_holdings(self):
        """Ticker in a unique sector among many existing sectors still scores 20."""
        service = NewTickerDiscoveryService()

        sectors = ["Technology", "Financials", "Consumer Staples", "Industrials"]
        holding_tickers = ["AAPL", "JPM", "PG", "CAT"]

        with patch("yfinance.Ticker") as mock_yf:
            candidate_mock = MagicMock()
            candidate_mock.info = make_ticker_info("Real Estate")

            def side_effect(t):
                if t == "O":
                    return candidate_mock
                idx = holding_tickers.index(t)
                m = MagicMock()
                m.info = make_ticker_info(sectors[idx])
                return m

            mock_yf.side_effect = side_effect

            result = service.evaluate_diversification_benefit("O", holding_tickers)

        assert result["diversification_score"] == 20
        assert result["sector_count"] == 0


class TestDiversificationScoreExistingSector:
    """Tests for the existing-sector case (score = 10 / (sector_count + 1))."""

    def test_one_existing_holding_in_sector(self):
        """One existing holding in same sector → score = 10 / (1+1) = 5.0."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            tech_mock = MagicMock()
            tech_mock.info = make_ticker_info("Technology")
            mock_yf.return_value = tech_mock

            result = service.evaluate_diversification_benefit("MSFT", ["AAPL"])

        assert result["diversification_score"] == pytest.approx(5.0, abs=0.01)
        assert result["sector_count"] == 1

    def test_two_existing_holdings_in_sector(self):
        """Two existing holdings in same sector → score = 10 / (2+1) ≈ 3.33."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            tech_mock = MagicMock()
            tech_mock.info = make_ticker_info("Technology")
            mock_yf.return_value = tech_mock

            result = service.evaluate_diversification_benefit("NVDA", ["AAPL", "MSFT"])

        assert result["diversification_score"] == pytest.approx(10 / 3, abs=0.01)
        assert result["sector_count"] == 2

    def test_three_existing_holdings_in_sector(self):
        """Three existing holdings in same sector → score = 10 / (3+1) = 2.5."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            tech_mock = MagicMock()
            tech_mock.info = make_ticker_info("Technology")
            mock_yf.return_value = tech_mock

            result = service.evaluate_diversification_benefit("GOOGL", ["AAPL", "MSFT", "NVDA"])

        assert result["diversification_score"] == pytest.approx(2.5, abs=0.01)
        assert result["sector_count"] == 3

    def test_score_decreases_as_sector_count_increases(self):
        """Score should decrease monotonically as more holdings share the sector."""
        service = NewTickerDiscoveryService()

        scores = []
        for n_holdings in range(1, 6):
            holdings = [f"HOLD{i}" for i in range(n_holdings)]

            with patch("yfinance.Ticker") as mock_yf:
                tech_mock = MagicMock()
                tech_mock.info = make_ticker_info("Technology")
                mock_yf.return_value = tech_mock

                result = service.evaluate_diversification_benefit("NEW", holdings)
                scores.append(result["diversification_score"])

        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], (
                f"Score should decrease: scores[{i}]={scores[i]} not > scores[{i+1}]={scores[i+1]}"
            )

    def test_well_represented_sector_explanation(self):
        """Explanation should note sector is well-represented when sector_count >= 3."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            tech_mock = MagicMock()
            tech_mock.info = make_ticker_info("Technology")
            mock_yf.return_value = tech_mock

            result = service.evaluate_diversification_benefit(
                "GOOGL", ["AAPL", "MSFT", "NVDA"]
            )

        assert "well-represented" in result["explanation"].lower() or \
               "well represented" in result["explanation"].lower()

    def test_moderate_diversification_explanation(self):
        """Explanation should mention moderate benefit when sector_count < 3."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            tech_mock = MagicMock()
            tech_mock.info = make_ticker_info("Technology")
            mock_yf.return_value = tech_mock

            result = service.evaluate_diversification_benefit("MSFT", ["AAPL"])

        assert "moderate" in result["explanation"].lower()


class TestDiversificationScoreReturnStructure:
    """Tests for the structure and types of the returned dict."""

    def test_return_contains_required_keys(self):
        """Result must contain all required keys."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            m = MagicMock()
            m.info = make_ticker_info("Healthcare", "Pharmaceuticals")
            mock_yf.return_value = m

            result = service.evaluate_diversification_benefit("JNJ", [])

        required_keys = {"ticker", "sector", "industry", "sector_count", "diversification_score", "explanation"}
        assert required_keys.issubset(result.keys())

    def test_score_is_rounded_to_two_decimals(self):
        """Diversification score should be rounded to 2 decimal places."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            tech_mock = MagicMock()
            tech_mock.info = make_ticker_info("Technology")
            mock_yf.return_value = tech_mock

            # sector_count=2 → 10/3 = 3.333... → rounded to 3.33
            result = service.evaluate_diversification_benefit("GOOGL", ["AAPL", "MSFT"])

        score_str = str(result["diversification_score"])
        decimal_places = len(score_str.split(".")[-1]) if "." in score_str else 0
        assert decimal_places <= 2

    def test_ticker_field_matches_input(self):
        """Returned ticker field should match the input ticker."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            m = MagicMock()
            m.info = make_ticker_info("Energy")
            mock_yf.return_value = m

            result = service.evaluate_diversification_benefit("XOM", [])

        assert result["ticker"] == "XOM"

    def test_sector_and_industry_populated(self):
        """Sector and industry should be populated from yfinance info."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            m = MagicMock()
            m.info = make_ticker_info("Consumer Staples", "Household Products")
            mock_yf.return_value = m

            result = service.evaluate_diversification_benefit("PG", [])

        assert result["sector"] == "Consumer Staples"
        assert result["industry"] == "Household Products"


class TestDiversificationScoreErrorHandling:
    """Tests for error handling in evaluate_diversification_benefit."""

    def test_yfinance_exception_returns_safe_defaults(self):
        """When yfinance raises an exception, return safe default values."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker", side_effect=Exception("API error")):
            result = service.evaluate_diversification_benefit("BROKEN", ["AAPL"])

        assert result["ticker"] == "BROKEN"
        assert result["sector"] == "Unknown"
        assert result["diversification_score"] == 0

    def test_holding_with_missing_sector_is_skipped(self):
        """Holdings that fail sector lookup should be skipped without crashing."""
        service = NewTickerDiscoveryService()

        with patch("yfinance.Ticker") as mock_yf:
            candidate_mock = MagicMock()
            candidate_mock.info = make_ticker_info("Technology")

            bad_holding_mock = MagicMock()
            bad_holding_mock.info = MagicMock(side_effect=Exception("lookup failed"))

            good_holding_mock = MagicMock()
            good_holding_mock.info = make_ticker_info("Financials")

            def side_effect(t):
                if t == "NEW":
                    return candidate_mock
                if t == "BAD":
                    return bad_holding_mock
                return good_holding_mock

            mock_yf.side_effect = side_effect

            # Should not raise; BAD holding is skipped
            result = service.evaluate_diversification_benefit("NEW", ["BAD", "JPM"])

        assert result["diversification_score"] == 20  # Technology not in Financials


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
