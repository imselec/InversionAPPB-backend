"""
Sell Recommendation Service for identifying holdings to sell.

Implements requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.7:
- Identify sell candidates based on valuation, fundamentals, and rebalancing needs
- Analyze overvaluation vs historical P/E metrics
- Detect fundamental deterioration (dividends, payout ratio, debt)
- Calculate tax implications for sell recommendations
- Recommend sell quantities based on reason
"""
from datetime import datetime
from typing import Dict, List, Optional
import warnings
import logging

from .market_data_service import get_prices
from .valuation_service import ValuationService
from .dividend_service import DividendService
from ..database import get_connection

warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)

# Capital gains tax rate for US investments (Spain-based investor)
# Using long-term capital gains rate as a conservative estimate
CAPITAL_GAINS_RATE = 0.20  # 20% long-term capital gains rate

# Sell thresholds per design algorithm
PE_OVERVALUED_MULTIPLIER = 1.5       # current_PE > historical_avg * 1.5
PE_SIGNIFICANTLY_OVERVALUED = 30     # P/E > 30 is significantly overvalued
DIVIDEND_DETERIORATION_THRESHOLD = -0.20  # -20% change in dividend yield
PAYOUT_RATIO_UNSUSTAINABLE = 0.80   # payout ratio > 80%
REBALANCING_OVERWEIGHT_THRESHOLD = 0.20  # 20% allocation triggers rebalancing sell
REBALANCING_TARGET_ALLOCATION = 0.18    # Sell down to 18% allocation


