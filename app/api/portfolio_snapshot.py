from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def snapshot():
    return {
        "total_value": 12500,
        "annual_dividends": 480,
        "yield": 3.8
    }
