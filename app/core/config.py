# app/core/config.py

import copy

# Configuración base
PLAN_MENSUAL_USD = 200

# Restricciones para España
RESTRICTED_ES = ["SCHD"]
REPLACEMENTS_ES = {"SCHD": "VTI"}

# Benchmark sectorial configurable
BENCHMARK_TARGET = {
    "monthly_capital": 300,
    "score_threshold": 0.55,
    "weights": {
        "yield": 0.35,
        "momentum": 0.25,
        "quality": 0.25,
        "undervaluation": 0.15,
    },
    "rules": {
        "max_sector_exposure": 0.35,
        "max_payout": 0.85,
        "max_yield": 0.08,
        "exclude_tickers": ["SCHD"],
    },
}


def load_config() -> dict:
    """
    Devuelve un snapshot de la configuración completa para la inversión mensual.
    Se retorna copia para evitar modificaciones accidentales.
    """
    return {
        "PLAN_MENSUAL_USD": PLAN_MENSUAL_USD,
        "RESTRICTED_ES": copy.deepcopy(RESTRICTED_ES),
        "REPLACEMENTS_ES": copy.deepcopy(REPLACEMENTS_ES),
        "BENCHMARK_TARGET": copy.deepcopy(BENCHMARK_TARGET),
    }
