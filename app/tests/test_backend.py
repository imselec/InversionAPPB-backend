from app.services.backend_client import get


def test_connection():
    status = get("/system/status")
    print("Backend Status:", status)


if __name__ == "__main__":
    test_connection()
