"""
Watchlist Service for InversionAPP.

Manages the user's watchlist of stocks being monitored for potential purchase.

Implements requirements 15.1–15.10:
- Add/remove tickers from watchlist (with ETF rejection)
- Fetch live metrics: dividend yield, P/E ratio, market cap
- Evaluate buy criteria against user-defined conditions
- Compare watchlist stock with current holdings
- Calculate allocation impact if stock is added
- Prioritize watchlist using recommendation scoring algorithm
"""
import logging
import warnings
from datetime import datetime
from typing import Dict, List, Optional

import yfinance as yf

from ..database import get_connection
from .market_data_service import get_prices
from .dividend_service import DividendService
from .valuation_service import ValuationService
from .scoring_service import ScoringService

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("yahooquery").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# Priority bonus added to watchlist stocks in scoring (req 15.7)
WATCHLIST_PRIORITY_BONUS = 5.0

# Default buy criteria thresholds
DEFAULT_MIN_DIVIDEND_YIELD = 0.02   # 2 %
DEFAULT_MAX_PE_RATIO = 25.0
DEFAULT_MIN_MARKET_CAP = 10_000_000_000  # $10 B


class WatchlistService:
    """
    Service for managing and evaluating the user's stock watchlist.
    """

    def __init__(self):
        self.dividend_service = DividendService()
        self.valuation_service = ValuationService()
        self.scoring_service = ScoringService()

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def add_to_watchlist(
        self,
        user_id: int,
        ticker: str,
        notes: Optional[str] = None,
        target_price: Optional[float] = None,
    ) -> Dict:
        """
        Add a ticker to the watchlist.

        Rejects ETF tickers (requirement 15.10).
        Prevents duplicate (user_id, ticker) entries (requirement 15.2).

        Returns the created watchlist record.
        Raises ValueError for ETFs or duplicates.
        """
        ticker = ticker.upper().strip()

        # ETF validation (req 15.10)
        if self._is_etf(ticker):
            raise ValueError(
                f"{ticker} is an ETF and cannot be added to the watchlist."
            )

        now = datetime.now().isoformat()
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO watchlist "
                "(user_id, ticker, added_at, notes, target_price) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, ticker, now, notes, target_price),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM watchlist WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            ).fetchone()
            return self._row_to_dict(row)
        except Exception as exc:
            conn.rollback()
            raise ValueError(
                f"Could not add {ticker} to watchlist: {exc}"
            ) from exc
        finally:
            conn.close()

    def remove_from_watchlist(self, user_id: int, ticker: str) -> bool:
        """
        Remove a ticker from the watchlist.

        Returns True if removed, False if not found.
        """
        ticker = ticker.upper().strip()
        conn = get_connection()
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_watchlist(self, user_id: int) -> List[Dict]:
        """
        Return all watchlist items for a user (ordered by added_at desc).
        """
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_watchlist_metrics(self, user_id: int) -> List[Dict]:
        """
        Return watchlist items enriched with live market metrics.

        Each item includes: dividend_yield, pe_ratio, market_cap,
        current_price, sector, industry (req 15.3, 15.4).
        """
        items = self.get_watchlist(user_id)
        if not items:
            return []

        tickers = [i["ticker"] for i in items]
        prices = {}
        dividends = {}
        valuations = {}

        try:
            prices = get_prices(tickers)
        except Exception as e:
            logger.warning("Failed to fetch prices for watchlist: %s", e)

        try:
            dividends = self.dividend_service.get_dividends(tickers)
        except Exception as e:
            logger.warning("Failed to fetch dividends for watchlist: %s", e)

        try:
            valuations = self.valuation_service.get_valuation(tickers)
        except Exception as e:
            logger.warning("Failed to fetch valuations for watchlist: %s", e)

        enriched = []
        for item in items:
            ticker = item["ticker"]
            market_cap, sector, industry = self._get_stock_info(ticker)
            enriched.append({
                **item,
                "current_price": prices.get(ticker, 0),
                "dividend_yield": dividends.get(ticker, {}).get("yield", 0),
                "pe_ratio": valuations.get(ticker, 0),
                "market_cap": market_cap,
                "sector": sector,
                "industry": industry,
            })
        return enriched

    def update_metrics(self, user_id: int) -> List[Dict]:
        """Alias for get_watchlist_metrics — used by the scheduler."""
        return self.get_watchlist_metrics(user_id)

    # ------------------------------------------------------------------
    # Buy criteria evaluation
    # ------------------------------------------------------------------

    def evaluate_buy_criteria(
        self,
        ticker: str,
        min_dividend_yield: float = DEFAULT_MIN_DIVIDEND_YIELD,
        max_pe_ratio: float = DEFAULT_MAX_PE_RATIO,
        min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
    ) -> Dict:
        """
        Check whether a ticker meets user-defined buy conditions (req 15.5).

        Returns a dict with 'meets_criteria' bool and per-condition results.
        """
        ticker = ticker.upper().strip()
        dividends = self.dividend_service.get_dividends([ticker])
        valuations = self.valuation_service.get_valuation([ticker])
        market_cap, _, _ = self._get_stock_info(ticker)

        div_yield = dividends.get(ticker, {}).get("yield", 0)
        pe_ratio = valuations.get(ticker, 0)

        conditions = {
            "dividend_yield_ok": div_yield >= min_dividend_yield,
            "pe_ratio_ok": 0 < pe_ratio <= max_pe_ratio,
            "market_cap_ok": market_cap >= min_market_cap,
        }
        meets_criteria = all(conditions.values())

        return {
            "ticker": ticker,
            "meets_criteria": meets_criteria,
            "dividend_yield": div_yield,
            "pe_ratio": pe_ratio,
            "market_cap": market_cap,
            "conditions": conditions,
        }

    # ------------------------------------------------------------------
    # Comparison with holdings
    # ------------------------------------------------------------------

    def compare_with_holdings(self, ticker: str) -> Dict:
        """
        Compare a watchlist ticker with current portfolio holdings (req 15.6).

        Returns metrics for the watchlist ticker alongside portfolio averages.
        """
        ticker = ticker.upper().strip()
        conn = get_connection()
        holdings = conn.execute(
            "SELECT ticker FROM portfolio"
        ).fetchall()
        conn.close()

        holding_tickers = [r["ticker"] for r in holdings]

        # Metrics for the watchlist ticker
        dividends = self.dividend_service.get_dividends([ticker])
        valuations = self.valuation_service.get_valuation([ticker])
        market_cap, sector, industry = self._get_stock_info(ticker)

        ticker_div_yield = dividends.get(ticker, {}).get("yield", 0)
        ticker_pe = valuations.get(ticker, 0)

        # Portfolio averages
        portfolio_avg_yield = 0.0
        portfolio_avg_pe = 0.0
        if holding_tickers:
            h_divs = self.dividend_service.get_dividends(holding_tickers)
            h_vals = self.valuation_service.get_valuation(holding_tickers)
            yields = [
                h_divs.get(t, {}).get("yield", 0) for t in holding_tickers
            ]
            pes = [
                h_vals.get(t, 0) for t in holding_tickers
                if h_vals.get(t, 0) > 0
            ]
            portfolio_avg_yield = sum(yields) / len(yields) if yields else 0
            portfolio_avg_pe = sum(pes) / len(pes) if pes else 0

        return {
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "dividend_yield": ticker_div_yield,
            "pe_ratio": ticker_pe,
            "market_cap": market_cap,
            "portfolio_avg_dividend_yield": round(portfolio_avg_yield, 4),
            "portfolio_avg_pe_ratio": round(portfolio_avg_pe, 2),
            "yield_vs_portfolio": round(
                ticker_div_yield - portfolio_avg_yield, 4
            ),
            "pe_vs_portfolio": round(ticker_pe - portfolio_avg_pe, 2),
        }

    # ------------------------------------------------------------------
    # Allocation impact
    # ------------------------------------------------------------------

    def calculate_allocation_impact(
        self, ticker: str, shares: int = 1
    ) -> Dict:
        """
        Estimate the allocation change if a watchlist stock is added
        (req 15.9).

        Args:
            ticker: Ticker to evaluate.
            shares: Number of shares to hypothetically purchase (default 1).

        Returns:
            Dict with current_allocation_pct, new_allocation_pct, impact_pct.
        """
        ticker = ticker.upper().strip()
        prices = get_prices([ticker])
        current_price = prices.get(ticker, 0)

        conn = get_connection()
        portfolio_value_row = conn.execute(
            "SELECT SUM(shares * current_price) as total FROM portfolio"
        ).fetchone()
        conn.close()

        portfolio_value = (
            portfolio_value_row["total"]
            if portfolio_value_row and portfolio_value_row["total"]
            else 0
        )

        purchase_value = current_price * shares
        new_portfolio_value = portfolio_value + purchase_value

        current_allocation_pct = 0.0
        new_allocation_pct = (
            (purchase_value / new_portfolio_value * 100)
            if new_portfolio_value > 0
            else 0.0
        )

        return {
            "ticker": ticker,
            "shares": shares,
            "current_price": round(current_price, 2),
            "purchase_value": round(purchase_value, 2),
            "portfolio_value_before": round(portfolio_value, 2),
            "portfolio_value_after": round(new_portfolio_value, 2),
            "current_allocation_pct": round(current_allocation_pct, 4),
            "new_allocation_pct": round(new_allocation_pct, 4),
            "impact_pct": round(
                new_allocation_pct - current_allocation_pct, 4
            ),
        }

    # ------------------------------------------------------------------
    # Prioritized watchlist
    # ------------------------------------------------------------------

    def get_prioritized_watchlist(self, user_id: int) -> List[Dict]:
        """
        Return watchlist items sorted by recommendation score (req 15.7).

        Watchlist stocks receive a WATCHLIST_PRIORITY_BONUS on top of their
        base score so they surface above non-watchlist candidates.
        """
        items = self.get_watchlist_metrics(user_id)
        if not items:
            return []

        prices = {i["ticker"]: i["current_price"] for i in items}
        dividends = {
            i["ticker"]: {
                "yield": i["dividend_yield"],
                "payout": 0,
            }
            for i in items
        }
        valuations = {i["ticker"]: i["pe_ratio"] for i in items}

        scores = self.scoring_service.compute_score(
            prices, dividends, valuations, {}
        )

        for item in items:
            base_score = scores.get(item["ticker"], 0)
            item["score"] = round(base_score + WATCHLIST_PRIORITY_BONUS, 2)

        return sorted(items, key=lambda x: x["score"], reverse=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_etf(self, ticker: str) -> bool:
        """Return True if the ticker is an ETF (req 15.10)."""
        try:
            info = yf.Ticker(ticker).info
            return info.get("quoteType", "").upper() == "ETF"
        except Exception:
            return False

    def _get_stock_info(self, ticker: str):
        """Return (market_cap, sector, industry) for a ticker."""
        try:
            info = yf.Ticker(ticker).info
            return (
                info.get("marketCap", 0),
                info.get("sector", "Unknown"),
                info.get("industry", "Unknown"),
            )
        except Exception:
            return 0, "Unknown", "Unknown"

    @staticmethod
    def _row_to_dict(row) -> Dict:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "ticker": row["ticker"],
            "added_at": row["added_at"],
            "notes": row["notes"],
            "target_price": row["target_price"],
        }
