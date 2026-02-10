from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.portfolio_snapshot import router as snapshot_router
from app.api.portfolio_time_series import router as time_series_router
from app.api.dividends_by_asset import router as dividends_router
from app.api.yield_history import router as yield_router
from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import router as candidates_router
from app.api.portfolio import router as portfolio_router
from app.api.investments import router as investments_router
from app.api.alerts import router as alerts_router
from app.api.history import router as history_router
from app.api.system import router as system_router

app = FastAPI(title="InversionAPP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(snapshot_router, prefix="/portfolio/snapshot")
app.include_router(time_series_router, prefix="/portfolio/time-series")
app.include_router(dividends_router, prefix="/portfolio/dividends-by-asset")
app.include_router(yield_router, prefix="/portfolio/yield-history")

app.include_router(portfolio_router, prefix="/portfolio")
app.include_router(recommendations_router, prefix="/recommendations")
app.include_router(candidates_router, prefix="/recommendations/candidates")
app.include_router(investments_router, prefix="/investments")

app.include_router(alerts_router, prefix="/alerts")
app.include_router(history_router, prefix="/history")
app.include_router(system_router, prefix="/system")
