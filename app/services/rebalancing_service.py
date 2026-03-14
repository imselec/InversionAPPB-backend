"""
Rebalancing service for InversionAPP.
"""
from datetime import datetime
from typing import Dict, List
from ..database import get_connection
from .market_data_service import get_prices


class RebalancingService:
    
    OVERWEIGHT_THRESHOLD = 0.20  # 20% above target
    UNDERWEIGHT_THRESHOLD = 0.10  # 10% below target
    
    def check_balance_status(self) -> Dict:
        """
        Check current portfolio balance status.
        Returns allocation percentages and deviations from target.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get portfolio holdings
        cursor.execute("SELECT ticker, shares FROM portfolio WHERE shares > 0")
        holdings = cursor.fetchall()
        
        if not holdings:
            conn.close()
            return {"message": "No portfolio holdings found", "allocations": []}
        
        # Get current prices
        tickers = [h['ticker'] for h in holdings]
        prices = get_prices(tickers)
        
        # Calculate total portfolio value
        total_value = 0
        holdings_data = []
        
        for holding in holdings:
            ticker = holding['ticker']
            shares = holding['shares']
            price = prices.get(ticker, 0)
            value = shares * price
            total_value += value
            holdings_data.append({
                "ticker": ticker,
                "shares": shares,
                "price": price,
                "value": value
            })
        
        # Calculate target allocation (equal weight)
        stock_count = len(holdings_data)
        target_allocation = 100.0 / stock_count if stock_count > 0 else 0
        
        # Calculate current allocations and deviations
        allocations = []
        for holding in holdings_data:
            current_allocation = (holding['value'] / total_value * 100) if total_value > 0 else 0
            deviation = current_allocation - target_allocation
            deviation_pct = (deviation / target_allocation) if target_allocation > 0 else 0
            
            # Determine status
            if deviation_pct > self.OVERWEIGHT_THRESHOLD:
                status = "overweight"
                severity = "high"
            elif deviation_pct < -self.UNDERWEIGHT_THRESHOLD:
                status = "underweight"
                severity = "medium"
            else:
                status = "balanced"
                severity = "low"
            
            allocations.append({
                "ticker": holding['ticker'],
                "current_value": round(holding['value'], 2),
                "current_allocation": round(current_allocation, 2),
                "target_allocation": round(target_allocation, 2),
                "deviation": round(deviation, 2),
                "deviation_pct": round(deviation_pct * 100, 2),
                "status": status,
                "severity": severity
            })
        
        conn.close()
        
        return {
            "total_value": round(total_value, 2),
            "target_allocation": round(target_allocation, 2),
            "stock_count": stock_count,
            "allocations": sorted(allocations, key=lambda x: abs(x['deviation']), reverse=True)
        }
    
    def generate_rebalancing_alerts(self) -> List[Dict]:
        """
        Generate and store rebalancing alerts for imbalanced positions.
        """
        balance_status = self.check_balance_status()
        
        if "message" in balance_status:
            return []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clear old unresolved alerts
        cursor.execute("DELETE FROM rebalancing_alerts WHERE resolved = FALSE")
        
        alerts = []
        for allocation in balance_status['allocations']:
            if allocation['status'] != 'balanced':
                # Determine alert type
                if allocation['status'] == 'overweight':
                    alert_type = 'OVERWEIGHT'
                else:
                    alert_type = 'UNDERWEIGHT'
                
                # Insert alert
                cursor.execute("""
                    INSERT INTO rebalancing_alerts 
                    (ticker, current_allocation, target_allocation, deviation, alert_type, severity, created_at, resolved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, FALSE)
                """, (
                    allocation['ticker'],
                    allocation['current_allocation'],
                    allocation['target_allocation'],
                    allocation['deviation'],
                    alert_type,
                    allocation['severity'],
                    datetime.now().isoformat()
                ))
                
                alerts.append({
                    "ticker": allocation['ticker'],
                    "alert_type": alert_type,
                    "current_allocation": allocation['current_allocation'],
                    "target_allocation": allocation['target_allocation'],
                    "deviation": allocation['deviation'],
                    "severity": allocation['severity']
                })
        
        conn.commit()
        conn.close()
        
        return alerts
    
    def get_rebalancing_recommendations(self) -> List[Dict]:
        """
        Generate specific trade recommendations to rebalance portfolio.
        """
        balance_status = self.check_balance_status()
        
        if "message" in balance_status:
            return []
        
        total_value = balance_status['total_value']
        target_allocation = balance_status['target_allocation']
        
        recommendations = []
        
        for allocation in balance_status['allocations']:
            if allocation['status'] == 'balanced':
                continue
            
            ticker = allocation['ticker']
            current_value = allocation['current_value']
            target_value = total_value * (target_allocation / 100)
            difference = target_value - current_value
            
            if allocation['status'] == 'overweight':
                # Recommend selling
                shares_to_sell = abs(difference) / allocation['current_value'] * allocation['current_value'] / get_prices([ticker]).get(ticker, 1)
                recommendations.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "current_allocation": allocation['current_allocation'],
                    "target_allocation": target_allocation,
                    "value_difference": round(difference, 2),
                    "shares": round(shares_to_sell, 4),
                    "reasoning": f"Reduce {ticker} position by ${abs(difference):.2f} to reach target allocation"
                })
            else:
                # Recommend buying
                price = get_prices([ticker]).get(ticker, 0)
                shares_to_buy = abs(difference) / price if price > 0 else 0
                recommendations.append({
                    "ticker": ticker,
                    "action": "BUY",
                    "current_allocation": allocation['current_allocation'],
                    "target_allocation": target_allocation,
                    "value_difference": round(difference, 2),
                    "shares": round(shares_to_buy, 4),
                    "reasoning": f"Increase {ticker} position by ${abs(difference):.2f} to reach target allocation"
                })
        
        return recommendations
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active (unresolved) rebalancing alerts"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM rebalancing_alerts
            WHERE resolved = FALSE
            ORDER BY severity DESC, ABS(deviation) DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            alerts.append({
                "id": row['id'],
                "ticker": row['ticker'],
                "alert_type": row['alert_type'],
                "current_allocation": round(row['current_allocation'], 2),
                "target_allocation": round(row['target_allocation'], 2),
                "deviation": round(row['deviation'], 2),
                "severity": row['severity'],
                "created_at": row['created_at']
            })
        
        return alerts
