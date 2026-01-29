import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PORTFOLIO_FILE = BASE_DIR / "portfolio.csv"

def load_portfolio():
    return pd.read_csv(PORTFOLIO_FILE)
