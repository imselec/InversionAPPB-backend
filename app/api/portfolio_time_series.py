from fastapi import APIRouter

router = APIRouter()


@router.get("/time-series")
def time_series():
    return {"data": []}
