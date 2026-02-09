from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/dividends-by-asset")
def dividends_by_asset():
    """
    Retorna los dividendos acumulados por cada activo
    """
    df = pd.read_csv("app/portfolio.csv")

    df_div = df.groupby("ticker").agg(dividends=("dividend", "sum")).reset_index()

    return {
        "dividends": [
            {"ticker": row["ticker"], "dividends": round(row["dividends"], 2)}
            for _, row in df_div.iterrows()
        ]
    }
