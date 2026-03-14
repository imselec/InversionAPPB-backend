"""
Portfolio service for managing portfolio holdings and calculations.
"""
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
from app.database import get_connection
from app.services.market_data_service import get_prices


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTFOLIO_FILE = os.path.join(BASE_DIR, "data", "portfolio.csv")


def load_portfolio_from_db() -> List[Dict]:
    """Load portfolio holdings from database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ticker, shares, avg_price, current_price, last_updated
        FROM portfolio
        ORDER BY ticker
    """)
    
    portfolio = []
    for row in cursor.fetchall():
        portfolio.append({
            "ticker": row["ticker"],
            "shares": row["shares"],
            "avg_price": row["avg_price"],
            "current_price": row["current_price"],
            "last_updated": row["last_updated"]
        })
    
    conn.close()
    return portfolio


def load_portfolio():
    """Load portfolio from database (primary) or CSV (fallback)."""
    # Try database first
    portfolio = load_portfolio_from_db()
    
    if portfolio:
        return portfolio
    
    # Fallback to CSV if database is empty
    portfolio = []
    if not os.path.exists(PORTFOLIO_FILE):
        return portfolio

    with open(PORTFOLIO_FILE, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                shares = float(row["shares"])
            except:
                shares = 0

            portfolio.append({
                "ticker": row["ticker"],
                "shares": shares
            })

    return portfolio


def calculate_allocation(positions: List[Dict], total_value: float) -> List[Dict]:
    """Calculate allocation percentage for each position."""
    for position in positions:
        if total_value > 0:
            position["allocation_pct"] = round(
                (position["value"] / total_value) * 100, 2
            )
        else:
            position["allocation_pct"] = 0
    return positions


def get_portfolio_snapshot():
    """Get current portfolio snapshot with prices and values."""
    portfolio = load_portfolio()
    tickers = [p["ticker"] for p in portfolio]
    prices = get_prices(tickers)

    positions = []
    total_value = 0

    for asset in portfolio:
        ticker = asset["ticker"]
        shares = asset["shares"]
        avg_price = asset.get("avg_price", 0) or 0
        
        price = prices.get(ticker, 0)
        value = shares * price
        total_value += value
        
        # Calculate gain/loss
        cost_basis = shares * avg_price if avg_price > 0 else 0
        gain_loss = value - cost_basis if cost_basis > 0 else 0
        gain_loss_pct = (
            (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
        )

        positions.append({
            "ticker": ticker,
            "shares": shares,
            "price": round(price, 2),
            "value": round(value, 2),
            "avg_price": round(avg_price, 2) if avg_price > 0 else None,
            "cost_basis": round(cost_basis, 2) if cost_basis > 0 else None,
            "gain_loss": round(gain_loss, 2) if cost_basis > 0 else None,
            "gain_loss_pct": round(gain_loss_pct, 2) if cost_basis > 0 else None
        })

    # Calculate allocations
    positions = calculate_allocation(positions, total_value)
    
    # Update current prices in database
    update_current_prices(prices)

    return {
        "total_value": round(total_value, 2),
        "positions": positions,
        "last_updated": datetime.now().isoformat()
    }


def get_dashboard():
    """Get dashboard summary data."""
    snapshot = get_portfolio_snapshot()
    
    # Calculate total gain/loss
    total_invested = sum(
        p.get("cost_basis", 0) or 0 for p in snapshot["positions"]
    )
    total_gain_loss = snapshot["total_value"] - total_invested
    total_gain_loss_pct = (
        (total_gain_loss / total_invested) * 100 if total_invested > 0 else 0
    )

    return {
        "total_value": snapshot["total_value"],
        "total_invested": round(total_invested, 2),
        "total_gain_loss": round(total_gain_loss, 2),
        "total_gain_loss_pct": round(total_gain_loss_pct, 2),
        "positions": snapshot["positions"],
        "last_updated": snapshot["last_updated"]
    }


def get_allocation():
    """Get portfolio allocation percentages."""
    snapshot = get_portfolio_snapshot()
    
    allocations = []
    for position in snapshot["positions"]:
        allocations.append({
            "ticker": position["ticker"],
            "allocation_pct": position["allocation_pct"],
            "value": position["value"]
        })
    
    return {
        "total_value": snapshot["total_value"],
        "allocations": allocations
    }


def get_transaction_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ticker: Optional[str] = None
) -> List[Dict]:
    """Get transaction history with optional filtering."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    if ticker:
        query += " AND ticker = ?"
        params.append(ticker)
    
    query += " ORDER BY date DESC"
    
    cursor.execute(query, params)
    
    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            "id": row["id"],
            "date": row["date"],
            "ticker": row["ticker"],
            "action": row["action"],
            "shares": row["shares"],
            "price": row["price"],
            "total_amount": row["total_amount"],
            "transaction_type": row["transaction_type"],
            "notes": row["notes"]
        })
    
    conn.close()
    return transactions


def record_transaction(
    ticker: str,
    action: str,
    shares: float,
    price: float,
    transaction_type: str = "PURCHASE",
    notes: Optional[str] = None
) -> Dict:
    """Record a new transaction."""
    conn = get_connection()
    cursor = conn.cursor()
    
    total_amount = shares * price
    
    cursor.execute("""
        INSERT INTO transactions 
        (date, ticker, action, shares, price, total_amount, transaction_type, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(),
        ticker,
        action,
        shares,
        price,
        total_amount,
        transaction_type,
        notes
    ))
    
    transaction_id = cursor.lastrowid
    
    # Update portfolio holdings
    if action == "BUY":
        update_portfolio_after_buy(cursor, ticker, shares, price)
    elif action == "SELL":
        update_portfolio_after_sell(cursor, ticker, shares)
    
    conn.commit()
    conn.close()
    
    return {
        "transaction_id": transaction_id,
        "ticker": ticker,
        "action": action,
        "shares": shares,
        "price": price,
        "total_amount": round(total_amount, 2),
        "recorded_at": datetime.now().isoformat()
    }


