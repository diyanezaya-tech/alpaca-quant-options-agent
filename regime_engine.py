"""
Cerebro Matemático - Algoritmo Mutante (adaptado del proyecto original)

Detecta el régimen de mercado vigente para un subyacente:
  - TENDENCIAL_ALCISTA
  - TENDENCIAL_BAJISTA
  - RANGO_LATERAL
  - DEFENSIVO   (alta volatilidad o stop loss activo o sentimiento negativo)

La lógica de conmutación es la misma del backend original (main.py del proyecto
"App Trading"), pero en vez de devolver una señal -1/0/1 sobre el subyacente,
devuelve un RÉGIMEN que luego la capa de opciones traduce a una estructura.
"""

from dataclasses import dataclass
import pandas as pd
import numpy as np

from config import (
    MEDIA_RAPIDA_VENTANA,
    MEDIA_LENTA_VENTANA,
    VOLATILIDAD_VENTANA,
    VOL_PROMEDIO_VENTANA,
    UMBRAL_TENDENCIA,
    VOL_SPIKE_MULT,
)


TENDENCIAL_ALCISTA = "TENDENCIAL_ALCISTA"
TENDENCIAL_BAJISTA = "TENDENCIAL_BAJISTA"
RANGO_LATERAL = "RANGO_LATERAL"
DEFENSIVO = "DEFENSIVO"


@dataclass
class RegimeResult:
    regime: str
    precio: float
    media_rapida: float
    media_lenta: float
    volatilidad: float
    vol_promedio: float
    razon: str


def calcular_indicadores(datos: pd.DataFrame) -> pd.DataFrame:
    """Replica el cálculo de indicadores del main.py original."""
    datos = datos.copy()
    datos["Media_Rapida"] = datos["Close"].rolling(window=MEDIA_RAPIDA_VENTANA).mean()
    datos["Media_Lenta"] = datos["Close"].rolling(window=MEDIA_LENTA_VENTANA).mean()
    datos["Volatilidad"] = datos["Close"].rolling(window=VOLATILIDAD_VENTANA).std()

    largo_datos = len(datos)
    ventana_vol = (
        VOL_PROMEDIO_VENTANA if largo_datos > 250 else max(10, int(largo_datos * 0.3))
    )
    datos["Vol_Promedio"] = datos["Volatilidad"].rolling(window=ventana_vol).mean()
    return datos.dropna().copy()


def detectar_regimen(datos_con_indicadores: pd.DataFrame, sentiment_score: float = 0.0,
                      sentiment_defensive: bool = False) -> RegimeResult:
    """
    Evalúa la última fila de datos (ya con indicadores calculados) y determina
    el régimen de mercado. El sentimiento de noticias actúa como interruptor
    de emergencia: si sentiment_defensive=True, fuerza DEFENSIVO sin importar
    el resto de las condiciones técnicas.
    """
    fila = datos_con_indicadores.iloc[-1]
    precio = float(fila["Close"])
    media_r = float(fila["Media_Rapida"])
    media_l = float(fila["Media_Lenta"])
    vol = float(fila["Volatilidad"])
    vol_prom = float(fila["Vol_Promedio"]) if not pd.isna(fila["Vol_Promedio"]) else vol

    # 1. Interruptor de emergencia por sentimiento (NLP)
    if sentiment_defensive:
        return RegimeResult(
            DEFENSIVO, precio, media_r, media_l, vol, vol_prom,
            razon=f"Sentimiento de noticias negativo (score={sentiment_score:.2f}) "
                  f"< umbral -> modo defensivo preventivo.",
        )

    # 2. Filtro de volatilidad extrema -> defensivo
    if vol > (vol_prom * VOL_SPIKE_MULT):
        return RegimeResult(
            DEFENSIVO, precio, media_r, media_l, vol, vol_prom,
            razon=f"Volatilidad ({vol:.2f}) > {VOL_SPIKE_MULT}x promedio ({vol_prom:.2f}).",
        )

    # 3. Filtro de ruido / confirmación de tendencia (umbral 0.7%)
    if abs(media_r - media_l) > (precio * UMBRAL_TENDENCIA):
        if media_r > media_l:
            return RegimeResult(
                TENDENCIAL_ALCISTA, precio, media_r, media_l, vol, vol_prom,
                razon="Media rápida > media lenta, separación > umbral de ruido.",
            )
        else:
            return RegimeResult(
                TENDENCIAL_BAJISTA, precio, media_r, media_l, vol, vol_prom,
                razon="Media rápida < media lenta, separación > umbral de ruido.",
            )

    # 4. Rango lateral (sin tendencia clara, volatilidad controlada)
    return RegimeResult(
        RANGO_LATERAL, precio, media_r, media_l, vol, vol_prom,
        razon="Sin separación significativa entre medias; volatilidad contenida.",
    )
