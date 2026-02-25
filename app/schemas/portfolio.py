from pydantic import BaseModel


class PortfolioResponse(BaseModel):
    id: int
    ticker: str
    shares: float
    purchase_price: float

    class Config:
        orm_mode = True
