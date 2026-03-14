"""
Unit tests for alert API endpoints.
Tests Requirements 14.7, 14.8, 14.9, 14.10
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_ALERT = {
    "id": 1,
    "user_id": 1,
    "alert_type": "price",
    "ticker": "AAPL",
    "target_price": 150.0,
    "enabled": True,
    "last_triggered": None,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}

SAMPLE_HISTORY = [
    {
        "id": 1,
        "user_id": 1,
        "alert_id": 1,
        "alert_type": "price",
        "ticker": "AAPL",
        "message": "AAPL reached target price $150.00",
        "sent_at": "2026-01-02T10:00:00",
        "delivered": True,
        "read": False,
    }
]


# ---------------------------------------------------------------------------
# POST /alerts — create alert
# ---------------------------------------------------------------------------

class TestCreateAlert:
    def test_create_price_alert_success(self):
        """Creating a valid price alert returns 200 with alert data."""
        with patch(
            "app.api.alerts_api.alert_service.create_alert",
            return_value=SAMPLE_ALERT,
        ):
            response = client.post(
                "/alerts",
                json={
                    "alert_type": "price",
                    "ticker": "AAPL",
                    "target_price": 150.0,
                    "enabled": True,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["alert_type"] == "price"
        assert data["ticker"] == "AAPL"

    def test_create_rebalancing_alert_no_ticker_required(self):
        """Rebalancing alerts do not require a ticker."""
        rebalancing_alert = {**SAMPLE_ALERT, "alert_type": "rebalancing",
                             "ticker": None, "target_price": None}
        with patch(
            "app.api.alerts_api.alert_service.create_alert",
            return_value=rebalancing_alert,
        ):
            response = client.post(
                "/alerts",
                json={"alert_type": "rebalancing"},
            )
        assert response.status_code == 200

    def test_create_alert_invalid_type_returns_400(self):
        """Unknown alert_type returns 400."""
        response = client.post(
            "/alerts",
            json={"alert_type": "unknown_type"},
        )
        assert response.status_code == 400
        assert "alert_type" in response.json()["detail"].lower()

    def test_create_price_alert_missing_ticker_returns_400(self):
        """Price alert without ticker returns 400."""
        response = client.post(
            "/alerts",
            json={"alert_type": "price", "target_price": 100.0},
        )
        assert response.status_code == 400

    def test_create_price_alert_missing_target_price_returns_400(self):
        """Price alert without target_price returns 400."""
        response = client.post(
            "/alerts",
            json={"alert_type": "price", "ticker": "AAPL"},
        )
        assert response.status_code == 400

    def test_create_price_alert_zero_target_price_returns_400(self):
        """Price alert with target_price=0 returns 400."""
        response = client.post(
            "/alerts",
            json={"alert_type": "price", "ticker": "AAPL", "target_price": 0},
        )
        assert response.status_code == 400

    def test_create_dividend_alert_missing_ticker_returns_400(self):
        """Dividend alert without ticker returns 400."""
        response = client.post(
            "/alerts",
            json={"alert_type": "dividend"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /alerts — list alerts
# ---------------------------------------------------------------------------

class TestGetAlerts:
    def test_get_alerts_returns_list(self):
        """GET /alerts returns alerts list with count."""
        with patch(
            "app.api.alerts_api.alert_service.get_user_alerts",
            return_value=[SAMPLE_ALERT],
        ):
            response = client.get("/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "count" in data
        assert data["count"] == 1

    def test_get_alerts_empty_list(self):
        """GET /alerts returns empty list when no alerts configured."""
        with patch(
            "app.api.alerts_api.alert_service.get_user_alerts",
            return_value=[],
        ):
            response = client.get("/alerts")
        assert response.status_code == 200
        assert response.json()["count"] == 0


# ---------------------------------------------------------------------------
# GET /alerts/history — notification history
# ---------------------------------------------------------------------------

class TestNotificationHistory:
    def test_get_history_returns_paginated_results(self):
        """GET /alerts/history returns history with pagination metadata."""
        with patch(
            "app.api.alerts_api.alert_service.get_notification_history",
            return_value=SAMPLE_HISTORY,
        ):
            response = client.get("/alerts/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "count" in data
        assert "limit" in data
        assert "offset" in data

    def test_get_history_pagination_params(self):
        """Limit and offset query params are respected."""
        many = [dict(SAMPLE_HISTORY[0], id=i) for i in range(10)]
        with patch(
            "app.api.alerts_api.alert_service.get_notification_history",
            return_value=many,
        ):
            response = client.get("/alerts/history?limit=5&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 2

    def test_get_history_invalid_limit_returns_422(self):
        """limit=0 is rejected with 422."""
        response = client.get("/alerts/history?limit=0")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /alerts/{alert_id} — get specific alert
# ---------------------------------------------------------------------------

class TestGetAlert:
    def test_get_existing_alert(self):
        """GET /alerts/1 returns the alert when it exists."""
        with patch(
            "app.api.alerts_api.alert_service.get_user_alerts",
            return_value=[SAMPLE_ALERT],
        ):
            response = client.get("/alerts/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_nonexistent_alert_returns_404(self):
        """GET /alerts/999 returns 404 when alert not found."""
        with patch(
            "app.api.alerts_api.alert_service.get_user_alerts",
            return_value=[],
        ):
            response = client.get("/alerts/999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /alerts/{alert_id} — update alert
# ---------------------------------------------------------------------------

class TestUpdateAlert:
    def test_update_alert_success(self):
        """PUT /alerts/1 updates and returns the alert."""
        updated = {**SAMPLE_ALERT, "target_price": 200.0}
        with patch(
            "app.api.alerts_api.alert_service.update_alert",
            return_value=updated,
        ):
            response = client.put(
                "/alerts/1",
                json={"target_price": 200.0},
            )
        assert response.status_code == 200
        assert response.json()["target_price"] == 200.0

    def test_update_alert_no_fields_returns_400(self):
        """PUT /alerts/1 with empty body returns 400."""
        response = client.put("/alerts/1", json={})
        assert response.status_code == 400

    def test_update_nonexistent_alert_returns_404(self):
        """PUT /alerts/999 returns 404 when alert not found."""
        with patch(
            "app.api.alerts_api.alert_service.update_alert",
            return_value=None,
        ):
            response = client.put(
                "/alerts/999",
                json={"enabled": False},
            )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /alerts/{alert_id} — delete alert
# ---------------------------------------------------------------------------

class TestDeleteAlert:
    def test_delete_existing_alert(self):
        """DELETE /alerts/1 returns success message."""
        with patch(
            "app.api.alerts_api.alert_service.delete_alert",
            return_value=True,
        ):
            response = client.delete("/alerts/1")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_delete_nonexistent_alert_returns_404(self):
        """DELETE /alerts/999 returns 404 when alert not found."""
        with patch(
            "app.api.alerts_api.alert_service.delete_alert",
            return_value=False,
        ):
            response = client.delete("/alerts/999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /alerts/{alert_id}/toggle — toggle alert
# ---------------------------------------------------------------------------

class TestToggleAlert:
    def test_toggle_enabled_to_disabled(self):
        """Toggle flips enabled=True to enabled=False."""
        disabled = {**SAMPLE_ALERT, "enabled": False}
        with patch(
            "app.api.alerts_api.alert_service.get_user_alerts",
            return_value=[SAMPLE_ALERT],
        ), patch(
            "app.api.alerts_api.alert_service.update_alert",
            return_value=disabled,
        ):
            response = client.put("/alerts/1/toggle")
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_toggle_nonexistent_alert_returns_404(self):
        """Toggle on missing alert returns 404."""
        with patch(
            "app.api.alerts_api.alert_service.get_user_alerts",
            return_value=[],
        ):
            response = client.put("/alerts/999/toggle")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /alerts/evaluate — manual evaluation
# ---------------------------------------------------------------------------

class TestEvaluateAlerts:
    def test_evaluate_returns_summary(self):
        """POST /alerts/evaluate returns evaluation summary."""
        summary = {"evaluated": 3, "triggered": 1, "errors": 0}
        with patch(
            "app.api.alerts_api.alert_service.evaluate_alerts",
            return_value=summary,
        ):
            response = client.post("/alerts/evaluate")
        assert response.status_code == 200
        data = response.json()
        assert "evaluated" in data or "triggered" in data or data == summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
