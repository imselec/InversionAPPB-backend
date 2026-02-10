from typing import List, Dict
from app.core.history_loader import load_price_history, load_dividends
from app.core.portfolio_loader import load_portfolio
from app.core.config import PLAN_MENSUAL_USD, RESTRICTED_ES, REPLACEMENTS_ES

def dynamic_score(asset: Dict, price_history: Dict[str, List[float]], dividends: Dict[str, float]) -> float:
    ticker = asset["ticker"]
    
    # Dividend yield dinámico (total últimos 12 meses / precio actual)
    dividend = dividends.get(ticker, 0)
    avg_price = asset.get("avg_price", 1)
    dy_score = min(dividend / avg_price, 1.0)

    # Trend de precio (últimos 5 días)
    prices = price_history.get(ticker, [])
    trend_score = 0.5
    if len(prices) >= 5:
        trend = (prices[-1] - prices[-5]) / prices[-5]  # subida o bajada %
        # Bajada => más atractivo (compra)
        trend_score = max(min(0.5 - trend, 1.0), 0.0)

    # Sector fijo (opcional, se puede incluir)
    sector_score = 0.5  # si quieres, se puede ponderar igual que antes

    # Score final ponderado
    score = 0.6 * dy_score + 0.4 * trend_score
    return score

def calculate_monthly_allocation_dynamic(country="ES") -> list[dict]:
    # tu código de scoring dinámico, reemplazos y buy_signal
    ...
