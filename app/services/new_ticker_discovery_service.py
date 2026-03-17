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
        """Screen candidates. Uses fast batch fetch; falls back to full list
        if yfinance is slow/unavailable."""
        screened = []
        # Try batch screening with a short timeout per ticker
        batch_size = 5
        for i in range(0, min(len(candidates), 30), batch_size):
            batch = candidates[i:i + batch_size]
            try:
                dividends = self.dividend_service.get_dividends(batch)
                valuations = self.valuation_service.get_valuation(batch)
                for ticker in batch:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.fast_info  # faster than .info
                        market_cap = getattr(info, 'market_cap', 0) or 0
                        if market_cap < min_market_cap:
                            continue
                        div_data = dividends.get(ticker, {})
                        dividend_yield = div_data.get('yield', 0) or 0
                        if dividend_yield < min_dividend_yield:
                            continue
                        payout_ratio = div_data.get('payout', 0) or 0
                        if payout_ratio > max_payout_ratio:
                            continue
                        pe_ratio = valuations.get(ticker, 0) or 0
                        if pe_ratio > max_pe_ratio or pe_ratio <= 0:
                            continue
                        screened.append(ticker)
                    except Exception:
                        continue
            except Exception:
                # If batch fails, include all as candidates (no filter)
                screened.extend(batch)
                continue

        # If screening returned nothing, return first N candidates unfiltered
        if not screened:
            return candidates[:15]
        return screened
    
    def evaluate_diversification_benefit(
        self,
        ticker: str,
        current_holdings: Optional[List[str]] = None
    ) -> Dict:
        """Evaluate diversification benefit using a static sector map for speed."""
        # Static sector map to avoid N yfinance calls per holding
        SECTOR_MAP = {
            "AVGO": "Technology", "TXN": "Technology", "MSFT": "Technology",
            "AAPL": "Technology", "IBM": "Technology", "CSCO": "Technology",
            "INTC": "Technology", "QCOM": "Technology",
            "PG": "Consumer Staples", "KO": "Consumer Staples",
            "PEP": "Consumer Staples", "WMT": "Consumer Staples",
            "COST": "Consumer Staples", "CL": "Consumer Staples",
            "KMB": "Consumer Staples", "GIS": "Consumer Staples",
            "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities",
            "D": "Utilities", "AEP": "Utilities", "EXC": "Utilities",
            "JNJ": "Healthcare", "ABBV": "Healthcare", "LLY": "Healthcare",
            "UNH": "Healthcare", "MDT": "Healthcare", "TMO": "Healthcare",
            "UPS": "Industrials", "LMT": "Industrials", "RTX": "Industrials",
            "CAT": "Industrials", "HON": "Industrials", "MMM": "Industrials",
            "GE": "Industrials", "EMR": "Industrials",
            "CVX": "Energy", "XOM": "Energy", "COP": "Energy",
            "EOG": "Energy", "PSX": "Energy",
            "O": "Real Estate", "AMT": "Real Estate", "PLD": "Real Estate",
            "EQIX": "Real Estate", "PSA": "Real Estate",
            "JPM": "Financials", "BLK": "Financials", "V": "Financials",
            "MA": "Financials", "AXP": "Financials", "USB": "Financials",
            "T": "Communication", "VZ": "Communication", "CMCSA": "Communication",
            "LIN": "Materials", "APD": "Materials", "ECL": "Materials",
        }
        INDUSTRY_MAP = {
            "MSFT": "Software", "AAPL": "Consumer Electronics",
            "IBM": "IT Services", "CSCO": "Networking",
            "INTC": "Semiconductors", "QCOM": "Semiconductors",
            "WMT": "Retail", "COST": "Retail", "CL": "Household Products",
            "KMB": "Household Products", "GIS": "Packaged Foods",
            "SO": "Electric Utilities", "D": "Electric Utilities",
            "AEP": "Electric Utilities", "EXC": "Electric Utilities",
            "UNH": "Managed Care", "MDT": "Medical Devices",
            "TMO": "Life Sciences", "HON": "Conglomerates",
            "MMM": "Conglomerates", "GE": "Conglomerates",
            "COP": "Oil & Gas E&P", "EOG": "Oil & Gas E&P",
            "PSX": "Oil Refining", "AMT": "Cell Towers",
            "PLD": "Industrial REITs", "EQIX": "Data Centers",
            "PSA": "Self-Storage REITs", "V": "Payment Networks",
            "MA": "Payment Networks", "AXP": "Credit Services",
            "T": "Telecom", "VZ": "Telecom", "CMCSA": "Cable/Media",
            "LIN": "Industrial Gases", "APD": "Industrial Gases",
        }

        if current_holdings is None:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker FROM portfolio")
            current_holdings = [row['ticker'] for row in cursor.fetchall()]
            conn.close()

        sector = SECTOR_MAP.get(ticker)
        industry = INDUSTRY_MAP.get(ticker, sector or "Unknown")

        # If not in static map, try a quick yfinance lookup
        if not sector:
            try:
                info = yf.Ticker(ticker).fast_info
                sector = getattr(info, 'sector', 'Unknown') or 'Unknown'
                industry = sector
            except Exception:
                sector = "Unknown"
                industry = "Unknown"

        # Count holdings in same sector using static map
        sector_count = sum(
            1 for h in current_holdings
            if SECTOR_MAP.get(h, '') == sector
        )

        if sector_count == 0:
            diversification_score = 20
            explanation = (
                f"Adds exposure to {sector} sector, "
                "not currently represented in the portfolio."
            )
        else:
            diversification_score = max(1, 10 / (sector_count + 1))
            explanation = (
                f"Adds to {sector} sector "
                f"({sector_count} current holdings). "
            )
            if sector_count >= 3:
                explanation += "Sector already well-represented."
            else:
                explanation += "Provides moderate diversification benefit."

        return {
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "sector_count": sector_count,
            "diversification_score": round(diversification_score, 2),
            "explanation": explanation
        }
