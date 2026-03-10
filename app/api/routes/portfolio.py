from fastapi import APIRouter

router = APIRouter()


@router.get("/snapshot")
def portfolio_snapshot():
    return {
        "portfolio_value": 10000
    }
