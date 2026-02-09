from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/dividends-by-asset")
def dividends_by_asset():
    df = pd.read_csv("portfolio.csv")

    divs = (
        df.groupby("ticker")["dividend"]
        .sum()
        .reset_index()
        .sort_values("dividend", ascending=False)
    )

    return {
        "dividends": [
            {
                "ticker": t,
                "total": round(d, 2)
            }
            for t, d in zip(divs["ticker"], divs["dividend"])
        ]
    }
