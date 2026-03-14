@router.get("/portfolio/snapshot")
def portfolio_snapshot():

    portfolio = load_portfolio()

    market = MarketDataService()
    dividend = DividendService()

    positions = []
    total_value = 0
    total_dividends = 0

    for asset in portfolio:

        ticker = asset["ticker"]
        shares = asset["shares"]

        try:
            price = market.get_price(ticker)
        except Exception:
            price = 0

        try:
            div = dividend.get_annual_dividend(ticker)
        except Exception:
            div = 0

        value = price * shares
        annual_div = div * shares

        total_value += value
        total_dividends += annual_div

        positions.append(
            {
                "ticker": ticker,
                "shares": shares,
                "price": price,
                "value": value,
                "annual_dividend": annual_div
            }
        )

    yield_pct = 0
    if total_value > 0:
        yield_pct = (total_dividends / total_value) * 100

    return {
        "total_value": round(total_value, 2),
        "annual_dividends": round(total_dividends, 2),
        "yield": round(yield_pct, 2),
        "positions": positions
    }
