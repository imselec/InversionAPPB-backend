from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.api.portfolio_snapshot import router as snapshot_router
from app.api.portfolio_time_series import router as time_series_router
from app.api.dividends_by_asset import router as dividends_router
from app.api.yield_history import router as yield_router
from app.api.recommendations import router as recommendations_router
from app.api.candidates import router as candidates_router
from app.api.alerts import router as alerts_router
from app.api.history import router as history_router
from app.api.system_status import router as status_router
from app.api.system_audit import router as audit_router
from app.api.investments_plan import router as plan_router

app = FastAPI(title="InversionAPP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(snapshot_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(time_series_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(dividends_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(yield_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(candidates_router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(history_router, prefix="/history", tags=["History"])
app.include_router(status_router, prefix="/system", tags=["System"])
app.include_router(audit_router, prefix="/system", tags=["System"])
app.include_router(plan_router, prefix="/investments/plan", tags=["Investments"])
