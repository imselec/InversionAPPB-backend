from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.security import create_access_token

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


FAKE_USER = {
    "username": "admin",
    "password": "admin123"
}


@router.post("/login")
def login(credentials: LoginRequest):
    if (credentials.username != FAKE_USER["username"] or
            credentials.password != FAKE_USER["password"]):
        raise HTTPException(status_code=401,
                            detail="Invalid credentials")

    token = create_access_token({"sub": credentials.username})
    return {"access_token": token, "token_type": "bearer"}
