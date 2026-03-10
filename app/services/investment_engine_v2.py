from app.services.scoring_service import score_assets
from app.services.allocation_engine import recommend_purchase


def load_mock_market_data():
    """
    Datos simulados para pruebas del motor de inversión
    """

    assets = [
        {
            "ticker": "TXN",
            "yield": 2.9,
            "momentum": 0.20,
            "volatility": 0.18,
            "price": 180
        },
        {
            "ticker": "JNJ",
            "yield": 3.1,
            "momentum": 0.12,
            "volatility": 0.15,
            "price": 160
        },
        {
            "ticker": "PG",
            "yield": 2.4,
            "momentum": 0.10,
            "volatility": 0.14,
            "price": 155
        },
        {
            "ticker": "AVGO",
            "yield": 1.7,
            "momentum": 0.25,
            "volatility": 0.22,
            "price": 1250
        }
    ]

    return assets


def load_mock_portfolio():
    """
    Simulación de tu cartera actual
    """

    portfolio = {
        "TXN": {"weight": 0.07},
        "JNJ": {"weight": 0.04},
        "PG": {"weight": 0.10},
        "AVGO": {"weight": 0.18}
    }

    return portfolio


def run_monthly_investment(capital=200):
    """
    Motor completo de inversión mensual
    """

    market_assets = load_mock_market_data()

    scored_assets = score_assets(market_assets)

    portfolio = load_mock_portfolio()

    recommendation = recommend_purchase(
        scored_assets,
        portfolio,
        capital
    )

    return {
        "capital": capital,
        "recommendation": recommendation
    }
