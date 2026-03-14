"""
Analytics service for portfolio performance metrics.
"""
from typing import Dict, List
from datetime import datetime
from app.database import get_connection
from app.services.market_data_service import get_prices
import math


def calculate_total_return() -> Dict:
    """
    Calculate total return percentage since inception.
    Returns: {total_invested, current_value, total_return, total_return_pct}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate total invested from buy transactions
    cursor.execute("""
        SELECT SUM(total_amount) as total_invested
        FROM transactions
        WHERE action = 'buy'
    """)
    result = cursor.fetchone()
    total_invested = result['total_invested'] if result['total_invested'] else 0
    
    # Calculate current portfolio value
    cursor.execute("SELECT ticker, shares FROM portfolio WHERE shares > 0")
    holdings = cursor.fetchall()
    
    if not holdings:
        conn.close()
        return {
            "total_invested": 0,
            "current_value": 0,
            "total_return": 0,
            "total_return_pct": 0
        }
    
    tickers = [h['ticker'] for h in holdings]
    prices = get_prices(tickers)
    
    current_value = sum(
        h['shares'] * prices.get(h['ticker'], 0)
        for h in holdings
    )
    
    total_return = current_value - total_invested
    total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0
    
    conn.close()
    
    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2)
    }


def calculate_annualized_return() -> Dict:
    """
    Calculate annualized return rate.
    Returns: {annualized_return_pct, years_invested, days_invested}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get first transaction date
    cursor.execute("""
        SELECT MIN(date) as first_date
        FROM transactions
        WHERE action = 'buy'
    """)
    result = cursor.fetchone()
    
    if not result or not result['first_date']:
        conn.close()
        return {
            "annualized_return_pct": 0,
            "years_invested": 0,
            "days_invested": 0
        }
    
    first_date = datetime.fromisoformat(result['first_date'])
    days_invested = (datetime.now() - first_date).days
    years_invested = days_invested / 365.25
    
    if years_invested < 0.01:  # Less than ~4 days
        conn.close()
        return {
            "annualized_return_pct": 0,
            "years_invested": round(years_invested, 2),
            "days_invested": days_invested
        }
    
    # Get total return
    total_return_data = calculate_total_return()
    total_invested = total_return_data['total_invested']
    current_value = total_return_data['current_value']
    
    if total_invested <= 0:
        conn.close()
        return {
            "annualized_return_pct": 0,
            "years_invested": round(years_invested, 2),
            "days_invested": days_invested
        }
    
    # Annualized return = ((current_value / total_invested) ^ (1 / years)) - 1
    annualized_return = (math.pow(current_value / total_invested, 1 / years_invested) - 1) * 100
    
    conn.close()
    
    return {
        "annualized_return_pct": round(annualized_return, 2),
        "years_invested": round(years_invested, 2),
        "days_invested": days_invested
    }


def calculate_portfolio_dividend_yield() -> Dict:
    """
    Calculate portfolio dividend yield.
    Returns: {portfolio_yield, total_annual_dividends, current_value}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current holdings
    cursor.execute("SELECT ticker, shares FROM portfolio WHERE shares > 0")
    holdings = cursor.fetchall()
    
    if not holdings:
        conn.close()
        return {
            "portfolio_yield": 0,
            "total_annual_dividends": 0,
            "current_value": 0
        }
    
    tickers = [h['ticker'] for h in holdings]
    prices = get_prices(tickers)
    
    # Calculate current portfolio value
    current_value = sum(
        h['shares'] * prices.get(h['ticker'], 0)
        for h in holdings
    )
    
    # Calculate total annual dividends
    total_annual_dividends = 0
    for holding in holdings:
        ticker = holding['ticker']
        shares = holding['shares']
        
        # Get dividend per share from database or fetch from API
        cursor.execute("""
            SELECT SUM(per_share_amount) / COUNT(*) as avg_dividend
            FROM dividend_payments
            WHERE ticker = ?
            AND payment_date >= date('now', '-1 year')
        """, (ticker,))
        result = cursor.fetchone()
        
        if result and result['avg_dividend']:
            # Estimate annual dividend (multiply by 4 for quarterly)
            annual_dividend = result['avg_dividend'] * 4 * shares
            total_annual_dividends += annual_dividend
    
    portfolio_yield = (total_annual_dividends / current_value * 100) if current_value > 0 else 0
    
    conn.close()
    
    return {
        "portfolio_yield": round(portfolio_yield, 2),
        "total_annual_dividends": round(total_annual_dividends, 2),
        "current_value": round(current_value, 2)
    }


def calculate_per_ticker_returns() -> List[Dict]:
    """
    Calculate return breakdown per ticker.
    Returns: List of {ticker, shares, cost_basis, current_value, gain_loss, return_pct}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current holdings
    cursor.execute("SELECT ticker, shares, avg_price FROM portfolio WHERE shares > 0")
    holdings = cursor.fetchall()
    
    if not holdings:
        conn.close()
        return []
    
    tickers = [h['ticker'] for h in holdings]
    prices = get_prices(tickers)
    
    returns = []
    for holding in holdings:
        ticker = holding['ticker']
        shares = holding['shares']
        avg_price = holding['avg_price'] if holding['avg_price'] else 0
        current_price = prices.get(ticker, 0)
        
        cost_basis = avg_price * shares
        current_value = current_price * shares
        gain_loss = current_value - cost_basis
        return_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
        
        returns.append({
            "ticker": ticker,
            "shares": round(shares, 4),
            "avg_price": round(avg_price, 2),
            "current_price": round(current_price, 2),
            "cost_basis": round(cost_basis, 2),
            "current_value": round(current_value, 2),
            "gain_loss": round(gain_loss, 2),
            "return_pct": round(return_pct, 2)
        })
    
    conn.close()
    
    return returns


