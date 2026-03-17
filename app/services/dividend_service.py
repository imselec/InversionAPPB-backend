from datetime import datetime
from typing import Dict, List, Optional
import warnings
import logging
from ..database import get_connection

warnings.filterwarnings('ignore')
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)


class DividendService:

    def get_dividends(self, tickers):
        from yahooquery import Ticker
        result = {}
        try:
            data = Ticker(tickers)
            for t in tickers:
                try:
                    summary = data.summary_detail.get(t, {})
                    if (isinstance(summary, dict)
                            and 'error' not in str(summary).lower()):
                        result[t] = {
                            "yield": summary.get("dividendYield", 0),
                            "payout": summary.get("payoutRatio", 0)
                        }
                    else:
                        result[t] = {"yield": 0, "payout": 0}
                except Exception:
                    result[t] = {"yield": 0, "payout": 0}
        except Exception:
            for t in tickers:
                result[t] = {"yield": 0, "payout": 0}
        return result

    def get_annual_dividend(self, ticker):
        try:
            dividends = self.get_dividends([ticker])
            dividend_yield = dividends.get(ticker, {}).get("yield", 0)
            from .market_data_service import get_prices
            prices = get_prices([ticker])
            price = prices.get(ticker, 0)
            if price > 0 and dividend_yield > 0:
                return price * dividend_yield
            return 0
        except Exception:
            return 0

    def get_dividend_summary(self) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(amount) as monthly_total
            FROM dividend_payments
            WHERE payment_date >= date('now', '-30 days')
        """)
        row = cursor.fetchone()
        monthly_total = row['monthly_total'] if row['monthly_total'] else 0.0
        cursor.execute("""
            SELECT SUM(amount) as yearly_total
            FROM dividend_payments
            WHERE payment_date >= date('now', '-365 days')
        """)
        row = cursor.fetchone()
        yearly_total = row['yearly_total'] if row['yearly_total'] else 0.0
        cursor.execute("SELECT SUM(amount) as total FROM dividend_payments")
        row = cursor.fetchone()
        total_all_time = row['total'] if row['total'] else 0.0
        conn.close()
        return {
            "monthly_total": round(monthly_total, 2),
            "yearly_total": round(yearly_total, 2),
            "total_all_time": round(total_all_time, 2)
        }

    def get_dividends_by_ticker(self) -> List[Dict]:
        """Return per-ticker dividend data with fields expected by frontend."""
        conn = get_connection()
        cursor = conn.cursor()
        # Get portfolio shares
        cursor.execute("SELECT ticker, shares FROM portfolio")
        portfolio = {r['ticker']: r['shares'] for r in cursor.fetchall()}
        # Get dividend history grouped by ticker
        cursor.execute("""
            SELECT
                ticker,
                SUM(amount) as total_dividends,
                COUNT(*) as payment_count,
                MAX(payment_date) as last_payment_date,
                MAX(amount) as last_payment_amount,
                AVG(per_share_amount) as avg_per_share
            FROM dividend_payments
            GROUP BY ticker
            ORDER BY total_dividends DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        # Get live yields
        tickers = [r['ticker'] for r in rows]
        live_yields = {}
        if tickers:
            try:
                live_yields = self.get_dividends(tickers)
            except Exception:
                pass
        result = []
        for row in rows:
            t = row['ticker']
            shares = portfolio.get(t, 0)
            yld = live_yields.get(t, {}).get('yield', 0) or 0
            from .market_data_service import get_prices
            try:
                price = get_prices([t]).get(t, 0) or 0
            except Exception:
                price = 0
            annual_amount = price * yld * shares if price and yld else 0
            result.append({
                "ticker": t,
                "yield_pct": round(yld * 100, 2),
                "annual_amount": round(annual_amount, 2),
                "last_payment_date": row['last_payment_date'],
                "last_payment_amount": round(
                    row['last_payment_amount'] or 0, 2
                ),
                "total_dividends": round(row['total_dividends'], 2),
                "payment_count": row['payment_count'],
            })
        return result

    def get_dividend_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ticker: Optional[str] = None
    ) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM dividend_payments WHERE 1=1"
        params = []
        if start_date:
            query += " AND payment_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND payment_date <= ?"
            params.append(end_date)
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        query += " ORDER BY payment_date DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "id": row['id'],
                "ticker": row['ticker'],
                "payment_date": row['payment_date'],
                "amount": round(row['amount'], 2),
                "shares_owned": row['shares_owned'],
                "per_share_amount": round(row['per_share_amount'], 4),
                "reinvested": bool(row['reinvested']),
                "reinvestment_shares": row['reinvestment_shares']
            })
        return result

    def import_historical_dividends(self) -> Dict:
        """Import last 2 years of dividend history from yfinance for all
        portfolio tickers. Skips duplicates by payment_date+ticker."""
        import yfinance as yf
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, shares FROM portfolio")
        holdings = {r['ticker']: r['shares'] for r in cursor.fetchall()}
        imported = 0
        skipped = 0
        for ticker, shares in holdings.items():
            try:
                stock = yf.Ticker(ticker)
                divs = stock.dividends  # pandas Series indexed by date
                if divs is None or len(divs) == 0:
                    continue
                # Only last 2 years
                from datetime import timedelta
                cutoff = datetime.now() - timedelta(days=730)
                recent = divs[divs.index >= cutoff.strftime('%Y-%m-%d')]
                for date, per_share in recent.items():
                    date_str = str(date)[:10]
                    amount = round(float(per_share) * shares, 4)
                    # Check duplicate
                    cursor.execute(
                        "SELECT id FROM dividend_payments "
                        "WHERE ticker=? AND payment_date=?",
                        (ticker, date_str)
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue
                    cursor.execute("""
                        INSERT INTO dividend_payments
                        (ticker, payment_date, amount, shares_owned,
                         per_share_amount, reinvested)
                        VALUES (?, ?, ?, ?, ?, 0)
                    """, (ticker, date_str, amount, shares,
                          float(per_share)))
                    imported += 1
            except Exception:
                continue
        conn.commit()
        conn.close()
        return {"imported": imported, "skipped": skipped}

    def record_manual_dividend(
        self,
        ticker: str,
        payment_date: str,
        per_share_amount: float,
        reinvested: bool = False
    ) -> Dict:
        """Record a single dividend payment manually."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT shares FROM portfolio WHERE ticker=?", (ticker,)
        )
        row = cursor.fetchone()
        shares = row['shares'] if row else 0
        amount = round(per_share_amount * shares, 4)
        cursor.execute("""
            INSERT INTO dividend_payments
            (ticker, payment_date, amount, shares_owned,
             per_share_amount, reinvested)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, payment_date, amount, shares,
              per_share_amount, 1 if reinvested else 0))
        conn.commit()
        conn.close()
        return {
            "ticker": ticker,
            "payment_date": payment_date,
            "amount": amount,
            "shares_owned": shares,
            "per_share_amount": per_share_amount,
            "reinvested": reinvested
        }

    def record_dividend_reinvestment(
        self,
        ticker: str,
        dividend_amount: float,
        reinvestment_price: float
    ) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        shares_purchased = dividend_amount / reinvestment_price
        cursor.execute(
            "SELECT shares FROM portfolio WHERE ticker = ?", (ticker,)
        )
        row = cursor.fetchone()
        current_shares = row['shares'] if row else 0
        cursor.execute("""
            INSERT INTO transactions
            (date, ticker, action, shares, price, total_amount,
             transaction_type, notes)
            VALUES (?, ?, 'BUY', ?, ?, ?, 'DIVIDEND_REINVESTMENT',
            'Automatic dividend reinvestment')
        """, (datetime.now().isoformat(), ticker, shares_purchased,
              reinvestment_price, dividend_amount))
        new_shares = current_shares + shares_purchased
        if current_shares > 0:
            cursor.execute(
                "UPDATE portfolio SET shares=?, last_updated=? "
                "WHERE ticker=?",
                (new_shares, datetime.now().isoformat(), ticker)
            )
        else:
            cursor.execute(
                "INSERT INTO portfolio (ticker, shares, last_updated) "
                "VALUES (?, ?, ?)",
                (ticker, new_shares, datetime.now().isoformat())
            )
        conn.commit()
        conn.close()
        return {
            "ticker": ticker,
            "dividend_amount": round(dividend_amount, 2),
            "reinvestment_price": round(reinvestment_price, 2),
            "shares_purchased": round(shares_purchased, 4),
            "new_total_shares": round(new_shares, 4)
        }

    def get_dividend_chart_data(self, period: str = "12m") -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        days_map = {"1m": 30, "3m": 90, "6m": 180, "12m": 365}
        days = days_map.get(period, 365)
        cursor.execute("""
            SELECT
                strftime('%Y-%m', payment_date) as month,
                SUM(amount) as amount
            FROM dividend_payments
            WHERE payment_date >= date('now', '-' || ? || ' days')
            GROUP BY month
            ORDER BY month
        """, (days,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {"month": row['month'], "amount": round(row['amount'], 2)}
            for row in rows
        ]
