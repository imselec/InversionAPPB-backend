"""
Settings service for InversionAPP.
"""
from datetime import datetime
from typing import Dict, Optional
from ..database import get_connection


class SettingsService:
    
    def get_monthly_budget(self) -> float:
        """Get the current monthly investment budget"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT setting_value FROM user_settings
            WHERE setting_key = 'monthly_budget'
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return float(row['setting_value'])
        return 300.0  # Default budget
    
    def update_monthly_budget(self, budget: float) -> Dict:
        """
        Update the monthly investment budget.
        Validates minimum budget of $50.
        """
        if budget < 50:
            raise ValueError("Monthly budget must be at least $50")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if setting exists
        cursor.execute("""
            SELECT id FROM user_settings
            WHERE setting_key = 'monthly_budget'
        """)
        
        row = cursor.fetchone()
        
        if row:
            # Update existing
            cursor.execute("""
                UPDATE user_settings
                SET setting_value = ?, updated_at = ?
                WHERE setting_key = 'monthly_budget'
            """, (str(budget), datetime.now().isoformat()))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO user_settings (setting_key, setting_value, updated_at)
                VALUES ('monthly_budget', ?, ?)
            """, (str(budget), datetime.now().isoformat()))
        
        # Record budget change in transactions for history
        cursor.execute("""
            INSERT INTO transactions (date, ticker, action, shares, price, total_amount, transaction_type, notes)
            VALUES (?, 'SYSTEM', 'SETTING', 0, 0, ?, 'BUDGET_CHANGE', ?)
        """, (datetime.now().isoformat(), budget, f"Monthly budget updated to ${budget}"))
        
        conn.commit()
        conn.close()
        
        return {
            "monthly_budget": budget,
            "updated_at": datetime.now().isoformat(),
            "message": "Budget updated successfully"
        }
    
    def get_allocation_targets(self) -> Dict:
        """Get custom allocation targets"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT setting_value FROM user_settings
            WHERE setting_key = 'allocation_targets'
        """)
        
        row = cursor.fetchone()
        
        if row and row['setting_value']:
            import json
            try:
                conn.close()
                return json.loads(row['setting_value'])
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, fall through to default
                pass
        
        conn.close()
        
        # Default: equal allocation
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) as count FROM portfolio")
        count_row = cursor2.fetchone()
        conn2.close()
        
        stock_count = count_row['count'] if count_row else 18
        default_allocation = 100.0 / stock_count if stock_count > 0 else 5.56
        
        return {
            "target_type": "equal",
            "target_percentage": round(default_allocation, 2)
        }
    
    def update_allocation_targets(self, targets: Dict) -> Dict:
        """Update custom allocation targets"""
        import json
        
        conn = get_connection()
        cursor = conn.cursor()
        
        targets_json = json.dumps(targets)
        
        # Check if setting exists
        cursor.execute("""
            SELECT id FROM user_settings
            WHERE setting_key = 'allocation_targets'
        """)
        
        row = cursor.fetchone()
        
        if row:
            # Update existing
            cursor.execute("""
                UPDATE user_settings
                SET setting_value = ?, updated_at = ?
                WHERE setting_key = 'allocation_targets'
            """, (targets_json, datetime.now().isoformat()))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO user_settings (setting_key, setting_value, updated_at)
                VALUES ('allocation_targets', ?, ?)
            """, (targets_json, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return {
            "allocation_targets": targets,
            "updated_at": datetime.now().isoformat(),
            "message": "Allocation targets updated successfully"
        }
    
    def get_budget_change_history(self, limit: int = 10) -> list:
        """Get history of budget changes"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, total_amount, notes
            FROM transactions
            WHERE transaction_type = 'BUDGET_CHANGE'
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "date": row['date'],
                "new_budget": row['total_amount'],
                "notes": row['notes']
            })
        
        return history
