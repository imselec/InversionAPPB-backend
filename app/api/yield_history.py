from fastapi import APIRouter

router = APIRouter()


@router.get("/yield-history")
def yield_history():
    return {"data": []}
