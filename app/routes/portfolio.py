from fastapi import APIRouter
from app.services.portfolio_service import load_portfolio

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

@router.get("/snapshot")
def portfolio_snapshot():
    df = load_portfolio()

    return {
        "assets": [
            {
                "ticker": row["ticker"],
                "quantity": float(row["quantity"])
            }
            for _, row in df.iterrows()
        ],
        "total_assets": len(df)
    }
