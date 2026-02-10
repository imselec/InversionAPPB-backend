from pathlib import Path
import csv
from typing import List, Dict

BASE_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BASE_DIR / "data" / "portfolio.csv"

def load_portfolio() -> List[Dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"portfolio.csv no encontrado en {CSV_PATH}")

    portfolio = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            portfolio.append({
                "ticker": row["symbol"].upper().strip(),
                "shares": float(row["shares"]),
                "avg_price": float(row.get("price_per_share", 0) or 0),
                "sector": row.get("sector", "").strip(),
                "dividend_yield": float(row.get("dividend_per_share", 0) or 0)
            })
    return portfolio
