from fastapi import APIRouter

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/candidates")
def candidates():
    return {
        "candidates": [
            {"ticker": "JPM"},
            {"ticker": "O"},
            {"ticker": "MS"},
        ]
    }
