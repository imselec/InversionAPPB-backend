from fastapi import FastAPI
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

# Importar TODOS los routers
from app.api.portfolio_snapshot import router as portfolio_snapshot_router
from app.api.portfolio_time_series import router as portfolio_time_series_router
from app.api.yield_history import router as yield_history_router
from app.api.portfolio_actual import router as portfolio_actual_router

from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import (
    router as recommendations_candidates_router,
)

from app.api.dividends_by_asset import router as dividends_by_asset_router
from app.api.alerts import router as alerts_router

app = FastAPI(title="InversionAPP Backend", version="1.0.0")

# ✅ CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Crear tablas
Base.metadata.create_all(bind=engine)

# Crear app
app = FastAPI(title="InversionAPPB Backend", version="1.0.0")

app.include_router(dividends_by_asset_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(alerts_router, tags=["Alerts"])

# Health check
@app.get("/system/status")
def system_status():
    return {"status": "ok", "message": "Backend running"}


# Registrar routers PORTFOLIO
app.include_router(portfolio_snapshot_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(
    portfolio_time_series_router, prefix="/portfolio", tags=["Portfolio"]
)
app.include_router(yield_history_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(portfolio_actual_router, prefix="/portfolio", tags=["Portfolio"])

# Registrar routers RECOMMENDATIONS
app.include_router(
    recommendations_router, prefix="/recommendations", tags=["Recommendations"]
)
app.include_router(
    recommendations_candidates_router,
    prefix="/recommendations",
    tags=["Recommendations"],
)
