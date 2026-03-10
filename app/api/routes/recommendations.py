from fastapi import APIRouter

router = APIRouter()


@router.get("/top-pick")
def top_pick():
    return {
        "ticker": "LMT",
        "score": 92
    }
