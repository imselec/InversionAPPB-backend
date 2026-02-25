from fastapi import APIRouter, Depends
from app.core.security import verify_token

router = APIRouter(tags=["config"])

BENCHMARK = {"symbol": "SPY"}

@router.get("/benchmark")
def get_benchmark(user=Depends(verify_token)):
    return BENCHMARK

@router.post("/benchmark")
def set_benchmark(data: dict, user=Depends(verify_token)):
    BENCHMARK["symbol"] = data["symbol"]
    return BENCHMARK
