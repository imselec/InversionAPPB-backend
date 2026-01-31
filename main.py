import os
from fastapi import FastAPI, Header, HTTPException
from app import update_portfolio
from sqlalchemy.orm import Session
from app import db, models

app = FastAPI(title="InversionAPP Backend")

# Dependency
def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Endpoints existentes
@app.get("/system/status")
def status():
    return {"status": "ok"}

@app.get("/portfolio")
def get_portfolio_endpoint(db: Session = db.SessionLocal()):
    assets = db.query(models.Portfolio).all()
    return [
        {"symbol": asset.symbol, "quantity": asset.quantity, "avg_price": asset.avg_price}
        for asset in assets
    ]

# 🔹 Endpoint seguro para actualizar la DB
@app.post("/update-portfolio")
def update_portfolio_endpoint(secret_key: str = Header(...)):
    if secret_key != os.getenv("SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    update_portfolio.update_portfolio()
    return {"status": "Portfolio actualizado ✅"}
