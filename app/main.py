# app/main.py
from fastapi import FastAPI

# Importa tus routers
from app.api.system import router as system_router
from app.api.portfolio import router as portfolio_router
from app.api.investments import router as investments_router

# Crear la app FastAPI
app = FastAPI(title="InversionAPP API", version="1.0")

# Root endpoint para que la URL base no devuelva 404
@app.get("/")
def root():
    return {"message": "InversionAPP backend está activo"}

# Incluir routers con prefijos y tags
app.include_router(system_router, prefix="/system", tags=["system"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
app.include_router(investments_router, prefix="/investments", tags=["investments"])
