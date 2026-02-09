from fastapi import APIRouter
import pandas as pd

router = APIRouter()

@router.get("/portfolio/yield-history")
def yield_history():
    """
    Retorna rendimiento histórico aproximado por fecha
    """
    df = pd.read_csv("app/portfolio.csv")
    df["position_value"] = df["shares"] * df["price"]
    df_group = df.groupby("date").agg(total_value=("position_value", "sum")).reset_index()
    
    # Calcular rendimiento relativo al primer valor
    if not df_group.empty:
        initial = df_group["total_value"].iloc[0]
        df_group["yield"] = (df_group["total_value"] - initial) / initial * 100
    else:
        df_group["yield"] = 0

    return {
        "yield_history": [
            {"date": row["date"], "yield_percent": round(row["yield"], 2)}
            for _, row in df_group.iterrows()
        ]
    }
