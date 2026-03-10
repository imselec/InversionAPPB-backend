class ScoringService:

    def compute_score(self, prices, dividends, valuation, volatility):

        scores = {}

        for ticker in prices:

            score = 0

            dividend_yield = dividends.get(ticker, {}).get("yield", 0)
            payout = dividends.get(ticker, {}).get("payout", 0)
            pe = valuation.get(ticker, 0)
            vol = volatility.get(ticker, 0)

            # Dividend yield
            score += dividend_yield * 40

            # payout ratio saludable
            if payout and payout < 0.65:
                score += 20

            # valoración
            if pe and pe < 20:
                score += 20

            # penalización por volatilidad
            score -= vol * 2

            scores[ticker] = round(score, 2)

        return scores
