from fastapi import FastAPI

from app.routes.system import router as system_router
from app.routes.portfolio import router as portfolio_router
from app.routes.recommendations import router as recommendations_router
from app.routes.alerts import router as alerts_router
from app.routes.history import router as history_router

app = FastAPI(title="InversionAPP API")

app.include_router(system_router)
app.include_router(portfolio_router)
app.include_router(recommendations_router)
app.include_router(alerts_router)
app.include_router(history_router)
