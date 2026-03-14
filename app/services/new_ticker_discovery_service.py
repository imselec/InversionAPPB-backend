"""
New Ticker Discovery Service for identifying potential new stocks to add to portfolio.
"""
from typing import Dict, List, Optional
import yfinance as yf
import warnings
import logging
from .market_data_service import get_prices
from .dividend_service import DividendService
from .valuation_service import ValuationService
from .scoring_service import ScoringService
from ..database import get_connection

# Suppress warnings
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)


class NewTickerDiscoveryService:
    """
    Service for discovering and evaluating new ticker candidates for portfolio diversification.
    
    Implements requirements 11.1, 11.2, 11.3, 11.6, 11.7:
    - Analyze market opportunities for stocks not in current holdings
    - Evaluate based on dividend yield, valuation, sector diversification
    - Recommend tickers that improve diversification
    - Limit to market cap > $10 billion
    - Exclude ETFs
    """
    
    def __init__(self):
        self.dividend_service = DividendService()
        self.valuation_service = ValuationService()
        self.scoring_service = ScoringService()
    
    def discover_candidates(
        self, 
        min_market_cap: float = 10_000_000_000,  # $10 billion
        min_dividend_yield: float = 0.02,  # 2%
        max_pe_ratio: float = 25,
        max_payout_ratio: float = 0.70,
        limit: int = 50
    ) -> List[str]:
        """
        Discover candidate tickers based on screening criteria.
        
        Args:
            min_market_cap: Minimum market capitalization (default $10B)
            min_dividend_yield: Minimum dividend yield (default 2%)
            max_pe_ratio: Maximum P/E ratio (default 25)
            max_payout_ratio: Maximum payout ratio (default 70%)
            limit: Maximum number of candidates to return
            
        Returns:
            List of ticker symbols that meet screening criteria
        """
        # Get current portfolio tickers to exclude
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM portfolio")
        current_holdings = {row['ticker'] for row in cursor.fetchall()}
        conn.close()
        
        # Predefined universe of high-quality dividend stocks
        # This is a curated list of S&P 500 dividend aristocrats and quality dividend payers
        candidate_universe = [
            # Technology
            "MSFT", "AAPL", "IBM", "CSCO", "INTC", "QCOM",
            # Healthcare
            "UNH", "MDT", "TMO", "DHR", "SYK", "BSX",
            # Consumer Staples
            "WMT", "COST", "CL", "KMB", "GIS", "K", "MKC",
            # Financials
            "V", "MA", "AXP", "USB", "PNC", "TFC", "BK",
            # Industrials
            "HON", "MMM", "GE", "EMR", "ITW", "PH",
            # Energy
            "COP", "EOG", "PSX", "VLO", "MPC",
            # Utilities
            "SO", "D", "AEP", "EXC", "SRE", "ES",
            # Real Estate
            "AMT", "PLD", "EQIX", "PSA", "DLR", "SPG",
            # Materials
            "LIN", "APD", "ECL", "SHW", "NEM",
            # Communication Services
            "T", "VZ", "TMUS", "CMCSA"
        ]
        
        # Filter out current holdings
        candidates = [t for t in candidate_universe if t not in current_holdings]

        # Prepend watchlist tickers so they are evaluated first (req 15.7)
        try:
            from .watchlist_service import WatchlistService
            wl_items = WatchlistService().get_watchlist(user_id=1)
            wl_tickers = [
                item["ticker"] for item in wl_items
                if item["ticker"] not in current_holdings
            ]
            # Put watchlist tickers at the front, then the rest
            candidates = wl_tickers + [
                t for t in candidates if t not in wl_tickers
            ]
        except Exception:
            pass  # watchlist unavailable — continue with normal order
        
        # Screen candidates by fundamentals
        screened_candidates = self.screen_by_fundamentals(
            candidates,
            min_market_cap=min_market_cap,
            min_dividend_yield=min_dividend_yield,
            max_pe_ratio=max_pe_ratio,
            max_payout_ratio=max_payout_ratio
        )
        
        return screened_candidates[:limit]
    
    def screen_by_fundamentals(
        self,
        candidates: List[str],
        min_market_cap: float = 10_000_000_000,
        min_dividend_yield: float = 0.02,
        max_pe_ratio: float = 25,
        max_payout_ratio: float = 0.70
    ) -> List[str]:
        """
        Screen candidates by fundamental criteria.
        
        Args:
            candidates: List of ticker symbols to screen
            min_market_cap: Minimum market capitalization
            min_dividend_yield: Minimum dividend yield
            max_pe_ratio: Maximum P/E ratio
            max_payout_ratio: Maximum payout ratio
            
        Returns:
            List of tickers that pass all screening criteria
        """
        screened = []
        
        # Fetch data in batches to avoid API limits
        batch_size = 10
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            
            try:
                # Get dividend data
                dividends = self.dividend_service.get_dividends(batch)
                
                # Get valuation data
                valuations = self.valuation_service.get_valuation(batch)
                
                # Get market cap and other info
                for ticker in batch:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        
                        # Check if it's an ETF (Requirement 11.7)
                        quote_type = info.get('quoteType', '')
                        if quote_type == 'ETF':
                            continue
                        
                        # Get market cap (Requirement 11.6)
                        market_cap = info.get('marketCap', 0)
                        if market_cap < min_market_cap:
                            continue
                        
                        # Get dividend yield (Requirement 11.2)
                        div_data = dividends.get(ticker, {})
                        dividend_yield = div_data.get('yield', 0)
                        if dividend_yield < min_dividend_yield:
                            continue
                        
                        # Get payout ratio (Requirement 11.2)
                        payout_ratio = div_data.get('payout', 0)
                        if payout_ratio > max_payout_ratio:
                            continue
                        
                        # Get P/E ratio (Requirement 11.2)
                        pe_ratio = valuations.get(ticker, 0)
                        if pe_ratio > max_pe_ratio or pe_ratio <= 0:
                            continue
                        
                        # Passed all screens
                        screened.append(ticker)
                        
                    except Exception as e:
                        # Skip tickers with data issues
                        continue
                        
            except Exception as e:
                # Skip batch if there's an error
                continue
        
        return screened
    
    def evaluate_diversification_benefit(
        self,
        ticker: str,
        current_holdings: Optional[List[str]] = None
    ) -> Dict:
        """
        Evaluate how a new ticker would benefit portfolio diversification.
        
        Args:
            ticker: Ticker symbol to evaluate
            current_holdings: List of current portfolio tickers (fetched if not provided)
            
        Returns:
            Dictionary with diversification analysis including:
            - sector: Ticker's sector
            - industry: Ticker's industry
            - sector_count: Number of current holdings in same sector
            - diversification_score: Score indicating diversification benefit (0-20)
            - explanation: Text explaining the diversification benefit
        """
        # Get current holdings if not provided
        if current_holdings is None:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker FROM portfolio")
            current_holdings = [row['ticker'] for row in cursor.fetchall()]
            conn.close()
        
        try:
            # Get ticker info
            stock = yf.Ticker(ticker)
            info = stock.info
            
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            # Count holdings in same sector
            sector_count = 0
            for holding_ticker in current_holdings:
                try:
                    holding_stock = yf.Ticker(holding_ticker)
                    holding_info = holding_stock.info
                    if holding_info.get('sector', '') == sector:
                        sector_count += 1
                except:
                    continue
            
            # Calculate diversification score (Requirement 11.3)
            # Higher score for sectors not well represented
            if sector_count == 0:
                diversification_score = 20  # New sector - maximum benefit
                explanation = f"Adds exposure to {sector} sector, which is not currently represented in the portfolio."
            else:
                diversification_score = 10 / (sector_count + 1)
                explanation = f"Adds additional exposure to {sector} sector (currently {sector_count} holdings). "
                if sector_count >= 3:
                    explanation += "This sector is already well-represented in the portfolio."
                else:
                    explanation += "This provides moderate diversification benefit."
            
            return {
                "ticker": ticker,
                "sector": sector,
                "industry": industry,
                "sector_count": sector_count,
                "diversification_score": round(diversification_score, 2),
                "explanation": explanation
            }
            
        except Exception as e:
            return {
                "ticker": ticker,
                "sector": "Unknown",
                "industry": "Unknown",
                "sector_count": 0,
                "diversification_score": 0,
                "explanation": f"Unable to evaluate diversification benefit: {str(e)}"
            }
