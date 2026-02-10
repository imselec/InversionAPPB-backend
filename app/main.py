# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api.portfolio_snapshot import router as snapshot_router
from app.api.portfolio_time_series import router as time_series_router
from app.api.dividends_by_asset import router as dividends_router
from app.api.yield_history import router as yield_router
from app.api.recommendations import router as recommendations_router
from app.api.alerts import router as alerts_router
from app.api.history import router as history_router
from app.api.system import router as system_router
from app.api.investments_plan import router as investments_plan_router  # NUEVO

# ───────────────────────────────
# App FastAPI
# ───────────────────────────────
app = FastAPI(title="InversionAPP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────────────────────
# Include routers
# ───────────────────────────────
app.include_router(snapshot_router, prefix="/portfolio/snapshot", tags=["Portfolio Snapshot"])
app.include_router(time_series_router, prefix="/portfolio/time-series", tags=["Portfolio Time Series"])
app.include_router(dividends_router, prefix="/portfolio/dividends-by-asset", tags=["Dividends by Asset"])
app.include_router(yield_router, prefix="/portfolio/yield-history", tags=["Yield History"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(history_router, prefix="/history", tags=["History"])
app.include_router(system_router, prefix="/system", tags=["System"])
app.include_router(investments_plan_router, prefix="/investments/plan/monthly", tags=["Investments Plan"])
