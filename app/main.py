from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import investment

app = FastAPI(title="Investment Engine API", version="1.0")

# Permitir CORS para cualquier origen (solo para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


# Router seguro para Investment Engine
app.include_router(investment.router, prefix="/investment")
