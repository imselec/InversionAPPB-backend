import csv
import os
from sqlalchemy.orm import Session
from app import db, models

# Ruta del CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "portfolio.csv")

def update_portfolio():
    session: Session = db.SessionLocal()
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            print("Encabezados CSV detectados:", reader.fieldnames)

            for row in reader:
                ticker = row["ticker"].strip()
                quantity = float(row["quantity"].strip())
                
                # Asignamos avg_price si existe, sino 0
                price = float(row.get("price", 0))

                # Buscar si el activo ya existe
                existing = session.query(models.Portfolio).filter_by(symbol=ticker).first()
                if existing:
                    # Actualizar valores existentes
                    existing.quantity = quantity
                    existing.avg_price = price
                    session.add(existing)
                else:
                    # Crear nuevo activo si no existía
                    asset = models.Portfolio(
                        symbol=ticker,
                        quantity=quantity,
                        avg_price=price
                    )
                    session.add(asset)
        session.commit()
        print("Actualización de portfolio completada ✅")
    except Exception as e:
        print(f"Error en actualización: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    update_portfolio()
