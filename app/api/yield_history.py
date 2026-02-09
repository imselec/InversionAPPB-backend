from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/yield-history")
def yield_history():
    df = pd.read_csv("portfolio.csv", parse_dates=["date"])

    df["position_value"] = df["shares"] * df["price"]

    grouped = df.groupby("date").agg(
        total_value=("position_value", "sum"),
        total_dividends=("dividend", "sum")
    ).reset_index()

    grouped["yield"] = (
        grouped["total_dividends"] / grouped["total_value"]
    ) * 100

    return {
        "yield": [
            {
                "date": d.strftime("%Y-%m-%d"),
                "yield": round(y, 2)
            }
            for d, y in zip(grouped["date"], grouped["yield"])
        ]
    }
