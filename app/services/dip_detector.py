class DipDetector:

    def calculate_dip_score(self, price: float, ath: float) -> float:

        drawdown = (ath - price) / ath * 100

        if drawdown >= 20:
            return 10
        elif drawdown >= 10:
            return 7
        elif drawdown >= 5:
            return 4
        else:
            return 1
