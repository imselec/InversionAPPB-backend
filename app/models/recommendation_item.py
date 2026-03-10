# app/models/recommendation_item.py

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id = Column(Integer, primary_key=True, index=True)

    run_id = Column(Integer, ForeignKey("recommendation_runs.id"))
    ticker = Column(String, nullable=False)
    weight = Column(Float)
    allocation_usd = Column(Float)
    score = Column(Float)
    buy_signal = Column(Boolean)

    run = relationship("RecommendationRun", back_populates="items")