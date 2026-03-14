"""
Unit tests for watchlist API endpoints.
Tests Requirements 15.1, 15.2, 15.3, 15.6, 15.7
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_ITEM = {
    "id": 1, "user_id": 1, "ticker": "MSFT",
    "added_at": "2026-01-01T00:00:00",
    "notes": None, "target_price": None,
}
SAMPLE_METRICS = {
    **SAMPLE_ITEM,
    "current_price": 300.0, "dividend_yield": 0.008,
    "pe_ratio": 32.0, "market_cap": 2_000_000_000_000,
    "sector": "Technology", "industry": "Software",
}


# ---------------------------------------------------------------------------
# POST /watchlist
# ---------------------------------------------------------------------------

class TestAddToWatchlist:
    def test_add_valid_ticker(self):
        """POST /watchlist with valid ticker returns 200."""
        with patch(
            "app.api.watchlist_api.watchlist_service.add_to_watchlist",
            return_value=SAMPLE_ITEM,
        ):
            response = client.post("/watchlist", json={"ticker": "MSFT"})
        assert response.status_code == 200
        assert response.json()["ticker"] == "MSFT"

    def test_add_empty_ticker_returns_400(self):
        """POST /watchlist with empty ticker returns 400."""
        response = client.post("/watchlist", json={"ticker": ""})
        assert response.status_code == 400

    def test_add_etf_returns_400(self):
        """POST /watchlist with ETF ticker returns 400."""
        with patch(
            "app.api.watchlist_api.watchlist_service.add_to_watchlist",
            side_effect=ValueError("SPY is an ETF"),
        ):
            response = client.post("/watchlist", json={"ticker": "SPY"})
        assert response.status_code == 400
        assert "ETF" in response.json()["detail"]

    def test_add_duplicate_returns_400(self):
        """POST /watchlist with duplicate ticker returns 400."""
        with patch(
            "app.api.watchlist_api.watchlist_service.add_to_watchlist",
            side_effect=ValueError("Could not add MSFT"),
        ):
            response = client.post("/watchlist", json={"ticker": "MSFT"})
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /watchlist
# ---------------------------------------------------------------------------

class TestGetWatchlist:
    def test_get_watchlist_returns_list(self):
        """GET /watchlist returns items with count."""
        with patch(
            "app.api.watchlist_api.watchlist_service.get_watchlist_metrics",
            return_value=[SAMPLE_METRICS],
        ):
            response = client.get("/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert "watchlist" in data
        assert data["count"] == 1

    def test_get_watchlist_empty(self):
        """GET /watchlist returns empty list when no items."""
        with patch(
            "app.api.watchlist_api.watchlist_service.get_watchlist_metrics",
            return_value=[],
        ):
            response = client.get("/watchlist")
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_get_watchlist_includes_metrics(self):
        """GET /watchlist items include market metrics fields."""
        with patch(
            "app.api.watchlist_api.watchlist_service.get_watchlist_metrics",
            return_value=[SAMPLE_METRICS],
        ):
            response = client.get("/watchlist")
        item = response.json()["watchlist"][0]
        for field in ["current_price", "dividend_yield", "pe_ratio",
                      "market_cap", "sector", "industry"]:
            assert field in item


# ---------------------------------------------------------------------------
# DELETE /watchlist/{ticker}
# ---------------------------------------------------------------------------

class TestRemoveFromWatchlist:
    def test_remove_existing_ticker(self):
        """DELETE /watchlist/MSFT returns success message."""
        with patch(
            "app.api.watchlist_api.watchlist_service.remove_from_watchlist",
            return_value=True,
        ):
            response = client.delete("/watchlist/MSFT")
        assert response.status_code == 200
        assert "removed" in response.json()["message"].lower()

    def test_remove_nonexistent_ticker_returns_404(self):
        """DELETE /watchlist/UNKNOWN returns 404."""
        with patch(
            "app.api.watchlist_api.watchlist_service.remove_from_watchlist",
            return_value=False,
        ):
            response = client.delete("/watchlist/UNKNOWN")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /watchlist/{ticker}
# ---------------------------------------------------------------------------

class TestGetWatchlistTicker:
    def test_get_existing_ticker(self):
        """GET /watchlist/MSFT returns the item."""
        with patch(
            "app.api.watchlist_api.watchlist_service.get_watchlist_metrics",
            return_value=[SAMPLE_METRICS],
        ):
            response = client.get("/watchlist/MSFT")
        assert response.status_code == 200
        assert response.json()["ticker"] == "MSFT"

    def test_get_nonexistent_ticker_returns_404(self):
        """GET /watchlist/UNKNOWN returns 404."""
        with patch(
            "app.api.watchlist_api.watchlist_service.get_watchlist_metrics",
            return_value=[],
        ):
            response = client.get("/watchlist/UNKNOWN")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /watchlist/compare/{ticker}
# ---------------------------------------------------------------------------

class TestCompareWithHoldings:
    def test_compare_returns_comparison_data(self):
        """GET /watchlist/compare/MSFT returns comparison metrics."""
        comparison = {
            "ticker": "MSFT",
            "sector": "Technology",
            "industry": "Software",
            "dividend_yield": 0.008,
            "pe_ratio": 32.0,
            "market_cap": 2_000_000_000_000,
            "portfolio_avg_dividend_yield": 0.025,
            "portfolio_avg_pe_ratio": 18.0,
            "yield_vs_portfolio": -0.017,
            "pe_vs_portfolio": 14.0,
        }
        with patch(
            "app.api.watchlist_api.watchlist_service.compare_with_holdings",
            return_value=comparison,
        ):
            response = client.get("/watchlist/compare/MSFT")
        assert response.status_code == 200
        data = response.json()
        assert "portfolio_avg_dividend_yield" in data
        assert "yield_vs_portfolio" in data


# ---------------------------------------------------------------------------
# GET /watchlist/prioritized
# ---------------------------------------------------------------------------

class TestGetPrioritizedWatchlist:
    def test_prioritized_returns_sorted_list(self):
        """GET /watchlist/prioritized returns items with scores."""
        items = [
            {**SAMPLE_METRICS, "ticker": "JNJ", "score": 12.5},
            {**SAMPLE_METRICS, "ticker": "MSFT", "score": 8.0},
        ]
        with patch(
            "app.api.watchlist_api.watchlist_service.get_prioritized_watchlist",
            return_value=items,
        ):
            response = client.get("/watchlist/prioritized")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        scores = [i["score"] for i in data["watchlist"]]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# GET /watchlist/{ticker}/allocation-impact
# ---------------------------------------------------------------------------

class TestAllocationImpact:
    def test_allocation_impact_returns_data(self):
        """GET /watchlist/MSFT/allocation-impact returns impact data."""
        impact = {
            "ticker": "MSFT", "shares": 1,
            "current_price": 300.0, "purchase_value": 300.0,
            "portfolio_value_before": 50000.0,
            "portfolio_value_after": 50300.0,
            "current_allocation_pct": 0.0,
            "new_allocation_pct": 0.596,
            "impact_pct": 0.596,
        }
        with patch(
            "app.api.watchlist_api.watchlist_service.calculate_allocation_impact",
            return_value=impact,
        ):
            response = client.get("/watchlist/MSFT/allocation-impact")
        assert response.status_code == 200
        data = response.json()
        assert "impact_pct" in data
        assert "new_allocation_pct" in data

    def test_allocation_impact_shares_param(self):
        """GET /watchlist/MSFT/allocation-impact?shares=5 passes shares."""
        impact = {
            "ticker": "MSFT", "shares": 5,
            "current_price": 300.0, "purchase_value": 1500.0,
            "portfolio_value_before": 50000.0,
            "portfolio_value_after": 51500.0,
            "current_allocation_pct": 0.0,
            "new_allocation_pct": 2.91,
            "impact_pct": 2.91,
        }
        with patch(
            "app.api.watchlist_api.watchlist_service.calculate_allocation_impact",
            return_value=impact,
        ) as mock_calc:
            response = client.get("/watchlist/MSFT/allocation-impact?shares=5")
        assert response.status_code == 200
        mock_calc.assert_called_once_with(ticker="MSFT", shares=5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
