from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.repositories.recommendation_repository import RecommendationRepository

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    return RecommendationRepository.get_runs(db)


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    result = RecommendationRepository.get_run_with_items(db, run_id)

    if not result:
        raise HTTPException(status_code=404, detail="Run not found")

    return result
