"""
Recommendation API endpoints for InversionAPP.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from ..services.recommendation_engine import RecommendationEngine
from ..services.new_ticker_discovery_service import NewTickerDiscoveryService
from ..services.sell_recommendation_service import SellRecommendationService
from ..services.scoring_service import ScoringService
from ..services.dividend_service import DividendService
from ..services.valuation_service import ValuationService
from ..services.volatility_service import VolatilityService
from ..services.market_data_service import get_prices
from ..services.watchlist_service import (
    WatchlistService,
    WATCHLIST_PRIORITY_BONUS,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendation_engine = RecommendationEngine()
new_ticker_service = NewTickerDiscoveryService()
sell_recommendation_service = SellRecommendationService()
watchlist_service = WatchlistService()

DEFAULT_USER_ID = 1


class GenerateRecommendationsRequest(BaseModel):
    budget: float


@router.post("/generate")
async def generate_recommendations(request: GenerateRecommendationsRequest):
    """
    Generate buy recommendations with budget parameter.
    
    Request body:
        - budget: Available capital for investment
    
    Returns:
        - run_id: Unique ID for this recommendation run
        - recommendations: List of buy recommendations sorted by priority
        - budget: Total budget provided
        - total_allocated: Amount allocated across recommendations
        - remaining: Unallocated budget
        - executed_at: Timestamp of generation
    """
    try:
        if request.budget < 0:
            raise HTTPException(status_code=400, detail="Budget must be positive")
        
        result = recommendation_engine.generate_buy_recommendations(request.budget)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/latest")
async def get_latest_recommendations():
    """
    Get the most recent recommendation run.
    
    Returns:
        - run_id: Unique ID for the recommendation run
        - executed_at: Timestamp of generation
        - budget: Budget used
        - total_allocated: Amount allocated
        - portfolio_value: Portfolio value at time of generation
        - recommendations: List of recommendations
    """
    try:
        result = recommendation_engine.get_latest_recommendations()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching latest recommendations: {str(e)}")


@router.get("/history")
async def get_recommendation_history(
    limit: int = Query(10, description="Number of past runs to retrieve", ge=1, le=100)
):
    """
    Get past recommendation runs.
    
    Query parameters:
        - limit: Number of runs to retrieve (1-100, default 10)
    
    Returns list of past recommendation runs with summary data.
    """
    try:
        history = recommendation_engine.get_recommendation_history(limit)
        return {"runs": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendation history: {str(e)}")


class NewTickerRecommendationsRequest(BaseModel):
    min_market_cap: Optional[float] = 10_000_000_000
    min_dividend_yield: Optional[float] = 0.02
    max_pe_ratio: Optional[float] = 25
    max_payout_ratio: Optional[float] = 0.70
    limit: Optional[int] = 5


@router.post("/new-tickers")
async def recommend_new_tickers(request: NewTickerRecommendationsRequest):
    """
    Analyze and recommend new tickers to add to portfolio.
    
    Implements Requirements 11.4, 11.5, 11.8:
    - Include sector/industry classification in response
    - Include diversification explanation in response
    - Include allocation impact in response
    
    Request body:
        - min_market_cap: Minimum market cap (default $10B)
        - min_dividend_yield: Minimum dividend yield (default 2%)
        - max_pe_ratio: Maximum P/E ratio (default 25)
        - max_payout_ratio: Maximum payout ratio (default 70%)
        - limit: Maximum number of recommendations (default 5)
    
    Returns:
        - recommendations: List of new ticker recommendations with:
            - ticker: Stock symbol
            - score: Composite investment score
            - sector: Sector classification (Requirement 11.4)
            - industry: Industry classification (Requirement 11.4)
            - diversification_score: Diversification benefit score
            - diversification_explanation: Why this ticker improves diversification (Requirement 11.5)
            - allocation_impact: Expected allocation percentage if added (Requirement 11.8)
            - current_price: Current stock price
            - dividend_yield: Annual dividend yield
            - pe_ratio: Price-to-earnings ratio
            - market_cap: Market capitalization
    """
    try:
        # Discover candidate tickers
        candidates = new_ticker_service.discover_candidates(
            min_market_cap=request.min_market_cap,
            min_dividend_yield=request.min_dividend_yield,
            max_pe_ratio=request.max_pe_ratio,
            max_payout_ratio=request.max_payout_ratio,
            limit=request.limit * 3  # Get more candidates for scoring
        )
        
        if not candidates:
            return {
                "recommendations": [],
                "message": "No candidates found matching the screening criteria"
            }
        
        # Get market data for candidates
        prices = get_prices(candidates)
        
        # Initialize services
        dividend_service = DividendService()
        valuation_service = ValuationService()
        volatility_service = VolatilityService()
        scoring_service = ScoringService()
        
        # Get financial metrics
        dividends = dividend_service.get_dividends(candidates)
        valuations = valuation_service.get_valuation(candidates)
        volatilities = volatility_service.compute_volatility(prices)
        
        # Calculate base scores
        base_scores = scoring_service.compute_score(
            prices, dividends, valuations, volatilities
        )
        
        # Get current portfolio value for allocation impact calculation
        from ..database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(shares * current_price) as total_value
            FROM portfolio
        """)
        portfolio_value = cursor.fetchone()['total_value'] or 0
        conn.close()
        
        # Evaluate diversification and build recommendations
        import yfinance as yf
        recommendations = []
        for ticker in candidates:
            if ticker not in base_scores:
                continue

            # Get diversification analysis (Requirements 11.4, 11.5)
            diversification = (
                new_ticker_service.evaluate_diversification_benefit(ticker)
            )

            # Get market cap
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                market_cap = info.get('marketCap', 0)
            except Exception:
                market_cap = 0

            # Calculate final score with diversification bonus
            final_score = (
                base_scores[ticker] +
                diversification['diversification_score']
            )

            # Calculate allocation impact (Requirement 11.8)
            # Assume a $300 purchase (typical monthly budget)
            assumed_purchase = 300
            new_portfolio_value = portfolio_value + assumed_purchase
            if new_portfolio_value > 0:
                allocation_impact = (
                    (assumed_purchase / new_portfolio_value) * 100
                )
            else:
                allocation_impact = 0

            recommendations.append({
                "ticker": ticker,
                "score": round(final_score, 2),
                "sector": diversification['sector'],
                "industry": diversification['industry'],
                "diversification_score": (
                    diversification['diversification_score']
                ),
                "diversification_explanation": (
                    diversification['explanation']
                ),
                "allocation_impact": round(allocation_impact, 2),
                "current_price": round(prices.get(ticker, 0), 2),
                "dividend_yield": round(
                    dividends.get(ticker, {}).get('yield', 0) * 100, 2
                ),
                "pe_ratio": round(valuations.get(ticker, 0), 2),
                "market_cap": market_cap
            })
        
        # Apply watchlist priority bonus (req 15.7)
        try:
            watchlist_items = watchlist_service.get_watchlist(DEFAULT_USER_ID)
            watchlist_tickers = {item["ticker"] for item in watchlist_items}
        except Exception:
            watchlist_tickers = set()

        for rec in recommendations:
            if rec["ticker"] in watchlist_tickers:
                rec["score"] = round(
                    rec["score"] + WATCHLIST_PRIORITY_BONUS, 2
                )
                rec["in_watchlist"] = True
            else:
                rec["in_watchlist"] = False

        # Sort by final score descending
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top recommendations
        return {
            "recommendations": recommendations[:request.limit],
            "total_candidates_screened": len(candidates),
            "portfolio_value": round(portfolio_value, 2)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating new ticker recommendations: {str(e)}"
        )


