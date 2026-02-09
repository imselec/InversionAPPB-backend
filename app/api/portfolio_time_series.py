from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/time-series")
def portfolio_time_series():
    df = pd.read_csv("portfolio.csv", parse_dates=["date"])

    df["position_value"] = df["shares"] * df["price"]

    ts = (
        df.groupby("date")["position_value"]
        .sum()
        .reset_index()
        .sort_values("date")
    )

    return {
        "series": [
            {
                "date": d.strftime("%Y-%m-%d"),
                "value": round(v, 2)
            }
            for d, v in zip(ts["date"], ts["position_value"])
        ]
    }
