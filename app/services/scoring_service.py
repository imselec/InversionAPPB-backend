from typing import List, Dict
from app.core.portfolio_loader import load_portfolio

PLAN_MENSUAL_USD = 200

def calculate_monthly_allocation() -> List[Dict]:
    portfolio = load_portfolio()

    weight = 1 / len(portfolio)

    results = []
    for asset in portfolio:
        allocation = PLAN_MENSUAL_USD * weight

        results.append({
            "ticker": asset["ticker"],
            "weight": round(weight, 3),
            "allocation_usd": round(allocation, 2),
            "shares_to_buy": 0,
            "buy_signal": True
        })

    return results
