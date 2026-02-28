import json
from datetime import datetime

import requests

BACKEND_URL = "https://inversionappb-backend.onrender.com"

ENDPOINTS = {
    "System Status": "/system/status",
    "Portfolio Snapshot": "/portfolio/snapshot",
    "Portfolio Time Series": "/portfolio/time-series",
    "Dividends by Asset": "/portfolio/dividends-by-asset",
    "Yield History": "/portfolio/yield-history",
    "Recommendation Candidates": "/recommendations/candidates",
    "Recommendations": "/recommendations",
    "Alerts": "/alerts",
}


def test_endpoint(name, path):
    url = f"{BACKEND_URL}{path}"
    try:
        response = requests.get(url, timeout=30)

        print(f"\n{name}")
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, dict):
                print("Response keys:", list(data.keys()))
            elif isinstance(data, list):
                print(f"Response items: {len(data)}")
            else:
                print("Response type:", type(data))

            print("OK")
            return True
        else:
            print("FAILED:", response.text)
            return False

    except Exception as e:
        print(f"\n{name}")
        print("ERROR:", str(e))
        return False


def main():
    print("=" * 50)
    print("Lovable ↔ Render Backend Connection Test")
    print("Time:", datetime.now())
    print("Backend:", BACKEND_URL)
    print("=" * 50)

    success = 0

    for name, path in ENDPOINTS.items():
        if test_endpoint(name, path):
            success += 1

    print("\n" + "=" * 50)
    print(f"Result: {success}/{len(ENDPOINTS)} endpoints OK")

    if success == len(ENDPOINTS):
        print("BACKEND FULLY OPERATIONAL")
    else:
        print("Some endpoints failed")


if __name__ == "__main__":
    main()
