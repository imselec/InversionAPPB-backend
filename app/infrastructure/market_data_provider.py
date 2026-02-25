from functools import lru_cache


@lru_cache(maxsize=64)
def get_price(ticker: str) -> float | None:
    try:
        import yfinance as yf  # import interno, solo al llamar la función

        data = yf.Ticker(ticker)
        hist = data.history(period="5d")

        if hist.empty:
            return None

        return float(hist["Close"].iloc[-1])

    except Exception:
        return None
