from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("")
def history():
    return [
        {
            "id": "h1",
            "run_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "invested_amount": 200,
            "recommendations_count": 5,
            "pdf_path": None,
            "email_sent": False
        }
    ]
