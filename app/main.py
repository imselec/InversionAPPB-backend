from fastapi import FastAPI
from app.database import Base, engine

# importar routers
from app.api.portfolio import router as portfolio_router
from app.api.recommendations import router as recommendations_router
from app.api.alerts import router as alerts_router

# crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="InversionAPPB Backend")


# health check
@app.get("/system/status")
def system_status():
    return {"status": "ok", "message": "Backend running"}


# registrar routers
app.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
app.include_router(
    recommendations_router, prefix="/recommendations", tags=["recommendations"]
)
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
