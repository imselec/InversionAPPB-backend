import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[2] / "portfolio.csv"

def load_portfolio():
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=["date", "symbol", "shares", "price"])

    return pd.read_csv(CSV_PATH)

def portfolio_snapshot():
    df = load_portfolio()

    if df.empty:
        return {
            "total_value": 0,
            "cash": 0,
            "positions": []
        }

    df["value"] = df["shares"] * df["price"]

    positions = (
        df.groupby("symbol", as_index=False)
        .agg({"shares": "sum", "value": "sum"})
        .to_dict(orient="records")
    )

    return {
        "total_value": round(df["value"].sum(), 2),
        "cash": 0,
        "positions": positions
    }

def portfolio_time_series():
    df = load_portfolio()

    if df.empty:
        return {"series": []}

    df["value"] = df["shares"] * df["price"]

    series = (
        df.groupby("date", as_index=False)["value"]
        .sum()
        .rename(columns={"value": "value"})
        .to_dict(orient="records")
    )

    return {"series": series}

def portfolio_history():
    df = load_portfolio()

    if df.empty:
        return {"operations": []}

    return {
        "operations": df.to_dict(orient="records")
    }
