import warnings
import logging

# Suppress yahooquery warnings and errors
warnings.filterwarnings('ignore')
logging.getLogger('yahooquery').setLevel(logging.CRITICAL)


class ValuationService:

    def get_valuation(self, tickers):

        from yahooquery import Ticker

        valuation = {}

        try:
            data = Ticker(tickers)

            for t in tickers:
                try:
                    summary = data.summary_detail.get(t, {})
                    # Check if summary is an error dict
                    if isinstance(summary, dict) and 'error' not in str(summary).lower():
                        valuation[t] = summary.get("trailingPE", 0)
                    else:
                        valuation[t] = 0
                except Exception:
                    valuation[t] = 0
        except Exception:
            # If entire request fails, return zeros for all tickers
            for t in tickers:
                valuation[t] = 0

        return valuation
