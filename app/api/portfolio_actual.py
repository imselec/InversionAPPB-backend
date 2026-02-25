from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Ajusta estos imports según tu estructura real
from app.database import get_db
from app.models.portfolio import Portfolio
from app.schemas.portfolio import PortfolioResponse

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/", response_model=List[PortfolioResponse])
def get_portfolio(db: Session = Depends(get_db)):
    """
    Devuelve el portafolio actual completo.
    """
    portfolio_items = db.query(Portfolio).all()

    if not portfolio_items:
        return []

    return portfolio_items


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio_by_id(portfolio_id: int, db: Session = Depends(get_db)):
    """
    Devuelve un activo específico del portafolio.
    """
    item = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")

    return item
