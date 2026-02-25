# app/core/config.py

# Plan mensual de inversión
PLAN_MENSUAL_USD = 200

# Restricciones para España
RESTRICTED_ES = ["SCHD"]
REPLACEMENTS_ES = {"SCHD": "VTI"}

# Benchmark sectorial configurable
BENCHMARK_TARGET = {
    "Technology": 0.27,
    "Healthcare": 0.13,
    "Financials": 0.11,
    "Consumer Discretionary": 0.10,
    "Industrials": 0.09,
    "Energy": 0.03,
    "Utilities": 0.03,
    "Materials": 0.03,
    "Real Estate": 0.02,
    "Communication Services": 0.05,
    "Consumer Staples": 0.14
}
