def compute_allocation_scores(scored_assets, portfolio):

    allocation = []

    for asset in scored_assets:

        ticker = asset["ticker"]

        factor_score = asset["score"]
        dividend_yield = asset.get("yield", 0)

        target_weight = asset.get("target_weight", 0.1)

        actual_weight = portfolio.get(ticker, {}).get("weight", 0)

        underweight_bonus = target_weight - actual_weight

        allocation_score = (
            0.5 * factor_score
            + 0.3 * underweight_bonus
            + 0.2 * dividend_yield
        )

        asset["allocation_score"] = allocation_score

        allocation.append(asset)

    return sorted(allocation, key=lambda x: x["allocation_score"], reverse=True)


def recommend_purchase(scored_assets, portfolio, capital):

    ranked = compute_allocation_scores(scored_assets, portfolio)

    best = ranked[0]

    price = best.get("price", 100)

    shares = capital / price

    return {
        "ticker": best["ticker"],
        "shares": round(shares, 2),
        "amount": capital,
        "score": best["allocation_score"]
    }
