from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

app = FastAPI(title="InversionAPPB Backend", version="1.0.0")

# =========================
# CORS CORRECTO
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # IMPORTANTE: no dejar vacío
    allow_credentials=True,
    allow_methods=["*"],  # IMPORTANTE: no dejar vacío
    allow_headers=["*"],
)


# =========================
# Middleware para OPTIONS
# =========================
@app.middleware("http")
async def handle_options(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(status_code=200, content={})
    return await call_next(request)


# =========================
# Routers
# =========================
app.include_router(system_router, prefix="/system", tags=["system"])
app.include_router(
    portfolio_snapshot_router, prefix="/portfolio/snapshot", tags=["portfolio"]
)
app.include_router(
    portfolio_time_series_router, prefix="/portfolio/time-series", tags=["portfolio"]
)
app.include_router(
    dividends_by_asset_router,
    prefix="/portfolio/dividends-by-asset",
    tags=["portfolio"],
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


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running with CORS fully enabled"}
