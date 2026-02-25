from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict

from app.database import get_db
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import RecommendationRunSchema
from app.models.recommendation_run import RecommendationRun
from app.models.recommendation_item import RecommendationItem

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# 🔹 GET /runs -> listado de todos los runs
@router.get("/runs", response_model=List[RecommendationRunSchema])
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(RecommendationRun).all()
    result = []
    for run in runs:
        items = db.query(RecommendationItem).filter_by(run_id=run.id).all()
        items_data = [
            {
                "ticker": i.ticker,
                "score": i.score,
                "allocated_amount": i.allocated_amount,
                "rule_trace": i.rule_trace,
            }
            for i in items
        ]
        result.append(
            {
                "run_id": run.id,
                "capital": run.capital,
                "status": "created",
                "items": items_data,
            }
        )
    return result


# 🔹 GET /runs/{run_id} -> detalle de un run
@router.get("/runs/{run_id}", response_model=RecommendationRunSchema)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(RecommendationRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    items = db.query(RecommendationItem).filter_by(run_id=run.id).all()
    items_data = [
        {
            "ticker": i.ticker,
            "score": i.score,
            "allocated_amount": i.allocated_amount,
            "rule_trace": i.rule_trace,
        }
        for i in items
    ]

    return {
        "run_id": run.id,
        "capital": run.capital,
        "status": "created",
        "items": items_data,
    }


# 🔹 POST /candidates -> crear un nuevo run de recomendaciones
@router.post("/candidates", response_model=RecommendationRunSchema)
def create_recommendation_run(
    capital_total: float = Query(300, description="Capital total a invertir"),
    tickers: List[str] = Query(
        ["VTI", "VXUS", "VOO", "QQQ"], description="Tickers a evaluar"
    ),
    exclude: List[str] = Query([], description="Tickers a excluir"),
    db: Session = Depends(get_db),
):
    run = RecommendationRepository.create_run(
        db=db, capital=capital_total, config_snapshot={"exclude": exclude}
    )

    tickers_to_use = [t for t in tickers if t not in exclude]

    items = RecommendationRepository.add_items(
        db=db, run_id=run.id, tickers=tickers_to_use, capital_total=capital_total
    )

    items_data = [
        {
            "ticker": i.ticker,
            "score": i.score,
            "allocated_amount": i.allocated_amount,
            "rule_trace": i.rule_trace,
        }
        for i in items
    ]

    return {
        "run_id": run.id,
        "capital": run.capital,
        "status": "created",
        "items": items_data,
    }
