class ValuationService:

    def get_valuation(self, tickers):

        from yahooquery import Ticker

        data = Ticker(tickers)

        valuation = {}

        for t in tickers:

            summary = data.summary_detail.get(t, {})

            valuation[t] = summary.get("trailingPE", 0)

        return valuation
