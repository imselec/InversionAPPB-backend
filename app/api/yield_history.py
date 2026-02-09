from fastapi import APIRouter
import pandas as pd
from datetime import datetime
import os

router = APIRouter()
CSV_PATH = os.path.join(os.path.dirname(__file__), "../../portfolio.csv")

@router.get("/yield-history")
def yield_history():
    df = pd.read_csv(CSV_PATH)
    total_value = (df["shares"] * df["price_per_share"]).sum()
    est_dividends = (df["shares"] * df["dividend_per_share"]).sum()
    avg_yield = (est_dividends / total_value * 100) if total_value else 0
    return [
        {"date": datetime.now().strftime("%Y-%m-%d"), "yield": round(avg_yield, 2)}
    ]
