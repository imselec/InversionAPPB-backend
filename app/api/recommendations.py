from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def recommendations():
    return {"data": []}
