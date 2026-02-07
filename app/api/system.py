from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/status")
def system_status():
    return {
        "status": "ok",
        "service": "inversionapp-backend"
    }
