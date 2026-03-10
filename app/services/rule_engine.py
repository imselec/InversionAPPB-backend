from typing import Dict


def evaluate_rules(asset: Dict, score: float, config: Dict) -> Dict:
    """
    Evalúa reglas duras del sistema y devuelve trazabilidad completa.
    No accede a base de datos.
    No imprime logs.
    Solo devuelve estructura auditable.
    """

    rules_config = config.get("rules", {})
    threshold = config.get("score_threshold", 0)

    reasons = []
    allowed = True

    ticker = asset.get("ticker")
    payout = asset.get("payout_ratio", 0)
    dividend_yield = asset.get("dividend_yield", 0)
    sector_weight = asset.get("sector_weight", 0)

    # 1️⃣ Exclusión explícita
    excluded = rules_config.get("exclude_tickers", [])
    if ticker in excluded:
        allowed = False
        reasons.append("Ticker excluido por configuración")

    # 2️⃣ Payout excesivo
    max_payout = rules_config.get("max_payout", 1)
    if payout > max_payout:
        allowed = False
        reasons.append("Payout superior al máximo permitido")

    # 3️⃣ Yield sospechoso
    max_yield = rules_config.get("max_yield", 1)
    if dividend_yield > max_yield:
        allowed = False
        reasons.append("Yield excesivo (posible trampa de valor)")

    # 4️⃣ Exposición sectorial
    max_sector = rules_config.get("max_sector_exposure", 1)
    if sector_weight > max_sector:
        allowed = False
        reasons.append("Sobreexposición sectorial")

    # 5️⃣ Umbral mínimo de score
    if score < threshold:
        allowed = False
        reasons.append("Score inferior al umbral mínimo")

    if allowed:
        reasons.append("Cumple todas las reglas")

    return {"ticker": ticker, "allowed": allowed, "reasons": reasons}
