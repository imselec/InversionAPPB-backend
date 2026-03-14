from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
import warnings
import logging
from ..database import get_connection

# Suppress yahooquery warnings and errors
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
                    # Check if summary is an error dict
                    if isinstance(summary, dict) and 'error' not in str(summary).lower():
                        result[t] = {
                            "yield": summary.get("dividendYield", 0),
                            "payout": summary.get("payoutRatio", 0)
                        }
                    else:
                        result[t] = {"yield": 0, "payout": 0}
                except Exception:
                    result[t] = {"yield": 0, "payout": 0}
        except Exception:
            # If entire request fails, return zeros for all tickers
            for t in tickers:
                result[t] = {"yield": 0, "payout": 0}
        return result

    def get_annual_dividend(self, ticker):
        """Obtiene el dividendo anual estimado para un ticker"""
        try:
            dividends = self.get_dividends([ticker])
            dividend_yield = dividends.get(ticker, {}).get("yield", 0)
            from .market_data_service import get_prices
            prices = get_prices([ticker])
            price = prices.get(ticker, 0)
            if price > 0 and dividend_yield > 0:
                annual_dividend = price * dividend_yield
                return annual_dividend
            return 0
        except Exception:
            return 0

    def get_dividend_summary(self) -> Dict:
        """Get monthly and yearly dividend totals"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Monthly total (last 30 days)
        cursor.execute("""
            SELECT SUM(amount) as monthly_total
            FROM dividend_payments
            WHERE payment_date >= date('now', '-30 days')
        """)
        monthly_row = cursor.fetchone()
        monthly_total = monthly_row['monthly_total'] if monthly_row['monthly_total'] else 0.0
        
        # Yearly total (last 365 days)
        cursor.execute("""
            SELECT SUM(amount) as yearly_total
            FROM dividend_payments
            WHERE payment_date >= date('now', '-365 days')
        """)
        yearly_row = cursor.fetchone()
        yearly_total = yearly_row['yearly_total'] if yearly_row['yearly_total'] else 0.0
        
        # Total all time
        cursor.execute("SELECT SUM(amount) as total FROM dividend_payments")
        total_row = cursor.fetchone()
        total_all_time = total_row['total'] if total_row['total'] else 0.0
        
        conn.close()
        
        return {
            "monthly_total": round(monthly_total, 2),
            "yearly_total": round(yearly_total, 2),
            "total_all_time": round(total_all_time, 2)
        }

    def get_dividends_by_ticker(self) -> List[Dict]:
        """Get dividend data per stock"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ticker,
                SUM(amount) as total_dividends,
                COUNT(*) as payment_count,
                MAX(payment_date) as last_payment_date,
                AVG(per_share_amount) as avg_per_share
            FROM dividend_payments
            GROUP BY ticker
            ORDER BY total_dividends DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                "ticker": row['ticker'],
                "total_dividends": round(row['total_dividends'], 2),
                "payment_count": row['payment_count'],
                "last_payment_date": row['last_payment_date'],
                "avg_per_share": round(row['avg_per_share'], 4)
            })
        
        return result

    def get_dividend_history(self, start_date: Optional[str] = None, end_date: Optional[str] = None, ticker: Optional[str] = None) -> List[Dict]:
        """Get historical dividend payments with optional filtering"""
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

    def record_dividend_reinvestment(self, ticker: str, dividend_amount: float, reinvestment_price: float) -> Dict:
        """Record a dividend reinvestment transaction"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calculate shares purchased
        shares_purchased = dividend_amount / reinvestment_price
        
        # Get current shares owned
        cursor.execute("SELECT shares FROM portfolio WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        current_shares = row['shares'] if row else 0
        
        # Record transaction
        cursor.execute("""
            INSERT INTO transactions (date, ticker, action, shares, price, total_amount, transaction_type, notes)
            VALUES (?, ?, 'BUY', ?, ?, ?, 'DIVIDEND_REINVESTMENT', 'Automatic dividend reinvestment')
        """, (datetime.now().isoformat(), ticker, shares_purchased, reinvestment_price, dividend_amount))
        
        # Update portfolio
        new_shares = current_shares + shares_purchased
        if current_shares > 0:
            cursor.execute("""
                UPDATE portfolio 
                SET shares = ?, last_updated = ?
                WHERE ticker = ?
            """, (new_shares, datetime.now().isoformat(), ticker))
        else:
            cursor.execute("""
                INSERT INTO portfolio (ticker, shares, last_updated)
                VALUES (?, ?, ?)
            """, (ticker, new_shares, datetime.now().isoformat()))
        
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
        """Get dividend income data for visualization"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Determine date range based on period
        if period == "1m":
            days = 30
        elif period == "3m":
            days = 90
        elif period == "6m":
            days = 180
        elif period == "12m":
            days = 365
        else:
            days = 365
        
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', payment_date) as month,
                SUM(amount) as total
            FROM dividend_payments
            WHERE payment_date >= date('now', '-' || ? || ' days')
            GROUP BY month
            ORDER BY month
        """, (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                "month": row['month'],
                "total": round(row['total'], 2)
            })
        
        return result
