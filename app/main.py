from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configura CORS
origins = [
    "https://lovable.ai",        # dominio oficial de Lovable
    "http://localhost",          # opcional para pruebas locales
    "http://127.0.0.1"           # opcional para pruebas locales
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/system/status")
def status():
    return {"status": "ok"}

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def startup_event():
    logger.info("Backend started and ready")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Backend shutting down")
