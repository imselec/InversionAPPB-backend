from fastapi import APIRouter
import pandas as pd
import os

router = APIRouter()
CSV_PATH = os.path.join(os.path.dirname(__file__), "../../portfolio.csv")

@router.get("/dividends-by-asset")
def dividends_by_asset():
    df = pd.read_csv(CSV_PATH)
    total_dividends = (df["shares"] * df["dividend_per_share"]).sum()
    results = []
    for _, row in df.iterrows():
        annual_div = row["shares"] * row["dividend_per_share"]
        results.append({
            "ticker": row["symbol"],
            "annual_dividend_usd": round(annual_div, 2),
            "percentage_of_total": round(annual_div / total_dividends * 100, 1) if total_dividends else 0
        })
    return results
