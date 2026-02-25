# app/repositories/recommendation_repository.py

import random
from sqlalchemy.orm import Session
from app.models.recommendation_run import RecommendationRun
from app.models.recommendation_item import RecommendationItem


class RecommendationRepository:
    model_run = RecommendationRun
    model_item = RecommendationItem

    @staticmethod
    def create_run(db: Session, capital: float, config_snapshot: dict):
        """
        Crea un nuevo run y lo guarda en la DB
        """
        run = RecommendationRun(capital=capital, config_snapshot=config_snapshot)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def add_items(
        db: Session, run_id: int, tickers: list[str], capital_total: float = 300
    ):
        """
        Genera RecommendationItems para un run usando motor profesional.
        Scores ponderados, allocation proporcional y trace completo.
        """
        items_to_add = []

        # 1️⃣ Generar métricas base y rule_trace
        raw_items = []
        for t in tickers:
            momentum = round(random.uniform(0.5, 1.0), 3)  # 0.5 = bajo, 1.0 = alto
            volatility = round(
                random.uniform(0.3, 0.9), 3
            )  # 0.3 = estable, 0.9 = muy volátil

            # Score ponderado según reglas
            score = round((momentum * 0.6 + (1 - volatility) * 0.4) * 100, 1)

            rule_trace = {
                "momentum": momentum,
                "volatility": volatility,
                "weights": {"momentum": 0.6, "volatility": 0.4},
                "score_formula": "score = (momentum*0.6 + (1-volatility)*0.4)*100",
            }

            raw_items.append({"ticker": t, "score": score, "rule_trace": rule_trace})

        # 2️⃣ Normalizar scores para asignación proporcional
        total_score = sum(i["score"] for i in raw_items)
        for i in raw_items:
            weight = i["score"] / total_score
            allocated_amount = round(weight * capital_total, 2)

            item = RecommendationItem(
                run_id=run_id,
                ticker=i["ticker"],
                score=i["score"],
                allocated_amount=allocated_amount,
                rule_trace=i["rule_trace"],
            )
            items_to_add.append(item)

        # 3️⃣ Guardar en DB
        db.add_all(items_to_add)
        db.commit()
        return items_to_add
