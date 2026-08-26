"""
Aproximación Black-Scholes para valorar opciones en el backtest histórico.

Alpaca no provee históricos de opciones baratos/gratuitos con la misma
profundidad que los de acciones, así que para validar
la estrategia offline (en este entorno sin salida a Alpaca) se estima el
precio de cada leg con Black-Scholes usando la volatilidad realizada del
subyacente como proxy de volatilidad implícita. Es una aproximación
razonable para pruebas de coherencia direccional del P&L, no para precisión
de trading real (que sí usará precios de mercado reales vía Alpaca).
"""

import math

RISK_FREE_RATE = 0.045  # referencia T-bill corto plazo


def _norm_cdf(x: float) -> float:
    """CDF de la normal estándar sin depender de scipy (evita bloqueos de DLL en Windows)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, dte_days: float, vol_anual: float,
             option_type: str, r: float = RISK_FREE_RATE) -> float:
    if dte_days <= 0:
        return max(0.0, (spot - strike) if option_type == "call" else (strike - spot))

    t = dte_days / 365.0
    vol_anual = max(vol_anual, 0.01)

    d1 = (math.log(spot / strike) + (r + 0.5 * vol_anual ** 2) * t) / (vol_anual * math.sqrt(t))
    d2 = d1 - vol_anual * math.sqrt(t)

    if option_type == "call":
        precio = spot * _norm_cdf(d1) - strike * math.exp(-r * t) * _norm_cdf(d2)
    else:
        precio = strike * math.exp(-r * t) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)

    return max(precio, 0.01)