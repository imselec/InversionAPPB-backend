# Inversión mensual
PLAN_MENSUAL_USD = 200

# Activos no permitidos en España
RESTRICTED_ES = {"SCHD", "VTI", "VOO"}

# Reemplazos automáticos UCITS
REPLACEMENTS_ES = {
    "SCHD": "SCHD.UCITS",
    "VTI": "VUSA.L",
    "VOO": "VUSA.L"
}

# Scoring
SCORING_WEIGHTS = {
    "dividend_yield": 0.7,
    "sector_priority": {
        "Tech": 1.0,
        "Healthcare": 0.8,
        "Energy": 0.6,
        "Finance": 0.7,
        "Other": 0.5
    }
}
