from sqlalchemy import Column, Integer, Float, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("recommendation_runs.id"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    score = Column(Float, nullable=False)
    allocated_amount = Column(Float, nullable=False)
    rule_trace = Column(JSON, nullable=False)

    run = relationship("RecommendationRun", backref="items", lazy="selectin")
