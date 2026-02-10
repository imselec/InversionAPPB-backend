import csv
from pathlib import Path

PORTFOLIO_PATH = Path("app/data/portfolio.csv")

def load_portfolio():
    portfolio = []
    with open(PORTFOLIO_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            portfolio.append({
                "ticker": row["ticker"],
                "shares": float(row["shares"]),
                "sector": row["sector"],
                "yield": float(row["yield"]),
                "category": row["category"]  # dividend_growth, income, etc
            })
    return portfolio
