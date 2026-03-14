"""
Property-based tests for recommendation engine.
Tests universal correctness properties using Hypothesis.
"""
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.recommendation_engine import RecommendationEngine
from app.database import get_connection, init_database
from app.tests.conftest import get_cached_market_data


# Property 2: Budget Constraint Adherence
# Validates: Requirements 1.3, 4.2, 4.5, 12.4, 12.7
@given(budget=st.floats(min_value=50.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_budget_constraint_adherence(budget):
    """
    Property: The total cost of all recommendations SHALL NEVER exceed the given budget.
    """
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    
    test_holdings = [
        ('AVGO', 1.5, 850.00, 900.00),
        ('PG', 5.0, 140.00, 145.00),
        ('NEE', 8.0, 65.00, 70.00),
    ]
    
    for ticker, shares, avg_price, current_price in test_holdings:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES (?, ?, ?, ?)
        """, (ticker, shares, avg_price, current_price))
    
    conn.commit()
    conn.close()
    
    # Use preloaded market data from cache
    cache = get_cached_market_data()
    mock_prices = {k: v for k, v in cache['prices'].items() if k in ['AVGO', 'PG', 'NEE']}
    mock_dividends = {k: v for k, v in cache['dividends'].items() if k in ['AVGO', 'PG', 'NEE']}
    mock_valuation = {k: v for k, v in cache['valuations'].items() if k in ['AVGO', 'PG', 'NEE']}
    
    # Calculate scores based on cached data
    mock_scores = {}
    for ticker in ['AVGO', 'PG', 'NEE']:
        score = 0
        div_yield = mock_dividends.get(ticker, {}).get('yield', 0)
        payout = mock_dividends.get(ticker, {}).get('payout', 0)
        pe = mock_valuation.get(ticker, 0)
        
        score += div_yield * 40
        if payout and payout < 0.65:
            score += 20
        if pe and pe < 20:
            score += 20
        mock_scores[ticker] = score
    
    with patch('app.services.recommendation_engine.get_prices', return_value=mock_prices), \
         patch('app.services.dividend_service.DividendService.get_dividends', return_value=mock_dividends), \
         patch('app.services.valuation_service.ValuationService.get_valuation', return_value=mock_valuation), \
         patch('app.services.scoring_service.ScoringService.compute_score', return_value=mock_scores):
        
        engine = RecommendationEngine()
        result = engine.generate_buy_recommendations(budget)
    
    total_allocated = result.get('total_allocated', 0)
    recommendations = result.get('recommendations', [])
    
    assert total_allocated <= budget, \
        f"Budget constraint violated: allocated {total_allocated} > budget {budget}"
    
    sum_of_costs = sum(rec['total_cost'] for rec in recommendations)
    assert abs(sum_of_costs - total_allocated) < 0.01, \
        f"Sum of costs {sum_of_costs} != total allocated {total_allocated}"
    
    running_total = 0
    for rec in recommendations:
        cost = rec['total_cost']
        assert running_total + cost <= budget + 0.01, \
            f"Recommendation {rec['ticker']} cost {cost} exceeds remaining budget"
        running_total += cost
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM recommendation_runs")
    cursor.execute("DELETE FROM recommendation_items")
    conn.commit()
    conn.close()


# Property 9: Recommendation Structure Completeness
# Validates: Requirements 4.4, 4.7
@given(budget=st.floats(min_value=100.0, max_value=5000.0, allow_nan=False, allow_infinity=False))
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_recommendation_structure_completeness(budget):
    """
    Property: Every recommendation MUST contain all required fields with valid values.
    """
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    
    test_holdings = [
        ('JNJ', 3.0, 160.00, 165.00),
        ('UPS', 4.0, 180.00, 185.00),
    ]
    
    for ticker, shares, avg_price, current_price in test_holdings:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES (?, ?, ?, ?)
        """, (ticker, shares, avg_price, current_price))
    
    conn.commit()
    conn.close()
    
    # Use preloaded market data from cache
    cache = get_cached_market_data()
    mock_prices = {k: v for k, v in cache['prices'].items() if k in ['JNJ', 'UPS']}
    mock_dividends = {k: v for k, v in cache['dividends'].items() if k in ['JNJ', 'UPS']}
    mock_valuation = {k: v for k, v in cache['valuations'].items() if k in ['JNJ', 'UPS']}
    
    # Calculate scores
    mock_scores = {}
    for ticker in ['JNJ', 'UPS']:
        score = 0
        div_yield = mock_dividends.get(ticker, {}).get('yield', 0)
        payout = mock_dividends.get(ticker, {}).get('payout', 0)
        pe = mock_valuation.get(ticker, 0)
        
        score += div_yield * 40
        if payout and payout < 0.65:
            score += 20
        if pe and pe < 20:
            score += 20
        mock_scores[ticker] = score
    
    with patch('app.services.recommendation_engine.get_prices', return_value=mock_prices), \
         patch('app.services.dividend_service.DividendService.get_dividends', return_value=mock_dividends), \
         patch('app.services.valuation_service.ValuationService.get_valuation', return_value=mock_valuation), \
         patch('app.services.scoring_service.ScoringService.compute_score', return_value=mock_scores):
        
        engine = RecommendationEngine()
        result = engine.generate_buy_recommendations(budget)
    
    recommendations = result.get('recommendations', [])
    required_fields = ['ticker', 'action', 'shares', 'price', 'total_cost', 'score', 'reasoning', 'priority']
    
    for rec in recommendations:
        for field in required_fields:
            assert field in rec, f"Missing required field '{field}' in recommendation"
        
        assert isinstance(rec['ticker'], str) and len(rec['ticker']) > 0
        assert rec['shares'] > 0
        assert rec['price'] > 0
        assert rec['total_cost'] > 0
        
        expected_cost = rec['shares'] * rec['price']
        assert abs(rec['total_cost'] - expected_cost) < 0.01
        
        assert isinstance(rec['reasoning'], str) and len(rec['reasoning']) > 0
        assert isinstance(rec['score'], (int, float))
        assert isinstance(rec['priority'], int) and rec['priority'] > 0
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM recommendation_runs")
    cursor.execute("DELETE FROM recommendation_items")
    conn.commit()
    conn.close()


# Property 10: Recommendation Ordering
# Validates: Requirements 4.8
@given(budget=st.floats(min_value=200.0, max_value=5000.0, allow_nan=False, allow_infinity=False))
@hypothesis_settings(max_examples=15, deadline=None)
def test_property_recommendation_ordering(budget):
    """
    Property: Recommendations MUST be ordered by priority, with priority 1 being highest.
    """
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    
    test_holdings = [
        ('CVX', 6.0, 150.00, 155.00),
        ('XOM', 7.0, 110.00, 115.00),
        ('ABBV', 4.0, 170.00, 175.00),
    ]
    
    for ticker, shares, avg_price, current_price in test_holdings:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price)
            VALUES (?, ?, ?, ?)
        """, (ticker, shares, avg_price, current_price))
    
    conn.commit()
    conn.close()
    
    # Use preloaded market data from cache
    cache = get_cached_market_data()
    mock_prices = {k: v for k, v in cache['prices'].items() if k in ['CVX', 'XOM', 'ABBV']}
    mock_dividends = {k: v for k, v in cache['dividends'].items() if k in ['CVX', 'XOM', 'ABBV']}
    mock_valuation = {k: v for k, v in cache['valuations'].items() if k in ['CVX', 'XOM', 'ABBV']}
    
    # Calculate scores
    mock_scores = {}
    for ticker in ['CVX', 'XOM', 'ABBV']:
        score = 0
        div_yield = mock_dividends.get(ticker, {}).get('yield', 0)
        payout = mock_dividends.get(ticker, {}).get('payout', 0)
        pe = mock_valuation.get(ticker, 0)
        
        score += div_yield * 40
        if payout and payout < 0.65:
            score += 20
        if pe and pe < 20:
            score += 20
        mock_scores[ticker] = score
    
    with patch('app.services.recommendation_engine.get_prices', return_value=mock_prices), \
         patch('app.services.dividend_service.DividendService.get_dividends', return_value=mock_dividends), \
         patch('app.services.valuation_service.ValuationService.get_valuation', return_value=mock_valuation), \
         patch('app.services.scoring_service.ScoringService.compute_score', return_value=mock_scores):
        
        engine = RecommendationEngine()
        result = engine.generate_buy_recommendations(budget)
    
    recommendations = result.get('recommendations', [])
    
    if len(recommendations) == 0:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio")
        cursor.execute("DELETE FROM recommendation_runs")
        cursor.execute("DELETE FROM recommendation_items")
        conn.commit()
        conn.close()
        return
    
    priorities = [rec['priority'] for rec in recommendations]
    expected_priorities = list(range(1, len(recommendations) + 1))
    assert priorities == expected_priorities
    
    for i in range(len(recommendations) - 1):
        current_priority = recommendations[i]['priority']
        next_priority = recommendations[i + 1]['priority']
        assert current_priority < next_priority
    
    scores = [rec['score'] for rec in recommendations]
    if len(scores) > 1:
        max_score = max(scores)
        first_score = scores[0]
        assert first_score >= max_score * 0.5
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM recommendation_runs")
    cursor.execute("DELETE FROM recommendation_items")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
    
    print("Running Property 2: Budget Constraint Adherence...")
    test_property_budget_constraint_adherence()
    print("✓ Property 2 passed!")
    
    print("\nRunning Property 9: Recommendation Structure Completeness...")
    test_property_recommendation_structure_completeness()
    print("✓ Property 9 passed!")
    
    print("\nRunning Property 10: Recommendation Ordering...")
    test_property_recommendation_ordering()
    print("✓ Property 10 passed!")

