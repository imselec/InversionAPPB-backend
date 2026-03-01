import os

import requests

BASE_URL = os.getenv("PYTHON_BACKEND_URL", "https://inversionappb-backend.onrender.com")


def get(endpoint: str):
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