class HoldingInput(BaseModel):
    ticker: str
    shares: float
    avg_price: float


class SellRecommendationsRequest(BaseModel):
    holdings: Optional[List[HoldingInput]] = None


@router.post("/sell")
async def generate_sell_recommendations(
    request: SellRecommendationsRequest = SellRecommendationsRequest(),
):
    """
    Generate sell recommendations for current portfolio holdings.

    Implements Requirements 13.6, 13.7, 13.9:
    - Detailed reasoning for each sell recommendation (13.6)
    - Tax implications for each sell recommendation (13.7)
    - Current gain/loss and holding period for each position (13.9)

    Request body (optional):
        - holdings: List of holdings to evaluate. If omitted, the current
          portfolio is loaded from the database.

    Returns:
        - recommendations: List of sell recommendations sorted by priority,
          each containing:
            - ticker: Stock symbol
            - shares_to_sell: Recommended number of shares to sell
            - current_price: Current market price per share
            - total_proceeds: Expected proceeds from the sale
            - reason: Sell reason (OVERVALUED / FUNDAMENTAL_DETERIORATION /
              REBALANCING)
            - reasoning_detail: Detailed explanation of the recommendation
              (Requirement 13.6)
            - tax_implications: Estimated capital gains tax in USD
              (Requirement 13.7)
            - holding_period_days: Number of days the position has been held
              (Requirement 13.9)
            - gain_loss: Expected gain or loss from the sale (Requirement 13.9)
            - priority: Urgency ranking (1 = highest)
        - count: Total number of sell recommendations
    """
    try:
        holdings = None
        if request.holdings:
            holdings = [h.model_dump() for h in request.holdings]

        candidates = sell_recommendation_service.identify_sell_candidates(
            holdings=holdings
        )

        return {
            "recommendations": candidates,
            "count": len(candidates),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating sell recommendations: {str(e)}",
        )
