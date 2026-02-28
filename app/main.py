from fastapi import FastAPI
from app.database import Base, engine

# Importar todos los routers existentes
from app.api.portfolio_snapshot import router as portfolio_snapshot_router
from app.api.portfolio_time_series import router as portfolio_time_series_router
from app.api.yield_history import router as yield_history_router
from app.api.portfolio_actual import router as portfolio_actual_router

from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import (
    router as recommendations_candidates_router,
)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Crear app
app = FastAPI(title="InversionAPPB Backend")


# Health check
@app.get("/system/status")
def system_status():
    return {"status": "ok", "message": "Backend running"}


# Registrar routers EXACTOS

app.include_router(portfolio_snapshot_router, prefix="/portfolio")
app.include_router(portfolio_time_series_router, prefix="/portfolio")
app.include_router(yield_history_router, prefix="/portfolio")
app.include_router(portfolio_actual_router, prefix="/portfolio")

app.include_router(recommendations_router, prefix="/recommendations")
app.include_router(recommendations_candidates_router, prefix="/recommendations")
