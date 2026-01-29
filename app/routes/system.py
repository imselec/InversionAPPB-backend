from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/status")
def system_status():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/audit")
def system_audit():
    return {
        "events": [
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "event": "SYSTEM_START",
                "severity": "info"
            }
        ]
    }
