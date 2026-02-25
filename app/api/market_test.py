from fastapi import APIRouter
from app.infrastructure.market_data_provider import get_price

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/{ticker}")
def market_price(ticker: str):
    price = get_price(ticker.upper())

    if price is None:
        return {"error": "Data unavailable"}

    return {"ticker": ticker.upper(), "price": price}
