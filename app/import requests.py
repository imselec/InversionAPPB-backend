import requests

BASE_URL = "http://127.0.0.1:8080"
PORTFOLIO_ID = 1  # Ajusta según tu portfolio

# -------------------------------
# 1️⃣ Portfolio Snapshot
# -------------------------------
resp = requests.get(f"{BASE_URL}/portfolio/{PORTFOLIO_ID}/snapshot")
print("Snapshot:", resp.status_code, resp.json())

# -------------------------------
# 2️⃣ Portfolio Time-Series
# -------------------------------
params = {"start": "2025-01-01", "end": "2026-01-01"}
resp = requests.get(f"{BASE_URL}/portfolio/{PORTFOLIO_ID}/time-series", params=params)
print("Time-Series:", resp.status_code, resp.json())

# -------------------------------
# 3️⃣ Dividends by Asset
# -------------------------------
params = {"ticker": "PG"}
resp = requests.get(
    f"{BASE_URL}/portfolio/{PORTFOLIO_ID}/dividends-by-asset", params=params
)
print("Dividends:", resp.status_code, resp.json())

# -------------------------------
# 4️⃣ Yield History
# -------------------------------
resp = requests.get(f"{BASE_URL}/portfolio/{PORTFOLIO_ID}/yield-history")
print("Yield History:", resp.status_code, resp.json())

# -------------------------------
# 5️⃣ Recommendations
# -------------------------------
# Si es GET
resp = requests.get(f"{BASE_URL}/recommendations")
print("Recommendations (GET):", resp.status_code, resp.json())

# Si es POST
payload = {"strategy": "growth"}
resp = requests.post(f"{BASE_URL}/recommendations", json=payload)
print("Recommendations (POST):", resp.status_code, resp.json())

# -------------------------------
# 6️⃣ Alerts
# -------------------------------
# GET
resp = requests.get(f"{BASE_URL}/alerts")
print("Alerts (GET):", resp.status_code, resp.json())

# POST
payload = {"ticker": "JPM", "price_target": 130}
resp = requests.post(f"{BASE_URL}/alerts", json=payload)
print("Alerts (POST):", resp.status_code, resp.json())

# DELETE (ejemplo con id=1)
resp = requests.delete(f"{BASE_URL}/alerts/1")
print(
    "Alerts (DELETE):",
    resp.status_code,
    resp.json() if resp.status_code != 204 else "Deleted",
)

# -------------------------------
# 7️⃣ History
# -------------------------------
resp = requests.get(f"{BASE_URL}/history")
print("History:", resp.status_code, resp.json())

# -------------------------------
# 8️⃣ System Status
# -------------------------------
resp = requests.get(f"{BASE_URL}/system/status")
print("System Status:", resp.status_code, resp.json())
