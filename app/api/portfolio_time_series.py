from fastapi import APIRouter
import pandas as pd
from datetime import datetime

router = APIRouter()

CSV_PATH = "./portfolio.csv"

@router.get("/time-series")
def portfolio_time_series():
    # Demo: genera series mensuales a partir de holdings actuales
    df = pd.read_csv(CSV_PATH)
    snapshots = []
    for i in range(6):
        date = (datetime.now().replace(day=1) - pd.DateOffset(months=i)).strftime("%Y-%m-01")
        total_invested = (df["shares"] * df["price_per_share"]).sum()
        est_dividends = (df["shares"] * df["dividend_per_share"]).sum()
        avg_yield = (est_dividends / total_invested * 100) if total_invested else 0
        snapshots.append({
            "date": date,
            "estimated_annual_dividends": round(est_dividends, 2),
            "total_invested": round(total_invested, 2),
            "average_yield": round(avg_yield, 2)
        })
    return snapshots[::-1]  # cronológico
