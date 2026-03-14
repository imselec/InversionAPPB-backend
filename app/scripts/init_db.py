"""
Database initialization script with seed data for InversionAPP.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_connection, init_database
from datetime import datetime


def seed_portfolio():
    """Seed portfolio table with 18 current holdings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Current holdings as of 04/03/26
    holdings = [
        ("AVGO", 1.3792, 150.00),
        ("PG", 1.9549, 165.00),
        ("NEE", 2.4958, 70.00),
        ("JNJ", 1.2209, 160.00),
        ("UPS", 0.5577, 180.00),
        ("TXN", 0.8946, 190.00),
        ("CVX", 1.0876, 145.00),
        ("XOM", 1.0643, 110.00),
        ("ABBV", 0.3574, 175.00),
        ("LMT", 0.2592, 450.00),
        ("O", 1.4255, 60.00),
        ("JPM", 0.7534, 200.00),
        ("DUK", 0.2092, 95.00),
        ("KO", 0.5996, 62.00),
        ("PEP", 0.4824, 170.00),
        ("BLK", 0.1956, 850.00),
        ("LLY", 0.198, 800.00),
        ("RTX", 0.2415, 115.00),
        ("CAT", 0.1099, 350.00),
    ]
    
    for ticker, shares, avg_price in holdings:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, shares, avg_price, avg_price, datetime.now()))
    
    conn.commit()
    print(f"Seeded {len(holdings)} portfolio holdings")
    conn.close()


def seed_settings():
    """Seed user settings with default values."""
    conn = get_connection()
    cursor = conn.cursor()
    
    settings = [
        ("monthly_budget", "300"),
        ("rebalance_threshold_high", "20"),
        ("rebalance_threshold_low", "10"),
        ("auto_refresh_enabled", "true"),
        ("refresh_interval_minutes", "5"),
    ]
    
    for key, value in settings:
        cursor.execute("""
            INSERT OR REPLACE INTO user_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now()))
    
    conn.commit()
    print(f"Seeded {len(settings)} user settings")
    conn.close()


def main():
    """Initialize database and seed with data."""
    print("Initializing database schema...")
    init_database()
    
    print("\nSeeding portfolio data...")
    seed_portfolio()
    
    print("\nSeeding user settings...")
    seed_settings()
    
    print("\n✅ Database initialization complete!")
    print(f"Database location: {Path(__file__).parent.parent.parent / 'inversionapp.db'}")


if __name__ == "__main__":
    main()
