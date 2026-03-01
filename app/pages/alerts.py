from app.services.backend_client import get


def show_alerts():
    alerts = get("/alerts")
    print("Alerts:", alerts)


if __name__ == "__main__":
    show_alerts()
