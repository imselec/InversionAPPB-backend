"""
Database configuration and schema for InversionAPP.
"""
import sqlite3
from pathlib import Path
from datetime import datetime


DATABASE_PATH = Path(__file__).parent.parent / "inversionapp.db"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database schema with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Portfolio table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(10) NOT NULL,
            shares REAL NOT NULL,
            avg_price REAL,
            current_price REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_ticker ON portfolio(ticker)")
    
    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP NOT NULL,
            ticker VARCHAR(10) NOT NULL,
            action VARCHAR(10) NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            total_amount REAL NOT NULL,
            transaction_type VARCHAR(50),
            notes TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    
    # Dividend payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dividend_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(10) NOT NULL,
            payment_date TIMESTAMP NOT NULL,
            amount REAL NOT NULL,
            shares_owned REAL NOT NULL,
            per_share_amount REAL NOT NULL,
            reinvested BOOLEAN DEFAULT FALSE,
            reinvestment_shares REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dividend_ticker ON dividend_payments(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dividend_date ON dividend_payments(payment_date)")
    
    # Recommendation runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            budget REAL NOT NULL,
            total_allocated REAL NOT NULL,
            portfolio_value REAL NOT NULL
        )
    """)
    
    # Recommendation items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            ticker VARCHAR(10) NOT NULL,
            action VARCHAR(10) NOT NULL,
            shares REAL,
            price REAL NOT NULL,
            total_cost REAL,
            score REAL NOT NULL,
            reasoning TEXT,
            priority INTEGER,
            FOREIGN KEY (run_id) REFERENCES recommendation_runs(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_run ON recommendation_items(run_id)")
    
    # Portfolio snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP NOT NULL,
            total_value REAL NOT NULL,
            total_invested REAL NOT NULL,
            total_gain_loss REAL NOT NULL,
            total_return_pct REAL NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_date ON portfolio_snapshots(date)")
    
    # User settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key VARCHAR(100) NOT NULL UNIQUE,
            setting_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Rebalancing alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rebalancing_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(10) NOT NULL,
            current_allocation REAL NOT NULL,
            target_allocation REAL NOT NULL,
            deviation REAL NOT NULL,
            alert_type VARCHAR(20) NOT NULL,
            severity VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT FALSE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rebalancing_ticker ON rebalancing_alerts(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rebalancing_resolved ON rebalancing_alerts(resolved)")
    
    # Alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type VARCHAR(50) NOT NULL,
            ticker VARCHAR(10),
            target_price REAL,
            enabled BOOLEAN DEFAULT TRUE,
            last_triggered TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON alerts(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_enabled ON alerts(enabled)")
    
    # Notification history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_id INTEGER,
            alert_type VARCHAR(50) NOT NULL,
            ticker VARCHAR(10),
            message TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivered BOOLEAN DEFAULT FALSE,
            read BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (alert_id) REFERENCES alerts(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_user ON notification_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_sent ON notification_history(sent_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_read ON notification_history(read)")
    
    # Watchlist table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker VARCHAR(10) NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            target_price REAL,
            UNIQUE(user_id, ticker)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON watchlist(ticker)")
    
    # Device tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_token VARCHAR(255) NOT NULL UNIQUE,
            platform VARCHAR(20) NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            active BOOLEAN DEFAULT TRUE,
            failure_count INTEGER DEFAULT 0
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_user ON device_tokens(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_token ON device_tokens(device_token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_active ON device_tokens(active)")
    
    conn.commit()
    conn.close()
    
    print("Database schema initialized successfully!")


if __name__ == "__main__":
    init_database()
