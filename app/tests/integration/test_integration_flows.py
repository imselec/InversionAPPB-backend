"""
Integration tests for frontend-backend communication flows.

Tests the complete data flows between frontend and backend:
- Portfolio data flow (Requirements 1.1, 1.2)
- Recommendation generation flow (Requirements 1.3)
- Dividend data synchronization (Requirements 1.1, 1.2)
- Alert creation and triggering flow (Requirements 14.1)
- Watchlist operations flow (Requirements 15.1)
- Error handling scenarios (Requirement 1.4)
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_PRICES = {
    "AVGO": 900.00, "PG": 145.00, "NEE": 70.00,
    "JNJ": 165.00, "UPS": 185.00, "CVX": 155.00,
    "XOM": 115.00, "ABBV": 175.00,
}

MOCK_PORTFOLIO_DB = [
    {"ticker": "AVGO", "shares": 1.0, "avg_price": 800.0, "current_price": 900.0, "last_updated": "2026-01-01"},
    {"ticker": "PG", "shares": 2.0, "avg_price": 140.0, "current_price": 145.0, "last_updated": "2026-01-01"},
    {"ticker": "NEE", "shares": 3.0, "avg_price": 65.0, "current_price": 70.0, "last_updated": "2026-01-01"},
]

MOCK_DIVIDENDS = {t: {"yield": 0.025, "payout": 0.50} for t in MOCK_PRICES}
MOCK_VALUATIONS = {t: 18.0 for t in MOCK_PRICES}
MOCK_SCORES = {t: 10.0 for t in MOCK_PRICES}

SAMPLE_ALERT = {
    "id": 1,
    "user_id": 1,
    "alert_type": "price",
    "ticker": "AVGO",
    "target_price": 950.0,
    "enabled": True,
    "last_triggered": None,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}

SAMPLE_WATCHLIST_ITEM = {
    "id": 1,
    "user_id": 1,
    "ticker": "MSFT",
    "added_at": "2026-01-01T00:00:00",
    "notes": None,
    "target_price": None,
    "current_price": 300.0,
    "dividend_yield": 0.008,
    "pe_ratio": 32.0,
    "market_cap": 2_000_000_000_000,
    "sector": "Technology",
    "industry": "Software",
}


# ===========================================================================
# 1. Portfolio Data Flow
# Tests: GET /portfolio/snapshot, GET /portfolio/dashboard, GET /portfolio/allocation
# Requirements: 1.1, 1.2
# ===========================================================================

class TestPortfolioDataFlow:
    """Integration tests for portfolio data flow from backend to dashboard."""

    def _portfolio_patches(self):
        return [
            patch("app.services.portfolio_service.load_portfolio_from_db", return_value=MOCK_PORTFOLIO_DB),
            patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES),
            patch("app.services.portfolio_service.update_current_prices"),
        ]

    def test_snapshot_returns_holdings_with_prices_and_values(self):
        """GET /portfolio/snapshot returns positions with ticker, shares, price, value."""
        with patch("app.services.portfolio_service.load_portfolio_from_db", return_value=MOCK_PORTFOLIO_DB), \
             patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.portfolio_service.update_current_prices"):
            response = client.get("/portfolio/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "positions" in data
        assert isinstance(data["positions"], list)
        assert len(data["positions"]) > 0
        for pos in data["positions"]:
            assert "ticker" in pos
            assert "shares" in pos
            assert "price" in pos
            assert "value" in pos
            assert pos["price"] >= 0
            assert pos["value"] >= 0

    def test_snapshot_total_value_equals_sum_of_positions(self):
        """Total portfolio value equals sum of individual position values."""
        with patch("app.services.portfolio_service.load_portfolio_from_db", return_value=MOCK_PORTFOLIO_DB), \
             patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.portfolio_service.update_current_prices"):
            response = client.get("/portfolio/snapshot")

        assert response.status_code == 200
        data = response.json()
        position_sum = sum(p["value"] for p in data["positions"])
        assert abs(data["total_value"] - position_sum) < 0.01

    def test_snapshot_positions_have_allocation_percentages(self):
        """Each position includes allocation_pct that sums to ~100%."""
        with patch("app.services.portfolio_service.load_portfolio_from_db", return_value=MOCK_PORTFOLIO_DB), \
             patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.portfolio_service.update_current_prices"):
            response = client.get("/portfolio/snapshot")

        assert response.status_code == 200
        data = response.json()
        total_alloc = sum(p["allocation_pct"] for p in data["positions"])
        assert abs(total_alloc - 100.0) < 0.1

    def test_dashboard_returns_summary_with_gain_loss(self):
        """GET /portfolio/dashboard returns total value, invested, and gain/loss."""
        with patch("app.services.portfolio_service.load_portfolio_from_db", return_value=MOCK_PORTFOLIO_DB), \
             patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.portfolio_service.update_current_prices"):
            response = client.get("/portfolio/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "total_invested" in data
        assert "total_gain_loss" in data
        assert "total_gain_loss_pct" in data
        assert "positions" in data

    def test_allocation_returns_percentages_per_ticker(self):
        """GET /portfolio/allocation returns allocation percentages for each ticker."""
        with patch("app.services.portfolio_service.load_portfolio_from_db", return_value=MOCK_PORTFOLIO_DB), \
             patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.portfolio_service.update_current_prices"):
            response = client.get("/portfolio/allocation")

        assert response.status_code == 200
        data = response.json()
        assert "allocations" in data
        assert "total_value" in data
        assert len(data["allocations"]) > 0
        for alloc in data["allocations"]:
            assert "ticker" in alloc
            assert "allocation_pct" in alloc
            assert 0 <= alloc["allocation_pct"] <= 100


# ===========================================================================
# 2. Recommendation Generation Flow
# Tests: POST /recommendations/generate, GET /recommendations/latest
# Requirements: 1.3
# ===========================================================================

class TestRecommendationFlow:
    """Integration tests for recommendation generation flow."""

    def _mock_engine_patches(self, tickers=None):
        if tickers is None:
            tickers = ["AVGO", "PG", "NEE"]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"ticker": t} for t in tickers]
        mock_cursor.fetchone.return_value = {"portfolio_value": 5000.0}
        mock_conn.close = MagicMock()
        return mock_conn

    def test_generate_returns_recommendations_within_budget(self):
        """POST /recommendations/generate returns recommendations within budget."""
        budget = 300.0
        mock_conn = self._mock_engine_patches(["AVGO", "PG", "NEE"])
        with patch("app.services.recommendation_engine.get_connection", return_value=mock_conn), \
             patch("app.services.recommendation_engine.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.recommendation_engine.DividendService.get_dividends", return_value=MOCK_DIVIDENDS), \
             patch("app.services.recommendation_engine.ValuationService.get_valuation", return_value=MOCK_VALUATIONS), \
             patch("app.services.recommendation_engine.ScoringService.compute_score", return_value=MOCK_SCORES):
            response = client.post("/recommendations/generate", json={"budget": budget})

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "budget" in data
        assert "total_allocated" in data
        assert data["budget"] == budget
        assert data["total_allocated"] <= budget

    def test_generate_recommendations_have_required_fields(self):
        """Each recommendation includes ticker, shares, price, total_cost, reasoning."""
        budget = 500.0
        mock_conn = self._mock_engine_patches(["PG", "NEE"])
        with patch("app.services.recommendation_engine.get_connection", return_value=mock_conn), \
             patch("app.services.recommendation_engine.get_prices", return_value=MOCK_PRICES), \
             patch("app.services.recommendation_engine.DividendService.get_dividends", return_value=MOCK_DIVIDENDS), \
             patch("app.services.recommendation_engine.ValuationService.get_valuation", return_value=MOCK_VALUATIONS), \
             patch("app.services.recommendation_engine.ScoringService.compute_score", return_value=MOCK_SCORES):
            response = client.post("/recommendations/generate", json={"budget": budget})

        assert response.status_code == 200
        data = response.json()
        for rec in data["recommendations"]:
            assert "ticker" in rec
            assert "shares" in rec
            assert "price" in rec
            assert "total_cost" in rec
            assert "reasoning" in rec
            assert "priority" in rec
            assert rec["shares"] > 0
            assert rec["price"] > 0
            assert rec["total_cost"] > 0

    def test_generate_negative_budget_returns_400(self):
        """POST /recommendations/generate with negative budget returns 400."""
        response = client.post("/recommendations/generate", json={"budget": -100.0})
        assert response.status_code == 400

    def test_latest_recommendations_returns_most_recent_run(self):
        """GET /recommendations/latest returns the most recent recommendation run."""
        mock_run = {
            "id": 1,
            "executed_at": "2026-01-01T10:00:00",
            "budget": 300.0,
            "total_allocated": 290.0,
            "portfolio_value": 5000.0,
        }
        mock_items = [
            {
                "ticker": "PG",
                "action": "BUY",
                "shares": 2,
                "price": 145.0,
                "total_cost": 290.0,
                "score": 10.0,
                "reasoning": "Good value",
                "priority": 1,
            }
        ]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_run
        mock_cursor.fetchall.return_value = mock_items
        mock_conn.close = MagicMock()

        with patch("app.services.recommendation_engine.get_connection", return_value=mock_conn):
            response = client.get("/recommendations/latest")

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data or "message" in data


# ===========================================================================
# 3. Dividend Data Synchronization Flow
# Tests: GET /dividends/summary, GET /dividends/by-ticker
# Requirements: 1.1, 1.2
# ===========================================================================

class TestDividendSyncFlow:
    """Integration tests for dividend data synchronization."""

    def test_dividend_summary_returns_monthly_and_yearly_totals(self):
        """GET /dividends/summary returns monthly_total, yearly_total, total_all_time."""
        mock_summary = {
            "monthly_total": 45.50,
            "yearly_total": 520.00,
            "total_all_time": 1200.00,
        }
        with patch("app.api.dividends_api.dividend_service.get_dividend_summary", return_value=mock_summary):
            response = client.get("/dividends/summary")

        assert response.status_code == 200
        data = response.json()
        assert "monthly_total" in data
        assert "yearly_total" in data
        assert "total_all_time" in data
        assert data["monthly_total"] >= 0
        assert data["yearly_total"] >= 0
        assert data["total_all_time"] >= 0

    def test_dividend_summary_yearly_gte_monthly(self):
        """Yearly total is always >= monthly total."""
        mock_summary = {"monthly_total": 45.50, "yearly_total": 520.00, "total_all_time": 1200.00}
        with patch("app.api.dividends_api.dividend_service.get_dividend_summary", return_value=mock_summary):
            response = client.get("/dividends/summary")

        data = response.json()
        assert data["yearly_total"] >= data["monthly_total"]

    def test_dividends_by_ticker_returns_per_stock_data(self):
        """GET /dividends/by-ticker returns dividend data for each stock."""
        mock_data = [
            {"ticker": "AVGO", "total_dividends": 120.00, "payment_count": 4,
             "last_payment_date": "2026-01-15", "avg_per_share": 5.25},
            {"ticker": "PG", "total_dividends": 85.00, "payment_count": 4,
             "last_payment_date": "2026-01-20", "avg_per_share": 0.94},
        ]
        with patch("app.api.dividends_api.dividend_service.get_dividends_by_ticker", return_value=mock_data):
            response = client.get("/dividends/by-ticker")

        assert response.status_code == 200
        data = response.json()
        assert "dividends" in data
        assert len(data["dividends"]) == 2
        for item in data["dividends"]:
            assert "ticker" in item
            assert "total_dividends" in item
            assert "payment_count" in item
            assert item["total_dividends"] >= 0

    def test_dividends_by_ticker_empty_when_no_payments(self):
        """GET /dividends/by-ticker returns empty list when no payments recorded."""
        with patch("app.api.dividends_api.dividend_service.get_dividends_by_ticker", return_value=[]):
            response = client.get("/dividends/by-ticker")

        assert response.status_code == 200
        assert response.json()["dividends"] == []

    def test_dividend_summary_zero_when_no_payments(self):
        """GET /dividends/summary returns zeros when no payments exist."""
        mock_summary = {"monthly_total": 0.0, "yearly_total": 0.0, "total_all_time": 0.0}
        with patch("app.api.dividends_api.dividend_service.get_dividend_summary", return_value=mock_summary):
            response = client.get("/dividends/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["monthly_total"] == 0.0
        assert data["yearly_total"] == 0.0


# ===========================================================================
# 4. Alert Creation and Triggering Flow
# Tests: POST /alerts, GET /alerts, PUT /alerts/{id}/toggle
# Requirements: 14.1
# ===========================================================================

class TestAlertFlow:
    """Integration tests for alert creation and triggering flow."""

    def test_create_alert_returns_alert_data(self):
        """POST /alerts creates an alert and returns it with an id."""
        with patch("app.api.alerts_api.alert_service.create_alert", return_value=SAMPLE_ALERT):
            response = client.post(
                "/alerts",
                json={"alert_type": "price", "ticker": "AVGO", "target_price": 950.0, "enabled": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["alert_type"] == "price"
        assert data["ticker"] == "AVGO"
        assert data["target_price"] == 950.0
        assert data["enabled"] is True

    def test_get_alerts_retrieves_created_alert(self):
        """GET /alerts returns the list of alerts including the created one."""
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[SAMPLE_ALERT]):
            response = client.get("/alerts")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["count"] == 1
        assert data["alerts"][0]["ticker"] == "AVGO"

    def test_get_alerts_returns_empty_list_when_none_configured(self):
        """GET /alerts returns empty list when no alerts are configured."""
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[]):
            response = client.get("/alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["alerts"] == []

    def test_toggle_alert_disables_enabled_alert(self):
        """PUT /alerts/{id}/toggle flips enabled=True to enabled=False."""
        disabled_alert = {**SAMPLE_ALERT, "enabled": False}
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[SAMPLE_ALERT]), \
             patch("app.api.alerts_api.alert_service.update_alert", return_value=disabled_alert):
            response = client.put("/alerts/1/toggle")

        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_toggle_alert_enables_disabled_alert(self):
        """PUT /alerts/{id}/toggle flips enabled=False to enabled=True."""
        disabled_alert = {**SAMPLE_ALERT, "enabled": False}
        enabled_alert = {**SAMPLE_ALERT, "enabled": True}
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[disabled_alert]), \
             patch("app.api.alerts_api.alert_service.update_alert", return_value=enabled_alert):
            response = client.put("/alerts/1/toggle")

        assert response.status_code == 200
        assert response.json()["enabled"] is True

    def test_alert_creation_validates_price_alert_requires_ticker(self):
        """POST /alerts with price type but no ticker returns 400."""
        response = client.post("/alerts", json={"alert_type": "price", "target_price": 100.0})
        assert response.status_code == 400

    def test_alert_creation_validates_price_alert_requires_target_price(self):
        """POST /alerts with price type but no target_price returns 400."""
        response = client.post("/alerts", json={"alert_type": "price", "ticker": "AVGO"})
        assert response.status_code == 400

    def test_full_alert_lifecycle_create_retrieve_toggle(self):
        """Full lifecycle: create alert → retrieve it → toggle it."""
        # Step 1: Create
        with patch("app.api.alerts_api.alert_service.create_alert", return_value=SAMPLE_ALERT):
            create_resp = client.post(
                "/alerts",
                json={"alert_type": "price", "ticker": "AVGO", "target_price": 950.0},
            )
        assert create_resp.status_code == 200
        alert_id = create_resp.json()["id"]

        # Step 2: Retrieve
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[SAMPLE_ALERT]):
            get_resp = client.get("/alerts")
        assert get_resp.status_code == 200
        assert get_resp.json()["count"] == 1

        # Step 3: Toggle
        toggled = {**SAMPLE_ALERT, "enabled": False}
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[SAMPLE_ALERT]), \
             patch("app.api.alerts_api.alert_service.update_alert", return_value=toggled):
            toggle_resp = client.put(f"/alerts/{alert_id}/toggle")
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["enabled"] is False


# ===========================================================================
# 5. Watchlist Operations Flow
# Tests: POST /watchlist, GET /watchlist, DELETE /watchlist/{ticker}
# Requirements: 15.1
# ===========================================================================

class TestWatchlistFlow:
    """Integration tests for watchlist operations flow."""

    def test_add_ticker_to_watchlist(self):
        """POST /watchlist adds a ticker and returns the watchlist item."""
        with patch("app.api.watchlist_api.watchlist_service.add_to_watchlist", return_value=SAMPLE_WATCHLIST_ITEM):
            response = client.post("/watchlist", json={"ticker": "MSFT"})

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert "current_price" in data

    def test_get_watchlist_returns_items_with_metrics(self):
        """GET /watchlist returns items enriched with market metrics."""
        with patch("app.api.watchlist_api.watchlist_service.get_watchlist_metrics", return_value=[SAMPLE_WATCHLIST_ITEM]):
            response = client.get("/watchlist")

        assert response.status_code == 200
        data = response.json()
        assert "watchlist" in data
        assert data["count"] == 1
        item = data["watchlist"][0]
        assert "ticker" in item
        assert "current_price" in item
        assert "dividend_yield" in item
        assert "pe_ratio" in item

    def test_get_watchlist_returns_empty_when_none_added(self):
        """GET /watchlist returns empty list when no tickers added."""
        with patch("app.api.watchlist_api.watchlist_service.get_watchlist_metrics", return_value=[]):
            response = client.get("/watchlist")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["watchlist"] == []

    def test_remove_ticker_from_watchlist(self):
        """DELETE /watchlist/{ticker} removes the ticker successfully."""
        with patch("app.api.watchlist_api.watchlist_service.remove_from_watchlist", return_value=True):
            response = client.delete("/watchlist/MSFT")

        assert response.status_code == 200
        data = response.json()
        assert "MSFT" in data["ticker"]

    def test_remove_nonexistent_ticker_returns_404(self):
        """DELETE /watchlist/{ticker} returns 404 when ticker not in watchlist."""
        with patch("app.api.watchlist_api.watchlist_service.remove_from_watchlist", return_value=False):
            response = client.delete("/watchlist/FAKE")

        assert response.status_code == 404

    def test_add_empty_ticker_returns_400(self):
        """POST /watchlist with empty ticker returns 400."""
        response = client.post("/watchlist", json={"ticker": ""})
        assert response.status_code == 400

    def test_get_prioritized_watchlist(self):
        """GET /watchlist/prioritized returns items sorted by score."""
        items = [
            {**SAMPLE_WATCHLIST_ITEM, "ticker": "MSFT", "score": 85},
            {**SAMPLE_WATCHLIST_ITEM, "ticker": "AAPL", "score": 70},
        ]
        with patch("app.api.watchlist_api.watchlist_service.get_prioritized_watchlist", return_value=items):
            response = client.get("/watchlist/prioritized")

        assert response.status_code == 200
        data = response.json()
        assert "watchlist" in data
        assert data["count"] == 2

    def test_full_watchlist_lifecycle_add_retrieve_remove(self):
        """Full lifecycle: add ticker → retrieve list → remove ticker."""
        # Step 1: Add
        with patch("app.api.watchlist_api.watchlist_service.add_to_watchlist", return_value=SAMPLE_WATCHLIST_ITEM):
            add_resp = client.post("/watchlist", json={"ticker": "MSFT"})
        assert add_resp.status_code == 200

        # Step 2: Retrieve
        with patch("app.api.watchlist_api.watchlist_service.get_watchlist_metrics", return_value=[SAMPLE_WATCHLIST_ITEM]):
            get_resp = client.get("/watchlist")
        assert get_resp.status_code == 200
        assert get_resp.json()["count"] == 1

        # Step 3: Remove
        with patch("app.api.watchlist_api.watchlist_service.remove_from_watchlist", return_value=True):
            del_resp = client.delete("/watchlist/MSFT")
        assert del_resp.status_code == 200


# ===========================================================================
# 6. Error Handling Scenarios
# Requirements: 1.4
# ===========================================================================

class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_portfolio_service_unavailable_returns_500(self):
        """Backend service failure returns 500 (simulates service unavailable)."""
        with patch("app.services.portfolio_service.load_portfolio_from_db", side_effect=Exception("DB unavailable")), \
             patch("app.services.portfolio_service.get_prices", return_value=MOCK_PRICES):
            response = client.get("/portfolio/snapshot")

        assert response.status_code == 500

    def test_dividend_service_unavailable_returns_500(self):
        """Dividend service failure returns 500."""
        with patch("app.api.dividends_api.dividend_service.get_dividend_summary", side_effect=Exception("Service down")):
            response = client.get("/dividends/summary")

        assert response.status_code == 500

    def test_alert_service_unavailable_returns_500(self):
        """Alert service failure returns 500."""
        with patch("app.api.alerts_api.alert_service.get_user_alerts", side_effect=Exception("DB error")):
            response = client.get("/alerts")

        assert response.status_code == 500

    def test_watchlist_service_unavailable_returns_500(self):
        """Watchlist service failure returns 500."""
        with patch("app.api.watchlist_api.watchlist_service.get_watchlist_metrics", side_effect=Exception("Service error")):
            response = client.get("/watchlist")

        assert response.status_code == 500

    def test_invalid_alert_type_returns_400(self):
        """POST /alerts with invalid alert_type returns 400 (invalid input validation)."""
        response = client.post(
            "/alerts",
            json={"alert_type": "invalid_type", "ticker": "AVGO", "target_price": 100.0},
        )
        assert response.status_code == 400

    def test_toggle_nonexistent_alert_returns_404(self):
        """PUT /alerts/{id}/toggle for non-existent alert returns 404."""
        with patch("app.api.alerts_api.alert_service.get_user_alerts", return_value=[]):
            response = client.put("/alerts/9999/toggle")

        assert response.status_code == 404

    def test_recommendation_engine_failure_returns_500(self):
        """Recommendation engine failure returns 500."""
        with patch("app.services.recommendation_engine.RecommendationEngine.generate_buy_recommendations",
                   side_effect=Exception("Engine error")):
            response = client.post("/recommendations/generate", json={"budget": 300.0})

        assert response.status_code == 500
