import statistics


class VolatilityService:

    def compute_volatility(self, prices):

        vol = {}

        for t, price in prices.items():

            vol[t] = abs(price * 0.02)  # placeholder

        return vol
        return vol
