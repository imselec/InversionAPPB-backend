from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def yield_history():
    return [
        {"date": "2025-09-01", "yield": 3.6},
        {"date": "2025-12-01", "yield": 3.7},
        {"date": "2026-02-01", "yield": 3.8},
    ]
