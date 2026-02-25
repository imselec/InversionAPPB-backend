import requests

# -------------------------------
# Configuración
# -------------------------------
BASE_URL = "http://127.0.0.1:8080"
PORTFOLIO_ID = 1  # Ajusta según tu cartera

# Prefijos según routers en main.py
PREFIXES = {
    "portfolio": "/portfolio",
    "market": "/market_test",
    "auth": "/auth",
    "config": "/config_routes",
}


# Función de prueba genérica
def test_endpoint(method, path, params=None, json_data=None):
    url = BASE_URL + path
    try:
        if method.upper() == "GET":
            resp = requests.get(url, params=params)
        elif method.upper() == "POST":
            resp = requests.post(url, json=json_data)
        elif method.upper() == "DELETE":
            resp = requests.delete(url)
        else:
            print(f"[ERROR] Método no soportado: {method}")
            return
        print(f"{method} {path} → {resp.status_code}")
        try:
            print(resp.json())
        except:
            print(resp.text)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Falló conexión a {url}: {e}")


# -------------------------------
# 1️⃣ Portfolio Endpoints
# -------------------------------
portfolio_prefix = PREFIXES["portfolio"]

# Snapshot
test_endpoint("GET", f"{portfolio_prefix}/snapshot/{PORTFOLIO_ID}")

# Time-Series
test_endpoint(
    "GET",
    f"{portfolio_prefix}/time-series/{PORTFOLIO_ID}",
    params={"start": "2025-01-01", "end": "2026-01-01"},
)

# Dividends by Asset
test_endpoint(
    "GET",
    f"{portfolio_prefix}/dividends-by-asset/{PORTFOLIO_ID}",
    params={"ticker": "PG"},
)

# Yield History
test_endpoint("GET", f"{portfolio_prefix}/yield-history/{PORTFOLIO_ID}")

# -------------------------------
# 2️⃣ Recommendations
# -------------------------------
recommendations_prefix = PREFIXES["market"]  # Ajusta si está en otro router
# GET
test_endpoint("GET", f"{recommendations_prefix}/recommendations")
# POST
test_endpoint(
    "POST",
    f"{recommendations_prefix}/recommendations",
    json_data={"strategy": "growth"},
)

# -------------------------------
# 3️⃣ Alerts
# -------------------------------
alerts_prefix = PREFIXES["config"]  # Ajusta según router real
# GET
test_endpoint("GET", f"{alerts_prefix}/alerts")
# POST
test_endpoint(
    "POST", f"{alerts_prefix}/alerts", json_data={"ticker": "JPM", "price_target": 130}
)
# DELETE ejemplo
test_endpoint("DELETE", f"{alerts_prefix}/alerts/1")

# -------------------------------
# 4️⃣ History
# -------------------------------
test_endpoint("GET", f"{portfolio_prefix}/history")

# -------------------------------
# 5️⃣ System Status
# -------------------------------
system_prefix = PREFIXES["auth"]  # Ajusta según router real
test_endpoint("GET", f"{system_prefix}/status")
