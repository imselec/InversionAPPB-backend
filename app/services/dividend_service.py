class DividendService:

    def get_dividends(self, tickers):

        from yahooquery import Ticker

        data = Ticker(tickers)

        result = {}

        for t in tickers:

            summary = data.summary_detail.get(t, {})

            result[t] = {
                "yield": summary.get("dividendYield", 0),
                "payout": summary.get("payoutRatio", 0)
            }

        return result
