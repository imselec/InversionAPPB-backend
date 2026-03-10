from app.core.cache import SimpleCache


class MarketDataService:

    def __init__(self):

        self.cache = SimpleCache()

    def get_prices(self, tickers):

        cached = self.cache.get("prices")

        if cached:
            return cached

        from yahooquery import Ticker

        data = Ticker(tickers)

        prices = {}

        for t in tickers:

            p = data.price.get(t, {})

            prices[t] = p.get("regularMarketPrice", 0)

        self.cache.set("prices", prices)

        return prices
