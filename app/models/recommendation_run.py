from sqlalchemy import Column, Integer, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id = Column(Integer, primary_key=True, index=True)
    capital = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    config_snapshot = Column(JSON, nullable=False)
