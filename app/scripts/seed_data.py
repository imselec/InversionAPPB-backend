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
    """Seed portfolio from CSV. Only inserts tickers not already in DB.
    CSV is updated by the app when user edits holdings, so it acts as
    persistent storage across Render restarts."""
    import csv as csv_module
    import os
    conn = get_connection()
    cursor = conn.cursor()

    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "data", "portfolio.csv"
    )

    holdings = []
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            reader = csv_module.DictReader(f)
            for row in reader:
                try:
                    ticker = row["ticker"].strip().upper()
                    shares = float(row["shares"])
                    avg_price = float(row.get("avg_price", "") or 0) or None
                    holdings.append((ticker, shares, avg_price))
                except (ValueError, KeyError):
                    continue

    if not holdings:
        # Fallback hardcoded defaults
        holdings = [
            ("AVGO", 1.3792, None), ("PG", 1.9549, None),
            ("NEE", 2.4958, None), ("JNJ", 1.2209, None),
            ("UPS", 0.5577, None), ("TXN", 0.8946, None),
            ("CVX", 1.0876, None), ("XOM", 1.0643, None),
            ("ABBV", 0.3574, None), ("LMT", 0.2592, None),
            ("O", 1.4255, None), ("JPM", 0.7534, None),
            ("DUK", 0.2092, None), ("KO", 0.5996, None),
            ("PEP", 0.4824, None), ("BLK", 0.1956, None),
            ("LLY", 0.198, None), ("RTX", 0.2415, None),
            ("CAT", 0.1099, None),
        ]

    inserted = 0
    for ticker, shares, avg_price in holdings:
        cursor.execute("SELECT id FROM portfolio WHERE ticker = ?", (ticker,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO portfolio (ticker, shares, avg_price, current_price, last_updated)
                VALUES (?, ?, ?, NULL, ?)
            """, (ticker, shares, avg_price, datetime.now()))
            inserted += 1

    conn.commit()
    print(f"Portfolio seed: {inserted} new tickers inserted, {len(holdings)-inserted} already existed.")
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


def seed_all():
    """Run all seed functions. Safe to call on every startup."""
    seed_portfolio()
    seed_settings()


def main():
    """Run all seed functions."""
    print("Starting database seeding...")
    seed_all()
    print("Database seeding completed!")


if __name__ == "__main__":
    main()
