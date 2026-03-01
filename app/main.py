from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# routers
from app.api.system import router as system_router
from app.api.portfolio_snapshot import router as portfolio_snapshot_router
from app.api.portfolio_time_series import router as portfolio_time_series_router
from app.api.dividends_by_asset import router as dividends_router
from app.api.yield_history import router as yield_history_router
from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import router as candidates_router
from app.api.alerts import router as alerts_router


# CREATE APP
app = FastAPI(title="InversionAPP Backend")


# ===== CRITICAL: CORS MUST BE HERE =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== ROOT =====


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running"}


# ===== SYSTEM =====

app.include_router(system_router, prefix="/system")


# ===== PORTFOLIO =====

app.include_router(portfolio_snapshot_router, prefix="/portfolio/snapshot")
app.include_router(portfolio_time_series_router, prefix="/portfolio/time-series")
app.include_router(dividends_router, prefix="/portfolio/dividends-by-asset")
app.include_router(yield_history_router, prefix="/portfolio/yield-history")


# ===== RECOMMENDATIONS =====

app.include_router(recommendations_router, prefix="/recommendations")
app.include_router(candidates_router, prefix="/recommendations/candidates")


# ===== ALERTS =====

app.include_router(alerts_router, prefix="/alerts")
