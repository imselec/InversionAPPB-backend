# app/scripts/seed_portfolio.py
from app.database import Base, SessionLocal, engine
from app.models.portfolio import Portfolio

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Datos de tu portafolio actual
portfolio_data = [
    {"ticker": "AVGO", "shares": 1.1901, "avg_price": None, "current_price": None},
    {"ticker": "PG", "shares": 1.9549, "avg_price": None, "current_price": None},
    {"ticker": "NEE", "shares": 2.4958, "avg_price": None, "current_price": None},
    {"ticker": "JNJ", "shares": 0.1614, "avg_price": None, "current_price": None},
    {"ticker": "UPS", "shares": 0.5577, "avg_price": None, "current_price": None},
    {"ticker": "TXN", "shares": 0.3157, "avg_price": None, "current_price": None},
    {"ticker": "CVX", "shares": 1.0876, "avg_price": None, "current_price": None},
    {"ticker": "XOM", "shares": 1.0643, "avg_price": None, "current_price": None},
    {"ticker": "ABBV", "shares": 0.3574, "avg_price": 224.8, "current_price": 224.8},
    {"ticker": "LMT", "shares": 0.2592, "avg_price": None, "current_price": None},
    {"ticker": "O", "shares": 1.4206, "avg_price": None, "current_price": None},
    {"ticker": "JPM", "shares": 0.5515, "avg_price": None, "current_price": None},
    {"ticker": "DUK", "shares": 0.2092, "avg_price": None, "current_price": None},
    {"ticker": "KO", "shares": 0.5996, "avg_price": None, "current_price": None},
    {"ticker": "PEP", "shares": 0.4824, "avg_price": None, "current_price": None},
    {"ticker": "BLK", "shares": 0.1384, "avg_price": 1093.7, "current_price": 1093.7},
]


def seed_portfolio():
    db = SessionLocal()
    try:
        # Limpiar tabla antes de insertar (opcional)
        db.query(Portfolio).delete()
        db.commit()

        # Insertar cada registro
        for item in portfolio_data:
            db_portfolio = Portfolio(**item)
            db.add(db_portfolio)

        db.commit()
        print("✅ Portafolio inicializado correctamente")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al inicializar portafolio: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_portfolio()
