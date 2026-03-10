class PortfolioOptimizer:

    def allocate(self, scores, capital):

        total = sum(scores.values())

        portfolio = []

        for t in scores:

            weight = scores[t] / total if total else 0

            portfolio.append({
                "ticker": t,
                "allocation": round(capital * weight, 2),
                "score": scores[t]
            })

        portfolio.sort(key=lambda x: x["score"], reverse=True)

        return portfolio
 
