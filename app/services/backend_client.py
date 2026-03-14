import os
import requests
from requests.exceptions import JSONDecodeError

BASE_URL = os.getenv("PYTHON_BACKEND_URL", "https://inversionappb-backend.onrender.com")


def get(endpoint: str):
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Handle empty or non-JSON responses
    if not response.content:
        return {}
    
    try:
        return response.json()
    except (JSONDecodeError, ValueError) as e:
        # If response is not valid JSON, return the text content
        print(f"Warning: Response from {endpoint} is not valid JSON: {e}")
        return {"error": "Invalid JSON response", "content": response.text}
