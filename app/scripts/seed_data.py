"""
Seed data script for InversionAPP database.
Populates initial portfolio holdings and default settings.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_connection
from datetime import datetime


def seed_portfolio():
    """Seed portfolio with 18 current holdings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Current holdings as of 04/03/26
    holdings = [
        ("AVGO", 1.3792),
        ("PG", 1.9549),
        ("NEE", 2.4958),
        ("JNJ", 1.2209),
        ("UPS", 0.5577),
        ("TXN", 0.8946),
        ("CVX", 1.0876),
        ("XOM", 1.0643),
        ("ABBV", 0.3574),
        ("LMT", 0.2592),
        ("O", 1.4255),
        ("JPM", 0.7534),
        ("DUK", 0.2092),
        ("KO", 0.5996),
        ("PEP", 0.4824),
        ("BLK", 0.1956),
        ("LLY", 0.198),
        ("RTX", 0.2415),
        ("CAT", 0.1099),
    ]
    
    # Check if portfolio already has data
    cursor.execute("SELECT COUNT(*) FROM portfolio")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Portfolio already has {count} holdings. Skipping seed.")
        conn.close()
        return
    
    # Insert holdings
    for ticker, shares in holdings:
        cursor.execute("""
            INSERT INTO portfolio (ticker, shares, avg_price, current_price, last_updated)
            VALUES (?, ?, NULL, NULL, ?)
        """, (ticker, shares, datetime.now()))
    
    conn.commit()
    print(f"Seeded {len(holdings)} portfolio holdings successfully!")
    conn.close()


def seed_settings():
    """Seed default user settings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if settings already exist
    cursor.execute("SELECT COUNT(*) FROM user_settings")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Settings already exist ({count} entries). Skipping seed.")
        conn.close()
        return
    
    # Default settings
    settings = [
        ("monthly_budget", "300"),
        ("rebalance_threshold_high", "20"),
        ("rebalance_threshold_low", "10"),
        ("auto_refresh_enabled", "true"),
        ("refresh_interval_minutes", "5"),
    ]
    
    for key, value in settings:
        cursor.execute("""
            INSERT INTO user_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now()))
    
    conn.commit()
    print(f"Seeded {len(settings)} default settings successfully!")
    conn.close()


def main():
    """Run all seed functions."""
    print("Starting database seeding...")
    seed_portfolio()
    seed_settings()
    print("Database seeding completed!")


if __name__ == "__main__":
    main()
