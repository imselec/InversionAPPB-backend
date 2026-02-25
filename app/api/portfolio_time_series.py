from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def time_series():
    return [
        {"date": "2025-09-01", "value": 11000},
        {"date": "2025-12-01", "value": 12000},
        {"date": "2026-02-01", "value": 12500},
    ]
