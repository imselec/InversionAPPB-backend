from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# importar routers
from app.api.portfolio_snapshot import router as portfolio_snapshot_router
from app.api.portfolio_time_series import router as portfolio_time_series_router
from app.api.dividends_by_asset import router as dividends_router
from app.api.yield_history import router as yield_history_router
from app.api.recommendations import router as recommendations_router
from app.api.recommendations_candidates import router as candidates_router
from app.api.alerts import router as alerts_router
from app.api.system import router as system_router


app = FastAPI(title="InversionAPP Backend")


# ===== CORS CONFIGURATION (CRITICAL) =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes restringir luego
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== ROUTERS =====

app.include_router(system_router, prefix="/system")

app.include_router(portfolio_snapshot_router, prefix="/portfolio/snapshot")
app.include_router(portfolio_time_series_router, prefix="/portfolio/time-series")
app.include_router(dividends_router, prefix="/portfolio/dividends-by-asset")
app.include_router(yield_history_router, prefix="/portfolio/yield-history")

app.include_router(recommendations_router, prefix="/recommendations")
app.include_router(candidates_router, prefix="/recommendations/candidates")

app.include_router(alerts_router, prefix="/alerts")


# ===== ROOT =====


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running"}