class SellRecommendationService:
    """
    Service for generating sell recommendations based on valuation,
    fundamental deterioration, and portfolio rebalancing needs.
    """

    def __init__(self):
        self.valuation_service = ValuationService()
        self.dividend_service = DividendService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def identify_sell_candidates(self, holdings: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Identify holdings that are candidates for selling.

        Evaluates each holding against three criteria:
        1. Overvaluation (P/E vs historical average)
        2. Fundamental deterioration (dividends, payout ratio, debt)
        3. Rebalancing needs (allocation > 20%)

        Args:
            holdings: List of holding dicts with keys ticker, shares, avg_price.
                      If None, fetched from the database.

        Returns:
            List of sell recommendation dicts sorted by priority.
        """
        if holdings is None:
            holdings = self._get_portfolio_holdings()

        if not holdings:
            return []

        tickers = [h['ticker'] for h in holdings]
        prices = get_prices(tickers)

        # Calculate total portfolio value for allocation checks
        total_value = sum(
            h['shares'] * prices.get(h['ticker'], 0) for h in holdings
        )

        sell_candidates = []

        for holding in holdings:
            ticker = holding['ticker']
            shares = holding['shares']
            avg_price = holding.get('avg_price', 0)
            current_price = prices.get(ticker, 0)

            if current_price <= 0 or shares <= 0:
                continue

            current_value = shares * current_price
            allocation_pct = (current_value / total_value) if total_value > 0 else 0

            # Run all three checks
            valuation_result = self.analyze_valuation_exit(ticker)
            fundamental_result = self.analyze_fundamental_deterioration(ticker)

            reasons = []

            # Fundamental deterioration — highest priority
            if fundamental_result.get('should_sell'):
                reasons.append({
                    'reason': 'FUNDAMENTAL_DETERIORATION',
                    'priority': 1,
                    'detail': fundamental_result.get('reasoning', ''),
                })

            # Significant overvaluation (P/E > 30)
            if valuation_result.get('significantly_overvalued'):
                reasons.append({
                    'reason': 'OVERVALUED',
                    'priority': 2,
                    'detail': valuation_result.get('reasoning', ''),
                })
            elif valuation_result.get('overvalued'):
                reasons.append({
                    'reason': 'OVERVALUED',
                    'priority': 3,
                    'detail': valuation_result.get('reasoning', ''),
                })

            # Rebalancing need
            if allocation_pct > REBALANCING_OVERWEIGHT_THRESHOLD:
                reasons.append({
                    'reason': 'REBALANCING',
                    'priority': 4,
                    'detail': (
                        f"{ticker} represents {allocation_pct * 100:.1f}% of portfolio, "
                        f"exceeding the 20% overweight threshold."
                    ),
                })

            if not reasons:
                continue

            # Use the highest-priority reason
            primary = min(reasons, key=lambda r: r['priority'])
            reason = primary['reason']
            reasoning_detail = primary['detail']

            shares_to_sell = self.recommend_sell_quantity(
                ticker=ticker,
                reason=reason,
                shares=shares,
                current_price=current_price,
                total_value=total_value,
            )

            tax = self.calculate_tax_implications(
                ticker=ticker,
                shares=shares_to_sell,
                avg_price=avg_price,
                current_price=current_price,
            )

            holding_period_days = self._get_holding_period_days(ticker)
            gain_loss = (current_price - avg_price) * shares_to_sell

            sell_candidates.append({
                'ticker': ticker,
                'shares_to_sell': round(shares_to_sell, 4),
                'current_price': round(current_price, 2),
                'total_proceeds': round(shares_to_sell * current_price, 2),
                'reason': reason,
                'reasoning_detail': reasoning_detail,
                'tax_implications': round(tax, 2),
                'holding_period_days': holding_period_days,
                'gain_loss': round(gain_loss, 2),
                'priority': primary['priority'],
            })

        # Sort by priority (lower number = higher urgency)
        sell_candidates.sort(key=lambda x: x['priority'])

        return sell_candidates

    def analyze_valuation_exit(self, ticker: str) -> Dict:
        """
        Determine if a stock is overvalued based on P/E ratio analysis.

        Checks:
        - current_PE > historical_avg_PE * 1.5  → overvalued
        - current_PE > 30                        → significantly overvalued

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Dict with keys: overvalued, significantly_overvalued, current_pe,
            historical_avg_pe, reasoning.
        """
        try:
            valuations = self.valuation_service.get_valuation([ticker])
            current_pe = valuations.get(ticker, 0)

            historical_avg_pe = self._get_historical_avg_pe(ticker)

            overvalued = False
            significantly_overvalued = False
            reasoning_parts = []

            if current_pe > 0:
                if current_pe > PE_SIGNIFICANTLY_OVERVALUED:
                    significantly_overvalued = True
                    overvalued = True
                    reasoning_parts.append(
                        f"P/E ratio of {current_pe:.1f} exceeds the significantly overvalued "
                        f"threshold of {PE_SIGNIFICANTLY_OVERVALUED}."
                    )

                if historical_avg_pe > 0 and current_pe > historical_avg_pe * PE_OVERVALUED_MULTIPLIER:
                    overvalued = True
                    reasoning_parts.append(
                        f"Current P/E ({current_pe:.1f}) is {current_pe / historical_avg_pe:.1f}x "
                        f"the historical average ({historical_avg_pe:.1f}), "
                        f"exceeding the 1.5x overvaluation threshold."
                    )

            reasoning = ' '.join(reasoning_parts) if reasoning_parts else (
                f"P/E ratio of {current_pe:.1f} is within acceptable range."
                if current_pe > 0 else "P/E data unavailable."
            )

            return {
                'ticker': ticker,
                'overvalued': overvalued,
                'significantly_overvalued': significantly_overvalued,
                'current_pe': round(current_pe, 2),
                'historical_avg_pe': round(historical_avg_pe, 2),
                'reasoning': reasoning,
            }

        except Exception as e:
            return {
                'ticker': ticker,
                'overvalued': False,
                'significantly_overvalued': False,
                'current_pe': 0,
                'historical_avg_pe': 0,
                'reasoning': f"Unable to analyze valuation: {str(e)}",
            }

    def analyze_fundamental_deterioration(self, ticker: str) -> Dict:
        """
        Check for deteriorating fundamentals: declining dividends, high payout ratio,
        and increased debt.

        Checks:
        - dividend_yield_change < -20%  → deteriorating dividends
        - payout_ratio > 80%            → unsustainable payout
        - debt_to_equity increased >50% YoY → risky debt levels

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Dict with keys: should_sell, issues (list), reasoning.
        """
        issues = []
        reasoning_parts = []

        try:
            div_data = self.dividend_service.get_dividends([ticker])
            ticker_div = div_data.get(ticker, {})
            current_yield = ticker_div.get('yield', 0)
            payout_ratio = ticker_div.get('payout', 0)

            # Check payout ratio sustainability
            if payout_ratio > PAYOUT_RATIO_UNSUSTAINABLE:
                issues.append('HIGH_PAYOUT_RATIO')
                reasoning_parts.append(
                    f"Payout ratio of {payout_ratio * 100:.1f}% exceeds the "
                    f"unsustainable threshold of {PAYOUT_RATIO_UNSUSTAINABLE * 100:.0f}%."
                )

            # Check dividend yield deterioration vs historical
            historical_yield = self._get_historical_dividend_yield(ticker)
            if historical_yield > 0 and current_yield > 0:
                yield_change = (current_yield - historical_yield) / historical_yield
                if yield_change < DIVIDEND_DETERIORATION_THRESHOLD:
                    issues.append('DECLINING_DIVIDEND')
                    reasoning_parts.append(
                        f"Dividend yield has declined {abs(yield_change) * 100:.1f}% "
                        f"from historical average ({historical_yield * 100:.2f}% → "
                        f"{current_yield * 100:.2f}%), exceeding the 20% deterioration threshold."
                    )

            # Check debt-to-equity deterioration
            debt_change = self._get_debt_change(ticker)
            if debt_change is not None and debt_change > 0.50:
                issues.append('INCREASED_DEBT')
                reasoning_parts.append(
                    f"Debt-to-equity ratio has increased by {debt_change * 100:.1f}% "
                    f"year-over-year, exceeding the 50% risk threshold."
                )

        except Exception as e:
            reasoning_parts.append(f"Unable to fully analyze fundamentals: {str(e)}")

        should_sell = len(issues) > 0
        reasoning = ' '.join(reasoning_parts) if reasoning_parts else (
            "Fundamentals appear healthy — no deterioration detected."
        )

        return {
            'ticker': ticker,
            'should_sell': should_sell,
            'issues': issues,
            'reasoning': reasoning,
        }

    def calculate_tax_implications(
        self,
        ticker: str,
        shares: float,
        avg_price: Optional[float] = None,
        current_price: Optional[float] = None,
    ) -> float:
        """
        Estimate capital gains tax for selling a given number of shares.

        Formula: tax = max(0, (current_price - avg_price) * shares * CAPITAL_GAINS_RATE)
        Only gains are taxed; losses result in $0 tax (though they may offset gains).

        Args:
            ticker: Stock ticker symbol.
            shares: Number of shares to sell.
            avg_price: Average purchase price per share (fetched from DB if None).
            current_price: Current market price (fetched if None).

        Returns:
            Estimated tax amount in USD.
        """
        try:
            if avg_price is None:
                avg_price = self._get_avg_price(ticker)

            if current_price is None:
                prices = get_prices([ticker])
                current_price = prices.get(ticker, 0)

            if current_price <= 0 or avg_price <= 0 or shares <= 0:
                return 0.0

            gain_per_share = current_price - avg_price
            if gain_per_share <= 0:
                return 0.0  # No tax on losses

            tax = gain_per_share * shares * CAPITAL_GAINS_RATE
            return round(tax, 2)

        except Exception:
            return 0.0

    def recommend_sell_quantity(
        self,
        ticker: str,
        reason: str,
        shares: Optional[float] = None,
        current_price: Optional[float] = None,
        total_value: Optional[float] = None,
    ) -> float:
        """
        Recommend how many shares to sell based on the sell reason.

        Rules per design algorithm:
        - FUNDAMENTAL_DETERIORATION → sell 100% of position
        - OVERVALUED                → sell 50% of position
        - REBALANCING               → sell excess shares to reach 18% allocation

        Args:
            ticker: Stock ticker symbol.
            reason: One of 'FUNDAMENTAL_DETERIORATION', 'OVERVALUED', 'REBALANCING'.
            shares: Current shares held (fetched from DB if None).
            current_price: Current market price (fetched if None).
            total_value: Total portfolio value (fetched if None).

        Returns:
            Number of shares to sell (float, >= 0).
        """
        try:
            if shares is None:
                shares = self._get_shares(ticker)

            if shares <= 0:
                return 0.0

            if reason == 'FUNDAMENTAL_DETERIORATION':
                return shares  # Sell entire position

            if reason == 'OVERVALUED':
                return shares * 0.5  # Sell half

            if reason == 'REBALANCING':
                if current_price is None:
                    prices = get_prices([ticker])
                    current_price = prices.get(ticker, 0)

                if total_value is None:
                    total_value = self._get_total_portfolio_value()

                if current_price <= 0 or total_value <= 0:
                    return 0.0

                current_value = shares * current_price
                target_value = total_value * REBALANCING_TARGET_ALLOCATION
                excess_value = current_value - target_value

                if excess_value <= 0:
                    return 0.0

                shares_to_sell = excess_value / current_price
                return min(shares_to_sell, shares)

            # Unknown reason — no sell
            return 0.0

        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_portfolio_holdings(self) -> List[Dict]:
        """Fetch current portfolio holdings from the database."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, shares, avg_price FROM portfolio WHERE shares > 0")
        rows = cursor.fetchall()
        conn.close()
        return [{'ticker': r['ticker'], 'shares': r['shares'], 'avg_price': r['avg_price'] or 0}
                for r in rows]

    def _get_avg_price(self, ticker: str) -> float:
        """Fetch average purchase price for a ticker from the database."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT avg_price FROM portfolio WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        return row['avg_price'] if row and row['avg_price'] else 0.0

    def _get_shares(self, ticker: str) -> float:
        """Fetch current shares held for a ticker from the database."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT shares FROM portfolio WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        return row['shares'] if row else 0.0

    def _get_total_portfolio_value(self) -> float:
        """Calculate total current portfolio value."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, shares FROM portfolio WHERE shares > 0")
        holdings = cursor.fetchall()
        conn.close()

        if not holdings:
            return 0.0

        tickers = [h['ticker'] for h in holdings]
        prices = get_prices(tickers)
        return sum(h['shares'] * prices.get(h['ticker'], 0) for h in holdings)

    def _get_holding_period_days(self, ticker: str) -> int:
        """
        Calculate the number of days the position has been held,
        based on the earliest BUY transaction for the ticker.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MIN(date) as first_buy FROM transactions WHERE ticker = ? AND action = 'BUY'",
            (ticker,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row or not row['first_buy']:
            return 0

        try:
            first_buy_str = row['first_buy']
            # Handle both date-only and datetime strings
            if 'T' in first_buy_str or ' ' in first_buy_str:
                first_buy = datetime.fromisoformat(first_buy_str.replace('Z', ''))
            else:
                first_buy = datetime.strptime(first_buy_str, '%Y-%m-%d')
            return (datetime.now() - first_buy).days
        except Exception:
            return 0

    def _get_historical_avg_pe(self, ticker: str) -> float:
        """
        Estimate historical average P/E ratio for a ticker.
        Uses yahooquery to fetch 5-year average P/E if available,
        falling back to a sector-based estimate.
        """
        try:
            from yahooquery import Ticker
            import warnings
            warnings.filterwarnings('ignore')

            data = Ticker(ticker)

            # yahooquery doesn't expose historical P/E directly;
            # use the forward P/E as a proxy for historical average when available
            summary = data.summary_detail.get(ticker, {})
            if isinstance(summary, dict):
                forward_pe = summary.get('forwardPE', 0)
                trailing_pe = summary.get('trailingPE', 0)

                # Use average of forward and trailing as a rough historical proxy
                if forward_pe > 0 and trailing_pe > 0:
                    return (forward_pe + trailing_pe) / 2
                if forward_pe > 0:
                    return forward_pe

            # Sector-based fallback averages
            profile = data.summary_profile.get(ticker, {})
            sector = profile.get('sector', '') if isinstance(profile, dict) else ''
            return self._sector_avg_pe(sector)

        except Exception:
            return 20.0  # Conservative market average fallback

    def _sector_avg_pe(self, sector: str) -> float:
        """Return a reasonable historical average P/E for a given sector."""
        sector_pe = {
            'Technology': 28.0,
            'Healthcare': 22.0,
            'Consumer Defensive': 20.0,
            'Consumer Cyclical': 22.0,
            'Financial Services': 14.0,
            'Industrials': 20.0,
            'Energy': 15.0,
            'Utilities': 18.0,
            'Real Estate': 35.0,
            'Basic Materials': 18.0,
            'Communication Services': 22.0,
        }
        return sector_pe.get(sector, 20.0)

    def _get_historical_dividend_yield(self, ticker: str) -> float:
        """
        Estimate historical average dividend yield for a ticker.
        Uses the 1-year average from yahooquery if available.
        """
        try:
            from yahooquery import Ticker
            import warnings
            warnings.filterwarnings('ignore')

            data = Ticker(ticker)
            summary = data.summary_detail.get(ticker, {})
            if isinstance(summary, dict) and 'error' not in str(summary).lower():
                # fiveYearAvgDividendYield is expressed as a percentage (e.g. 2.5 means 2.5%)
                five_year_avg = summary.get('fiveYearAvgDividendYield', 0)
                if five_year_avg and five_year_avg > 0:
                    return five_year_avg / 100  # Convert to decimal
            return 0.0
        except Exception:
            return 0.0

    def _get_debt_change(self, ticker: str) -> Optional[float]:
        """
        Estimate year-over-year change in debt-to-equity ratio.
        Returns fractional change (e.g. 0.5 = 50% increase), or None if unavailable.
        """
        try:
            from yahooquery import Ticker
            import warnings
            warnings.filterwarnings('ignore')

            data = Ticker(ticker)
            financial_data = data.financial_data.get(ticker, {})
            if not isinstance(financial_data, dict):
                return None

            # currentRatio and debtToEquity are available in financial_data
            current_de = financial_data.get('debtToEquity', None)
            if current_de is None:
                return None

            # yahooquery doesn't provide prior-year D/E directly;
            # use key_stats for the 5-year beta as a proxy signal is not ideal.
            # Instead, compare against a conservative baseline of 1.0 (100%)
            # and flag if current D/E > 1.5 (implying >50% above baseline).
            # This is a simplified heuristic when historical data is unavailable.
            baseline_de = 1.0
            if current_de > baseline_de * 1.5:
                return (current_de - baseline_de) / baseline_de

            return 0.0

        except Exception:
            return None
