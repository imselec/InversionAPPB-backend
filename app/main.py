from fastapi import FastAPI
from app.database import Base, engine
from app.api import recommendations
from fastapi.middleware.cors import CORSMiddleware

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InversionAPPB Backend",
    description="Backend FastAPI para gestión de inversiones",
    version="1.0.0",
)

# CORS (si lo necesitas)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(
    recommendations.router, prefix="/recommendations", tags=["recommendations"]
)


@app.get("/system/status")
def system_status():
    return {
        "status": "ok",
        "message": "Backend InversionAPPB funcionando correctamente",
    }
