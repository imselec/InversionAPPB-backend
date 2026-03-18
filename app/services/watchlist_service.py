"""
Watchlist Service for InversionAPP.
"""
import logging
import warnings
from datetime import datetime
from typing import Dict, List, Optional

from ..database import get_connection
from .market_data_service import get_prices
from .dividend_service import DividendService
from .valuation_service import ValuationService
from .scoring_service import ScoringService

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("yahooquery").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

WATCHLIST_PRIORITY_BONUS = 5.0
DEFAULT_MIN_DIVIDEND_YIELD = 0.02
DEFAULT_MAX_PE_RATIO = 25.0
DEFAULT_MIN_MARKET_CAP = 10_000_000_000

# Simple in-memory cache for yf.info (slow calls)
_info_cache: Dict[str, dict] = {}


def _get_yf_info(ticker: str) -> dict:
    """Fetch yfinance info with cache to avoid repeated slow calls."""
    if ticker in _info_cache:
        return _info_cache[ticker]
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        _info_cache[ticker] = info
        return info
    except Exception:
        return {}


class WatchlistService:

    def __init__(self):
        self.dividend_service = DividendService()
        self.valuation_service = ValuationService()
        self.scoring_service = ScoringService()

    def add_to_watchlist(
        self,
        user_id: int,
        ticker: str,
        notes: Optional[str] = None,
        target_price: Optional[float] = None,
    ) -> Dict:
        ticker = ticker.upper().strip()
        # Skip ETF check to avoid slow yf.info call on add
        # (ETF check is best-effort only)
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
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def get_watchlist_metrics(self, user_id: int) -> List[Dict]:
        """Return watchlist items with live metrics. Fast path: no yf.info."""
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
            logger.warning("Watchlist prices error: %s", e)

        try:
            dividends = self.dividend_service.get_dividends(tickers)
        except Exception as e:
            logger.warning("Watchlist dividends error: %s", e)

        try:
            valuations = self.valuation_service.get_valuation(tickers)
        except Exception as e:
            logger.warning("Watchlist valuations error: %s", e)

        enriched = []
        for item in items:
            t = item["ticker"]
            div_yield = dividends.get(t, {}).get("yield", 0) or 0
            pe = valuations.get(t, 0) or 0
            price = prices.get(t, 0) or 0
            # Score: simple composite
            score = round(min(100, div_yield * 1000 + max(0, 30 - pe) * 1.5), 1)
            meets = (
                div_yield >= DEFAULT_MIN_DIVIDEND_YIELD
                and 0 < pe <= DEFAULT_MAX_PE_RATIO
            )
            enriched.append({
                **item,
                "current_price": price,
                "dividend_yield": div_yield,
                "pe_ratio": pe,
                "market_cap": 0,  # skip slow yf.info call
                "sector": "N/A",
                "industry": "N/A",
                "score": score,
                "meets_criteria": meets,
            })
        return enriched

    def evaluate_buy_criteria(self, ticker: str, **kwargs) -> Dict:
        ticker = ticker.upper().strip()
        dividends = self.dividend_service.get_dividends([ticker])
        valuations = self.valuation_service.get_valuation([ticker])
        div_yield = dividends.get(ticker, {}).get("yield", 0)
        pe_ratio = valuations.get(ticker, 0)
        meets = (
            div_yield >= DEFAULT_MIN_DIVIDEND_YIELD
            and 0 < pe_ratio <= DEFAULT_MAX_PE_RATIO
        )
        return {
            "ticker": ticker,
            "meets_criteria": meets,
            "dividend_yield": div_yield,
            "pe_ratio": pe_ratio,
            "market_cap": 0,
        }

    def compare_with_holdings(self, ticker: str) -> Dict:
        ticker = ticker.upper().strip()
        conn = get_connection()
        holdings = conn.execute(
            "SELECT ticker FROM portfolio"
        ).fetchall()
        conn.close()
        holding_tickers = [r["ticker"] for r in holdings]
        dividends = self.dividend_service.get_dividends([ticker])
        valuations = self.valuation_service.get_valuation([ticker])
        ticker_div_yield = dividends.get(ticker, {}).get("yield", 0)
        ticker_pe = valuations.get(ticker, 0)
        portfolio_avg_yield = 0.0
        portfolio_avg_pe = 0.0
        if holding_tickers:
            h_divs = self.dividend_service.get_dividends(holding_tickers)
            h_vals = self.valuation_service.get_valuation(holding_tickers)
            yields = [h_divs.get(t, {}).get("yield", 0) for t in holding_tickers]
            pes = [h_vals.get(t, 0) for t in holding_tickers if h_vals.get(t, 0) > 0]
            portfolio_avg_yield = sum(yields) / len(yields) if yields else 0
            portfolio_avg_pe = sum(pes) / len(pes) if pes else 0
        return {
            "ticker": ticker,
            "sector": "N/A",
            "industry": "N/A",
            "dividend_yield": ticker_div_yield,
            "pe_ratio": ticker_pe,
            "market_cap": 0,
            "portfolio_avg_dividend_yield": round(portfolio_avg_yield, 4),
            "portfolio_avg_pe_ratio": round(portfolio_avg_pe, 2),
            "yield_vs_portfolio": round(ticker_div_yield - portfolio_avg_yield, 4),
            "pe_vs_portfolio": round(ticker_pe - portfolio_avg_pe, 2),
            "explanation": (
                f"{ticker} offers {ticker_div_yield*100:.1f}% yield vs "
                f"portfolio avg {portfolio_avg_yield*100:.1f}%."
            ),
        }

    def calculate_allocation_impact(self, ticker: str, shares: int = 1) -> Dict:
        ticker = ticker.upper().strip()
        prices = get_prices([ticker])
        current_price = prices.get(ticker, 0)
        conn = get_connection()
        row = conn.execute(
            "SELECT SUM(shares * current_price) as total FROM portfolio"
        ).fetchone()
        conn.close()
        portfolio_value = row["total"] if row and row["total"] else 0
        purchase_value = current_price * shares
        new_portfolio_value = portfolio_value + purchase_value
        new_alloc = (purchase_value / new_portfolio_value * 100) if new_portfolio_value > 0 else 0
        return {
            "ticker": ticker,
            "shares": shares,
            "current_price": round(current_price, 2),
            "purchase_value": round(purchase_value, 2),
            "portfolio_value_before": round(portfolio_value, 2),
            "portfolio_value_after": round(new_portfolio_value, 2),
            "current_allocation_pct": 0.0,
            "new_allocation_pct": round(new_alloc, 4),
            "impact_pct": round(new_alloc, 4),
        }

    def get_prioritized_watchlist(self, user_id: int) -> List[Dict]:
        items = self.get_watchlist_metrics(user_id)
        return sorted(items, key=lambda x: x.get("score", 0), reverse=True)

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
