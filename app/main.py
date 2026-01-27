from typing import List
import csv
import os
import json

from fastapi import FastAPI
from app.routes.system import router as system_router
from app.routes.portfolio import router as portfolio_router

app = FastAPI(title="InversionAPP API")

# Incluir routers
app.include_router(system_router)
app.include_router(portfolio_router)


# -------------------------
# Archivos de configuración
# -------------------------
CSV_FILE = os.path.join(os.path.dirname(__file__), "portfolio.csv")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# Leer inversión mensual desde config.json
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        monthly_budget = config.get("monthly_budget", 200)
else:
    monthly_budget = 200

# -------------------------
# Helper: Leer CSV
# -------------------------
def read_portfolio():
    portfolio = []
    with open(CSV_FILE, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            portfolio.append({
                "ticker": row["ticker"],
                "position": float(row["position"]),
                "price": float(row["price"]),
                "annual_dividend": float(row["annual_dividend"])
            })
    return portfolio

# -------------------------
# Snapshot y cálculos
# -------------------------
def calculate_snapshot(portfolio):
    total_positions = len(portfolio)
    estimated_annual_dividends = sum(d["position"] * d["annual_dividend"] for d in portfolio)
    average_yield = sum((d["annual_dividend"]/d["price"])*100*d["position"] for d in portfolio) / total_positions
    return {
        "date": "2026-01-23",
        "monthly_budget": monthly_budget,
        "total_positions": total_positions,
        "estimated_annual_dividends": round(estimated_annual_dividends,2),
        "average_yield": round(average_yield,2)
    }

def generate_dividends_by_asset(portfolio):
    total_dividends = sum(d["position"] * d["annual_dividend"] for d in portfolio)
    return [
        {
            "ticker": d["ticker"],
            "annual_dividend_usd": round(d["position"] * d["annual_dividend"],2),
            "percentage_of_total": round((d["position"] * d["annual_dividend"])/total_dividends*100,2)
        } for d in portfolio
    ]

# -------------------------
# Endpoints Portfolio
# -------------------------
@app.get("/portfolio/snapshot")
def portfolio_snapshot():
    portfolio = read_portfolio()
    return calculate_snapshot(portfolio)

@app.get("/portfolio/time-series")
def time_series():
    return [
        {"date": "2025-07", "total_invested": 10340.0, "estimated_annual_dividends": 182.27, "average_yield": 1.76},
        {"date": "2025-08", "total_invested": 10340.0, "estimated_annual_dividends": 182.27, "average_yield": 1.76},
        {"date": "2025-09", "total_invested": 10340.0, "estimated_annual_dividends": 182.27, "average_yield": 1.76},
    ]

@app.get("/portfolio/dividends-by-asset")
def dividends_by_asset():
    portfolio = read_portfolio()
    return generate_dividends_by_asset(portfolio)

@app.get("/portfolio/yield-history")
def yield_history():
    return [
        {"date": "2025-01", "yield": 4.2},
        {"date": "2025-02", "yield": 4.3},
        {"date": "2025-03", "yield": 4.1},
    ]

# -------------------------
# Recommendations
# -------------------------
@app.get("/recommendations")
def recommendations():
    return [
        {"ticker": "VYM", "allocation_usd": 100, "yield": 3.2, "reason": "High dividend ETF", "score": 85},
        {"ticker": "PEP", "allocation_usd": 100, "yield": 4.5, "reason": "Strong consumer sector", "score": 88},
        {"ticker": "CVX", "allocation_usd": 100, "yield": 5.1, "reason": "Energy sector dividend", "score": 82},
    ]

@app.get("/recommendations/candidates")
def candidates():
    return [
        {"ticker": "VYM", "reason": "High dividend ETF", "sector": "ETF"},
        {"ticker": "PEP", "reason": "Consistent dividend growth", "sector": "Consumer"},
        {"ticker": "CVX", "reason": "Strong dividend yield", "sector": "Energy"},
    ]

# -------------------------
# Alerts
# -------------------------
@app.get("/alerts")
def alerts():
    return [
        {"id": "1", "ticker": "AAPL", "signal_type": "BUY", "indicator": "RSI oversold", "date": "2026-01-23"}
    ]

# -------------------------
# History
# -------------------------
@app.get("/history")
def history():
    return [
        {"id": "1", "run_date": "2026-01-23", "invested_amount": monthly_budget, "recommendations_count": 3, "pdf_path": None, "email_sent": False}
    ]

# -------------------------
# System
# -------------------------
@app.get("/system/status")
def system_status():
    return {"status": "READY", "last_run": "2026-01-23T10:00:00Z", "message": "System operational"}

@app.get("/system/audit")
def audit():
    return {"status": "PASS", "messages": [{"level": "info", "text": "All checks passed"}]}

@app.post("/system/run")
def run_analysis():
    return {"success": True, "message": "Analysis completed"}
