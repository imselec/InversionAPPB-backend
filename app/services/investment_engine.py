from app.services.scoring_service import calculate_monthly_allocation
from app.core.config import PLAN_MENSUAL_USD
from app.database import SessionLocal
from app.models.recommendation_run import RecommendationRun
from app.models.recommendation_item import RecommendationItem


def run_monthly_investment():

    config = {
        "monthly_investment": PLAN_MENSUAL_USD
    }

    allocation_results = calculate_monthly_allocation(config)

    db = SessionLocal()

    try:
        # Crear run
        run = RecommendationRun(capital=PLAN_MENSUAL_USD)
        db.add(run)
        db.commit()
        db.refresh(run)

        # Crear items
        for item in allocation_results:
            db_item = RecommendationItem(
                run_id=run.id,
                ticker=item["ticker"],
                weight=item["weight"],
                allocation_usd=item["allocation_usd"],
                score=item["score"],
                buy_signal=item["buy_signal"]
            )
            db.add(db_item)

        db.commit()

        return {
            "run_id": run.id,
            "capital": PLAN_MENSUAL_USD,
            "allocations": allocation_results
        }

    finally:
        db.close()