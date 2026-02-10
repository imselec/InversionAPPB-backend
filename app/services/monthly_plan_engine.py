# app/services/monthly_plan_engine.py
from typing import List, Dict

def build_monthly_plan(amount: float = 200) -> Dict:
    """
    Genera un plan mensual de inversiones basado en el monto y la estrategia.
    Devuelve un diccionario con compras proyectadas y estado de la cartera.
    """
    # Lista de compras simuladas
    purchases = [
        {
            "ticker": "VYM",
            "amount_usd": 100,
            "shares_to_buy": 0.85,
            "reason": "High yield diversified ETF"
        },
        {
            "ticker": "JNJ",
            "amount_usd": 100,
            "shares_to_buy": 0.62,
            "reason": "Dividend aristocrat, healthcare sector"
        }
    ]

    # Cálculo de portfolio proyectado (simulado)
    projected_portfolio = [
        {"symbol": "AAPL", "shares": 10, "total_value": 1800},
        {"symbol": "JNJ", "shares": 5.62, "total_value": 899.2},
        {"symbol": "VYM", "shares": 0.85, "total_value": 100},
    ]

    # Retorno final como diccionario
    return {
        "investment_amount": amount,
        "strategy": "dividend_growth",
        "purchases": purchases,
        "projected_portfolio": projected_portfolio
    }
