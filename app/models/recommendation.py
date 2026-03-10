from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id = Column(Integer, primary_key=True, index=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    total_invested = Column(Float)

    items = relationship("RecommendationItem", back_populates="run")


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("recommendation_runs.id"))
    ticker = Column(String, index=True)
    allocated_amount = Column(Float)
    score = Column(Float)

    run = relationship("RecommendationRun", back_populates="items")
    run = relationship("RecommendationRun", back_populates="items")
