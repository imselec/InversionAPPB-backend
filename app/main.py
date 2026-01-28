from fastapi import FastAPI
from app.routes.system import router as system_router
from app.routes.portfolio import router as portfolio_router

app = FastAPI(title="InversionAPP Backend")

app.include_router(system_router)
app.include_router(portfolio_router)
