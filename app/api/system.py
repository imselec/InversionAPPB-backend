from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def system_status():
    return {"status": "READY", "last_run": "2026-02-09T10:00:00Z", "message": "System operational"}
