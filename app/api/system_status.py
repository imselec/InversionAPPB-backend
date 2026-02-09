from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/status")
def system_status():
    return {
        "status": "READY",
        "last_run": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "message": "System operational"
    }
