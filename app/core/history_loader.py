from pathlib import Path
import csv
from typing import Dict, List
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[2]

PRICE_HISTORY_PATH = BASE_DIR / "data" / "price_history.csv"
DIVIDENDS_PATH = BASE_DIR / "data" / "dividends.csv"

def load_price_history() -> Dict[str, List[float]]:
    data = defaultdict(list)
    with open(PRICE_HISTORY_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[row["ticker"].upper()].append(float(row["close_price"]))
    return data

def load_dividends() -> Dict[str, float]:
    data = defaultdict(float)
    with open(DIVIDENDS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[row["ticker"].upper()] += float(row["dividend"])
    return data
