from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.portfolio_api import router as portfolio_router
from app.api.market_data_api import router as market_router
from app.api.dividends_api import router as dividends_router
from app.api.recommendations_api import router as recommendations_router
from app.api.settings_api import router as settings_router
from app.api.analytics_api import router as analytics_router
from app.api.alerts_api import router as alerts_router
from app.api.notifications_api import router as notifications_router
from app.api.watchlist_api import router as watchlist_router
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="InversionAPP API",
    version="1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router)
app.include_router(market_router)
app.include_router(dividends_router)
app.include_router(recommendations_router)
app.include_router(settings_router)
app.include_router(analytics_router)
app.include_router(alerts_router)
app.include_router(notifications_router)
app.include_router(watchlist_router)


@app.get("/")
def root():
    return {"status": "running", "version": "1.0"}
