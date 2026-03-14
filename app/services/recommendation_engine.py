from datetime import datetime
from typing import Dict, List
from .market_data_service import get_prices
from .dividend_service import DividendService
from .valuation_service import ValuationService
from .volatility_service import VolatilityService
from .scoring_service import ScoringService
from .portfolio_optimizer import PortfolioOptimizer
from ..database import get_connection


class RecommendationEngine:

    def __init__(self):
        self.dividend = DividendService()
        self.valuation = ValuationService()
        self.volatility = VolatilityService()
        self.scoring = ScoringService()
        self.optimizer = PortfolioOptimizer()

    def generate_recommendations(self, tickers, capital):
        prices = get_prices(tickers)
        dividends = self.dividend.get_dividends(tickers)
        valuation = self.valuation.get_valuation(tickers)
        volatility = self.volatility.compute_volatility(prices)
        scores = self.scoring.compute_score(
            prices,
            dividends,
            valuation,
            volatility
        )
        portfolio = self.optimizer.allocate(scores, capital)
        return portfolio

    def generate_buy_recommendations(self, budget: float) -> Dict:
        """
        Generate buy recommendations respecting budget constraint.
        
        Args:
            budget: Available capital for investment
            
        Returns:
            Dictionary with recommendations and metadata
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current portfolio tickers
        cursor.execute("SELECT ticker FROM portfolio")
        rows = cursor.fetchall()
        tickers = [row['ticker'] for row in rows]
        
        if not tickers:
            conn.close()
            return {
                "recommendations": [],
                "budget": budget,
                "total_allocated": 0,
                "message": "No portfolio holdings found"
            }
        
        # Get current prices
        prices = get_prices(tickers)
        
        # Get dividend data
        dividends = self.dividend.get_dividends(tickers)
        
        # Get valuation data
        valuation = self.valuation.get_valuation(tickers)
        
        # Compute scores
        scores = self.scoring.compute_score(prices, dividends, valuation, {})
        
        # Sort by score
        sorted_tickers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Allocate budget
        recommendations = []
        total_allocated = 0
        priority = 1
        
        for ticker, score in sorted_tickers:
            price = prices.get(ticker, 0)
            if price == 0:
                continue
            
            # Calculate how many shares we can buy
            remaining_budget = budget - total_allocated
            shares = int(remaining_budget / price)
            
            if shares > 0:
                cost = shares * price
                total_allocated += cost
                
                # Generate reasoning
                div_yield = dividends.get(ticker, {}).get("yield", 0)
                pe_ratio = valuation.get(ticker, 0)  # valuation returns float directly
                
                reasoning = f"Score: {score:.2f}. "
                if div_yield > 0:
                    reasoning += f"Dividend yield: {div_yield*100:.2f}%. "
                if pe_ratio > 0:
                    reasoning += f"P/E ratio: {pe_ratio:.2f}. "
                reasoning += "Strong fundamentals and good value."
                
                recommendations.append({
                    "ticker": ticker,
                    "action": "BUY",
                    "shares": shares,
                    "price": round(price, 2),
                    "total_cost": round(cost, 2),
                    "score": round(score, 2),
                    "reasoning": reasoning,
                    "priority": priority
                })
                priority += 1
            
            if total_allocated >= budget * 0.95:  # Use 95% of budget
                break
        
        # Save recommendation run to database
        cursor.execute("""
            SELECT SUM(shares * current_price) as portfolio_value
            FROM portfolio
        """)
        portfolio_row = cursor.fetchone()
        portfolio_value = portfolio_row['portfolio_value'] if portfolio_row['portfolio_value'] else 0
        
        cursor.execute("""
            INSERT INTO recommendation_runs (executed_at, budget, total_allocated, portfolio_value)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), budget, total_allocated, portfolio_value))
        
        run_id = cursor.lastrowid
        
        # Save recommendation items
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO recommendation_items 
                (run_id, ticker, action, shares, price, total_cost, score, reasoning, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, rec['ticker'], rec['action'], rec['shares'], rec['price'], 
                  rec['total_cost'], rec['score'], rec['reasoning'], rec['priority']))
        
        conn.commit()
        conn.close()
        
        return {
            "run_id": run_id,
            "recommendations": recommendations,
            "budget": budget,
            "total_allocated": round(total_allocated, 2),
            "remaining": round(budget - total_allocated, 2),
            "executed_at": datetime.now().isoformat()
        }

    def get_latest_recommendations(self) -> Dict:
        """Get the most recent recommendation run"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get latest run
        cursor.execute("""
            SELECT * FROM recommendation_runs
            ORDER BY executed_at DESC
            LIMIT 1
        """)
        run_row = cursor.fetchone()
        
        if not run_row:
            conn.close()
            return {"message": "No recommendations found"}
        
        run_id = run_row['id']
        
        # Get recommendation items
        cursor.execute("""
            SELECT * FROM recommendation_items
            WHERE run_id = ?
            ORDER BY priority
        """, (run_id,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                "ticker": row['ticker'],
                "action": row['action'],
                "shares": row['shares'],
                "price": round(row['price'], 2),
                "total_cost": round(row['total_cost'], 2),
                "score": round(row['score'], 2),
                "reasoning": row['reasoning'],
                "priority": row['priority']
            })
        
        conn.close()
        
        return {
            "run_id": run_id,
            "executed_at": run_row['executed_at'],
            "budget": run_row['budget'],
            "total_allocated": round(run_row['total_allocated'], 2),
            "portfolio_value": round(run_row['portfolio_value'], 2),
            "recommendations": items
        }

    def get_recommendation_history(self, limit: int = 10) -> List[Dict]:
        """Get past recommendation runs"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.id,
                r.executed_at,
                r.budget,
                r.total_allocated,
                r.portfolio_value,
                COUNT(i.id) as recommendation_count
            FROM recommendation_runs r
            LEFT JOIN recommendation_items i ON r.id = i.run_id
            GROUP BY r.id
            ORDER BY r.executed_at DESC
            LIMIT ?
        """, (limit,))
        
        runs = []
        for row in cursor.fetchall():
            runs.append({
                "run_id": row['id'],
                "executed_at": row['executed_at'],
                "budget": row['budget'],
                "total_allocated": round(row['total_allocated'], 2),
                "portfolio_value": round(row['portfolio_value'], 2),
                "recommendation_count": row['recommendation_count']
            })
        
        conn.close()
        return runs
