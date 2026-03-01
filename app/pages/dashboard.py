from app.services.backend_client import get


def show_dashboard():
    snapshot = get("/portfolio/snapshot")
    time_series = get("/portfolio/time-series")
    yield_history = get("/portfolio/yield-history")
    dividends = get("/portfolio/dividends-by-asset")

    print("Portfolio Snapshot:", snapshot)
    print("Time Series:", time_series)
    print("Yield History:", yield_history)
    print("Dividends by Asset:", dividends)


if __name__ == "__main__":
    show_dashboard()
