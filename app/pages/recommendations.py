from app.services.backend_client import get


def show_recommendations():
    candidates = get("/recommendations/candidates")
    recs = get("/recommendations")

    print("Candidates:", candidates)
    print("Recommendations:", recs)


if __name__ == "__main__":
    show_recommendations()
