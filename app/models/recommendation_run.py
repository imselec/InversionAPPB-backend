# app/models/recommendation_run.py

from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id = Column(Integer, primary_key=True, index=True)
    capital = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "RecommendationItem",
        back_populates="run",
        cascade="all, delete-orphan"
    )