from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/snapshot")
def portfolio_snapshot():
    df = pd.read_csv("portfolio.csv")

    df["position_value"] = df["shares"] * df["price"]

    total_value = round(df["position_value"].sum(), 2)

    positions = (
        df.groupby("ticker")
        .agg(
            shares=("shares", "sum"),
            price=("price", "last"),
            value=("position_value", "sum")
        )
        .reset_index()
    )

    positions["weight"] = positions["value"] / total_value * 100

    return {
        "total_value": total_value,
        "positions": [
            {
                "ticker": row["ticker"],
                "shares": round(row["shares"], 4),
                "price": round(row["price"], 2),
                "value": round(row["value"], 2),
                "weight": round(row["weight"], 2)
            }
            for _, row in positions.iterrows()
        ]
    }
