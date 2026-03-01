from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.api.system import router as system_router
from app.api.portfolio_snapshot import router as portfolio_snapshot_router
from app.api.portfolio_time_series import router as portfolio_time_series_router
from app.api.dividends_by_asset import router as dividends_by_asset_router
from app.api.yield_history import router as yield_history_router
from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import (
    router as recommendations_candidates_router,
)
from app.api.alerts import router as alerts_router

# Crear app
app = FastAPI(title="InversionAPP Backend", version="1.0.0")

# =========================================================
# CORS CONFIGURATION — NECESARIO PARA LOVABLE Y BROWSER
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permitir cualquier frontend (Lovable, local, etc)
    allow_credentials=True,
    allow_methods=["*"],  # permitir GET, POST, OPTIONS, etc
    allow_headers=["*"],
)


# =========================================================
# ROOT ENDPOINT
# =========================================================
@app.get("/")
def root():
    return {"status": "ok", "message": "InversionAPP Backend running"}


# =========================================================
# SYSTEM
# =========================================================
app.include_router(system_router, prefix="/system", tags=["System"])

# =========================================================
# PORTFOLIO
# =========================================================
app.include_router(
    portfolio_snapshot_router, prefix="/portfolio/snapshot", tags=["Portfolio"]
)

app.include_router(
    portfolio_time_series_router, prefix="/portfolio/time-series", tags=["Portfolio"]
)

app.include_router(
    dividends_by_asset_router,
    prefix="/portfolio/dividends-by-asset",
    tags=["Portfolio"],
)

app.include_router(
    yield_history_router, prefix="/portfolio/yield-history", tags=["Portfolio"]
)

# =========================================================
# RECOMMENDATIONS
# =========================================================
app.include_router(
    recommendations_router, prefix="/recommendations", tags=["Recommendations"]
)

app.include_router(
    recommendations_candidates_router,
    prefix="/recommendations/candidates",
    tags=["Recommendations"],
)

# =========================================================
# ALERTS
# =========================================================
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
