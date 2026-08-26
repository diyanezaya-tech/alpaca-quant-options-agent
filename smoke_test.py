"""
Prueba de humo (sin red): genera un histórico sintético de precios y corre
el motor de régimen + backtest de opciones para verificar que la lógica no
tiene errores de ejecución. No reemplaza el backtest real (backtest.py),
que debes correr en tu PC con datos reales de Alpaca Market Data API.
"""

import numpy as np
import pandas as pd

np.random.seed(42)
n = 700
dates = pd.bdate_range("2023-01-01", periods=n)

# Random walk con drift + régimen de volatilidad cambiante, para ejercitar
# los tres regímenes (tendencial alcista, bajista, rango lateral).
drift = np.concatenate([
    np.full(200, 0.0009),   # tendencia alcista
    np.full(150, -0.0007),  # tendencia bajista
    np.full(200, 0.0000),   # rango lateral
    np.full(150, 0.0006),
])
vol = np.concatenate([
    np.full(200, 0.008),
    np.full(150, 0.012),
    np.full(200, 0.004),
    np.full(150, 0.009),
])
retornos = np.random.normal(drift, vol)
precios = 400 * np.cumprod(1 + retornos)

datos = pd.DataFrame({
    "Open": precios, "High": precios * 1.002, "Low": precios * 0.998,
    "Close": precios, "Volume": np.random.randint(1_000_000, 5_000_000, n),
}, index=dates)

from regime_engine import calcular_indicadores, detectar_regimen

datos_ind = calcular_indicadores(datos)
regimenes_vistos = set()
for i in range(len(datos_ind)):
    sub = datos_ind.iloc[: i + 1]
    if len(sub) < 5:
        continue
    r = detectar_regimen(sub)
    regimenes_vistos.add(r.regime)

print("Regímenes detectados en la serie sintética:", regimenes_vistos)
assert len(regimenes_vistos) >= 2, "El motor de régimen no está diferenciando escenarios."

from bs_pricing import bs_price
precio_call = bs_price(spot=400, strike=410, dte_days=30, vol_anual=0.20, option_type="call")
precio_put = bs_price(spot=400, strike=390, dte_days=30, vol_anual=0.20, option_type="put")
print(f"Precio BS call 410 (spot 400, 30d, vol 20%): {precio_call:.2f}")
print(f"Precio BS put 390 (spot 400, 30d, vol 20%): {precio_put:.2f}")
assert precio_call > 0 and precio_put > 0

from risk_manager import evaluar_tamano_posicion
decision = evaluar_tamano_posicion(equity=100_000, prima_estimada_por_contrato=3.5, posiciones_abiertas=0)
print("Risk gate de ejemplo:", decision)
assert decision.aprobado

print("\nSMOKE TEST OK: el motor de régimen, el pricing BS y los risk gates funcionan sin errores.")
