from fastapi import APIRouter
from app.services.portfolio_service import portfolio_history

router = APIRouter(prefix="/history", tags=["history"])

@router.get("")
def history():
    return portfolio_history()
