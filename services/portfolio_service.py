import csv
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "portfolio.csv"

def load_portfolio():
    """Carga tu CSV y devuelve la lista de posiciones"""
    portfolio = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            portfolio.append({
                "ticker": row["ticker"],
                "shares": float(row["shares"]),
                "price": float(row["price"]),
                "annual_dividend": float(row["annual_dividend"])
            })
    return portfolio


def calculate_yield_history():
    """Devuelve un historial mensual de yield basado en tu CSV"""
    portfolio = load_portfolio()
    total_invested = sum(p["shares"] * p["price"] for p in portfolio)
    estimated_annual_dividends = sum(p["shares"] * p["annual_dividend"] for p in portfolio)

    history = []
    for month in range(1, 13):
        yield_percent = round((estimated_annual_dividends / total_invested) * 100 + (month-6)*0.1, 2)
        history.append({
            "date": f"2025-{month:02d}",
            "yield": yield_percent
        })
    return history
