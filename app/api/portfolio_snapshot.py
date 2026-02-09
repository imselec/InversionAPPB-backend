from fastapi import APIRouter
import pandas as pd
import json
from datetime import datetime
import os

router = APIRouter()

CSV_PATH = os.path.join(os.path.dirname(__file__), "../../portfolio.csv")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../config.json")

@router.get("/snapshot")
def portfolio_snapshot():
    df = pd.read_csv(CSV_PATH)
    
    total_positions = len(df)
    total_value = (df["shares"] * df["price_per_share"]).sum()
    estimated_annual_dividends = (df["shares"] * df["dividend_per_share"]).sum()
    average_yield = (estimated_annual_dividends / total_value * 100) if total_value else 0

    monthly_budget = 200
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
            monthly_budget = cfg.get("monthly_investment", 200)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "monthly_budget": monthly_budget,
        "total_positions": total_positions,
        "estimated_annual_dividends": round(estimated_annual_dividends, 2),
        "average_yield": round(average_yield, 2)
    }

