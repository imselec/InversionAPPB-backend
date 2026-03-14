"""
Unit tests for new ticker recommendation API endpoint.
Tests Requirements 11.4, 11.5, 11.8
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_new_ticker_endpoint_returns_recommendations():
    """
    Test that POST /recommendations/new-tickers returns recommendations
    with required fields.
    """
    response = client.post(
        "/recommendations/new-tickers",
        json={
            "min_market_cap": 10000000000,
            "min_dividend_yield": 0.02,
            "max_pe_ratio": 25,
            "max_payout_ratio": 0.70,
            "limit": 3
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "recommendations" in data
    assert "total_candidates_screened" in data
    assert "portfolio_value" in data

    # If recommendations exist, verify structure
    if data["recommendations"]:
        rec = data["recommendations"][0]

        # Requirement 11.4: sector/industry classification
        assert "sector" in rec
        assert "industry" in rec

        # Requirement 11.5: diversification explanation
        assert "diversification_explanation" in rec
        assert isinstance(rec["diversification_explanation"], str)
        assert len(rec["diversification_explanation"]) > 0

        # Requirement 11.8: allocation impact
        assert "allocation_impact" in rec
        assert isinstance(rec["allocation_impact"], (int, float))
        assert rec["allocation_impact"] >= 0

        # Other required fields
        assert "ticker" in rec
        assert "score" in rec
        assert "current_price" in rec
        assert "dividend_yield" in rec
        assert "pe_ratio" in rec
        assert "market_cap" in rec


def test_new_ticker_endpoint_with_defaults():
    """
    Test that endpoint works with default parameters.
    """
    response = client.post("/recommendations/new-tickers", json={})

    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data


def test_new_ticker_recommendations_sorted_by_score():
    """
    Test that recommendations are sorted by score in descending order.
    """
    response = client.post(
        "/recommendations/new-tickers",
        json={"limit": 5}
    )

    assert response.status_code == 200
    data = response.json()

    if len(data["recommendations"]) > 1:
        scores = [rec["score"] for rec in data["recommendations"]]
        assert scores == sorted(scores, reverse=True)


def test_new_ticker_limit_parameter():
    """
    Test that limit parameter controls number of recommendations.
    """
    limit = 2
    response = client.post(
        "/recommendations/new-tickers",
        json={"limit": limit}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) <= limit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
