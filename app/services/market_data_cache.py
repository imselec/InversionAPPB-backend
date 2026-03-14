import time
from app.services.market_data_service import MarketDataService


class MarketDataCache:

    def __init__(self, ttl=300):
        self.ttl = ttl
        self.cache = {}
        self.last_update = 0
        self.market = MarketDataService()

    def get_prices(self, tickers):

        now = time.time()

        # devolver cache si aún es válido
        if self.cache and (now - self.last_update < self.ttl):
            return {t: self.cache.get(t, 0) for t in tickers}

        prices = {}

        try:
            # intento de obtener precios
            prices = self.market.get_prices(tickers)

        except Exception as e:
            print("Market data error:", e)
            prices = {}

        # guardar en cache
        for t in tickers:
            self.cache[t] = prices.get(t, 0)

        self.last_update = now

        return {t: self.cache.get(t, 0) for t in tickers}
