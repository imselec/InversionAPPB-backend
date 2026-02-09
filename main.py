from fastapi import FastAPI

from app.api.portfolio_snapshot import router as snapshot_router
from app.api.portfolio_time_series import router as time_series_router
from app.api.dividends_by_asset import router as dividends_router
from app.api.yield_history import router as yield_router

app = FastAPI()

app.include_router(snapshot_router)
app.include_router(time_series_router)
app.include_router(dividends_router)
app.include_router(yield_router)

