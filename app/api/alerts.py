from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("")
def alerts():
    # Ejemplo de alerta basada en la cartera actual
    return [
        {
            "id": "a1",
            "ticker": "JNJ",
            "signal_type": "HOLD",
            "indicator": "RSI neutral at 52",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    ]
