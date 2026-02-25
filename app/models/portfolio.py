from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    shares = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)

    @property
    def market_value(self):
        if self.current_price:
            return self.shares * self.current_price
        return 0.0
