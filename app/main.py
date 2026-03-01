from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.api.portfolio_snapshot import router as portfolio_snapshot_router
from app.api.portfolio_time_series import router as portfolio_time_series_router
from app.api.yield_history import router as yield_history_router
from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import (
    router as recommendations_candidates_router,
)
from app.api.alerts import router as alerts_router

app = FastAPI(title="InversionAPP Backend", version="1.0.0")

# ✅ CORS CONFIG — CRÍTICO: debe ir ANTES de include_router
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permite lovable y cualquier preview
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(
    portfolio_snapshot_router, prefix="/portfolio/snapshot", tags=["portfolio"]
)

app.include_router(
    portfolio_time_series_router, prefix="/portfolio/time-series", tags=["portfolio"]
)

app.include_router(
    yield_history_router, prefix="/portfolio/yield-history", tags=["portfolio"]
)

app.include_router(
    recommendations_router, prefix="/recommendations", tags=["recommendations"]
)

app.include_router(
    recommendations_candidates_router,
    prefix="/recommendations/candidates",
    tags=["recommendations"],
)

app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])


@app.get("/system/status")
def system_status():
    return {"status": "ok", "message": "Backend running"}
