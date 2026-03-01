from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

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

# =========================================================
# CREATE APP
# =========================================================

app = FastAPI(title="InversionAPP Backend", version="1.0.0")

# =========================================================
# FORCE CORS — CRITICAL FOR LOVABLE
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# GLOBAL OPTIONS HANDLER (FIXES 405)
# =========================================================


@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    return Response(status_code=200)


# =========================================================
# ROOT
# =========================================================


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running"}


# =========================================================
# ROUTERS
# =========================================================

app.include_router(system_router, prefix="/system", tags=["System"])

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

app.include_router(
    recommendations_router, prefix="/recommendations", tags=["Recommendations"]
)

app.include_router(
    recommendations_candidates_router,
    prefix="/recommendations/candidates",
    tags=["Recommendations"],
)

app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