def calculate_portfolio_volatility() -> Dict:
    """
    Calculate portfolio volatility (standard deviation of returns).
    Returns: {volatility, period_days}
    """
    import yfinance as yf
    import numpy as np
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current holdings
    cursor.execute("SELECT ticker, shares FROM portfolio WHERE shares > 0")
    holdings = cursor.fetchall()
    
    if not holdings:
        conn.close()
        return {
            "volatility": 0,
            "period_days": 0
        }
    
    tickers = [h['ticker'] for h in holdings]
    prices = get_prices(tickers)
    
    # Calculate portfolio weights
    total_value = sum(h['shares'] * prices.get(h['ticker'], 0) for h in holdings)
    weights = {}
    for holding in holdings:
        ticker = holding['ticker']
        value = holding['shares'] * prices.get(ticker, 0)
        weights[ticker] = value / total_value if total_value > 0 else 0
    
    # Fetch historical data (252 trading days = 1 year)
    try:
        historical_data = yf.download(
            tickers=tickers,
            period="1y",
            interval="1d",
            progress=False,
            threads=False
        )
        
        if len(tickers) == 1:
            returns = historical_data["Close"].pct_change().dropna()
            daily_returns = returns.values
        else:
            returns = historical_data["Close"].pct_change().dropna()
            # Calculate weighted portfolio returns
            daily_returns = []
            for idx in range(len(returns)):
                portfolio_return = sum(
                    returns.iloc[idx][ticker] * weights.get(ticker, 0)
                    for ticker in tickers
                    if ticker in returns.columns
                )
                daily_returns.append(portfolio_return)
        
        # Calculate standard deviation and annualize
        if len(daily_returns) > 0:
            daily_std = np.std(daily_returns)
            annual_volatility = daily_std * math.sqrt(252) * 100
        else:
            annual_volatility = 0
        
        period_days = len(daily_returns)
    
    except Exception as e:
        print(f"Error calculating volatility: {e}")
        annual_volatility = 0
        period_days = 0
    
    conn.close()
    
    return {
        "volatility": round(annual_volatility, 2),
        "period_days": period_days
    }


def calculate_sp500_comparison() -> Dict:
    """
    Compare portfolio performance vs S&P 500.
    Returns: {portfolio_return, sp500_return, alpha, period}
    """
    import yfinance as yf
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get first transaction date
    cursor.execute("""
        SELECT MIN(date) as first_date
        FROM transactions
        WHERE action = 'buy'
    """)
    result = cursor.fetchone()
    
    if not result or not result['first_date']:
        conn.close()
        return {
            "portfolio_return": 0,
            "sp500_return": 0,
            "alpha": 0,
            "period": "N/A"
        }
    
    first_date = datetime.fromisoformat(result['first_date'])
    
    # Get portfolio return
    total_return_data = calculate_total_return()
    portfolio_return = total_return_data['total_return_pct']
    
    # Fetch S&P 500 data
    try:
        sp500 = yf.Ticker("^GSPC")
        historical = sp500.history(start=first_date, end=datetime.now())
        
        if len(historical) >= 2:
            start_price = historical['Close'].iloc[0]
            end_price = historical['Close'].iloc[-1]
            sp500_return = ((end_price - start_price) / start_price) * 100
        else:
            sp500_return = 0
    
    except Exception as e:
        print(f"Error fetching S&P 500 data: {e}")
        sp500_return = 0
    
    alpha = portfolio_return - sp500_return
    
    days = (datetime.now() - first_date).days
    period = f"{days} days"
    
    conn.close()
    
    return {
        "portfolio_return": round(portfolio_return, 2),
        "sp500_return": round(sp500_return, 2),
        "alpha": round(alpha, 2),
        "period": period
    }
