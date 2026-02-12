from pathlib import Path
from typing import List, Dict
import csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PORTFOLIO_FILE = BASE_DIR / "portfolio.csv"


def load_portfolio() -> List[Dict]:
    """
    Lee portfolio.csv bajo demanda.
    No se ejecuta al importar.
    """

    if not PORTFOLIO_FILE.exists():
        return []

    portfolio = []

    try:
        with open(PORTFOLIO_FILE, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                portfolio.append({
                    "ticker": row["ticker"],
                    "shares": float(row["shares"]),
                    "avg_price": float(row["avg_price"])
                })
    except Exception:
        return []

    return portfolio
