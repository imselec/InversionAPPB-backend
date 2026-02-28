from fastapi import APIRouter

router = APIRouter()


@router.get("/candidates")
def candidates():
    return {"data": []}
