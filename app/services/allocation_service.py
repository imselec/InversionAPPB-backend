def allocate_capital(scored_assets, capital):

    # ordenar por score
    ranked = sorted(scored_assets, key=lambda x: x["score"], reverse=True)

    top = ranked[:3]

    allocation = []

    portion = capital / len(top)

    for asset in top:

        allocation.append({
            "ticker": asset["ticker"],
            "score": round(asset["score"], 2),
            "allocated_amount": round(portion, 2)
        })

    return allocation


class AllocationService:

    def allocate(self, capital: float, assets: list):

        if len(assets) == 0:
            return []

        allocation_per_asset = capital / len(assets)

        for asset in assets:
            asset["allocated_amount"] = round(allocation_per_asset, 2)

        return assets