def update_portfolio_after_buy(cursor, ticker: str, shares: float, price: float):
    """Update portfolio holdings after a buy transaction."""
    # Check if ticker exists in portfolio
    cursor.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing holding
        old_shares = existing["shares"]
        old_avg_price = existing["avg_price"] or 0
        
        new_shares = old_shares + shares
        new_avg_price = (
            (old_shares * old_avg_price + shares * price) / new_shares
        )
        
        cursor.execute("""
            UPDATE portfolio
            SET shares = ?, avg_price = ?, last_updated = ?
            WHERE ticker = ?
        """, (new_shares, new_avg_price, datetime.now(), ticker))
    else:
        # Insert new holding
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, last_updated)
            VALUES (?, ?, ?, ?)
        """, (ticker, shares, price, datetime.now()))


def update_portfolio_after_sell(cursor, ticker: str, shares: float):
    """Update portfolio holdings after a sell transaction."""
    cursor.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker,))
    existing = cursor.fetchone()
    
    if existing:
        new_shares = existing["shares"] - shares
        
        if new_shares <= 0:
            # Remove from portfolio if all shares sold
            cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
        else:
            # Update shares
            cursor.execute("""
                UPDATE portfolio
                SET shares = ?, last_updated = ?
                WHERE ticker = ?
            """, (new_shares, datetime.now(), ticker))


def update_current_prices(prices: Dict[str, float]):
    """Update current prices in database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    for ticker, price in prices.items():
        cursor.execute("""
            UPDATE portfolio
            SET current_price = ?, last_updated = ?
            WHERE ticker = ?
        """, (price, datetime.now(), ticker))
    
    conn.commit()
    conn.close()


def get_cost_basis(ticker: str) -> Optional[float]:
    """Get average cost basis for a ticker."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT avg_price FROM portfolio WHERE ticker = ?
    """, (ticker,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row and row["avg_price"]:
        return row["avg_price"]
    return None
