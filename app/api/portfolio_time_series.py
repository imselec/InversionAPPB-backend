from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/time-series")
def portfolio_time_series():
    """
    Retorna evolución histórica del valor total del portafolio
    """
    df = pd.read_csv("app/portfolio.csv")

    # Agrupar por fecha
    df["position_value"] = df["shares"] * df["price"]
    history = df.groupby("date").agg(total_value=("position_value", "sum")).reset_index()

    return {
        "history": [
            {"date": row["date"], "total_value": round(row["total_value"], 2)}
            for _, row in history.iterrows()
        ]
    }
