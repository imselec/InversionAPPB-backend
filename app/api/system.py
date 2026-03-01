from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def system_status():
    return {"status": "ok", "message": "Backend running"}
