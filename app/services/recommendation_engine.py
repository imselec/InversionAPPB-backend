from .market_data_service import MarketDataService
from .dividend_service import DividendService
from .valuation_service import ValuationService
from .volatility_service import VolatilityService
from .scoring_service import ScoringService
from .portfolio_optimizer import PortfolioOptimizer


class RecommendationEngine:

    def __init__(self):

        self.market = MarketDataService()
        self.dividend = DividendService()
        self.valuation = ValuationService()
        self.volatility = VolatilityService()
        self.scoring = ScoringService()
        self.optimizer = PortfolioOptimizer()

    def generate_recommendations(self, tickers, capital):

        prices = self.market.get_prices(tickers)

        dividends = self.dividend.get_dividends(tickers)

        valuation = self.valuation.get_valuation(tickers)

        volatility = self.volatility.compute_volatility(prices)

        scores = self.scoring.compute_score(
            prices,
            dividends,
            valuation,
            volatility
        )

        portfolio = self.optimizer.allocate(scores, capital)

        return portfolio
