from fastapi import APIRouter, HTTPException
from app.core.security import create_access_token

router = APIRouter(tags=["auth"])

FAKE_USER = {
    "username": "admin",
    "password": "admin123"
}

@router.post("/login")
def login(credentials: dict):
    if credentials["username"] != FAKE_USER["username"] or credentials["password"] != FAKE_USER["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": credentials["username"]})
    return {"access_token": token}
