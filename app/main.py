from fastapi import FastAPI

# =========================
# Database
# =========================
from app.database import Base, engine

# =========================
# Importar modelos (IMPORTANTE para registrar metadata)
# =========================
from app.models import recommendation_run
from app.models import recommendation_item
from app.models import portfolio  # si ya existe

# =========================
# Crear aplicación
# =========================
app = FastAPI(title="InversorAPP Backend", version="2.0.0")
from app.api import recommendations

app.include_router(recommendations.router)

# =========================
# Crear tablas automáticamente (solo para entorno local)
# =========================
Base.metadata.create_all(bind=engine)

# =========================
# Routers
# =========================
from app.routers import recommendation_test

# Si tienes otros routers:
# from app.routers import auth
# from app.routers import config_routes
# from app.routers import market_test
# from app.routers import portfolio_actual

app.include_router(recommendation_test.router)
# app.include_router(auth.router)
# app.include_router(config_routes.router)
# app.include_router(market_test.router)
# app.include_router(portfolio_actual.router)


# =========================
# Health Check
# =========================
@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running"}
