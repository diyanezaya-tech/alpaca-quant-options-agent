"""
Backtesting de la estrategia de opciones sobre el algoritmo mutante.

Usa Alpaca Market Data API para el subyacente + Black-Scholes para valorar
las opciones sintéticamente (Alpaca no ofrece históricos de opciones con
la misma profundidad). Requiere red real -> correr en tu PC, no en el
sandbox cloud. Sirve para validar la coherencia de la lógica antes de
operar en paper real.

Uso:
    python backtest.py --symbol SPY --years 3
"""

import argparse
import os
from datetime import timedelta, datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from config import (
    STARTING_BALANCE,
    OTM_PCT_DIRECTIONAL,
    IRON_CONDOR_SHORT_PCT,
    IRON_CONDOR_WING_PCT,
    TARGET_DTE_MIN,
    TARGET_DTE_MAX,
    OPTIONS_COMMISSION_PER_CONTRACT,
    MAX_RISK_PER_TRADE_PCT,
    TAKE_PROFIT_PCT,
    EXIT_DTE_BUFFER,
)
from regime_engine import (
    calcular_indicadores,
    detectar_regimen,
    TENDENCIAL_ALCISTA,
    TENDENCIAL_BAJISTA,
    RANGO_LATERAL,
    DEFENSIVO,
)
from risk_manager import evaluar_stop_loss, evaluar_take_profit, evaluar_salida_iron_condor
from bs_pricing import bs_price

load_dotenv()


def descargar_datos_alpaca(symbol: str, years: int) -> pd.DataFrame:
    """Trae barras diarias históricas vía Alpaca Market Data API (requiere .env con API keys)."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise SystemExit("Falta ALPACA_API_KEY / ALPACA_SECRET_KEY en .env")

    client = StockHistoricalDataClient(api_key, secret_key)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=365 * years),
    )
    barras = client.get_stock_bars(req).df
    if barras.empty:
        return pd.DataFrame()
    if isinstance(barras.index, pd.MultiIndex):
        barras = barras.xs(symbol, level=0)
    barras = barras.rename(columns={
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
    })
    return barras[["Open", "High", "Low", "Close", "Volume"]]


def volatilidad_anualizada(datos: pd.DataFrame, ventana: int = 15) -> pd.Series:
    retornos = datos["Close"].pct_change()
    return retornos.rolling(ventana).std() * np.sqrt(252)


def _valor_piernas(legs: list, precio: float, dte: float, vol_anual: float, qty: int) -> float:
    """
    Marca a mercado un conjunto de piernas de opciones (genérico: sirve para
    una sola pierna direccional o las 4 piernas de un Iron Condor).

    Cada pierna es {"type": "call"/"put", "side": "buy"/"sell", "strike": float}.
    Piernas compradas suman valor (activo); piernas vendidas restan (pasivo:
    lo que costaría recomprarlas). El costo neto de apertura se calcula con
    esta misma función al abrir, así que un débito neto da un número positivo
    y un crédito neto da uno negativo -- pnl_flotante = valor_actual - costo_neto
    funciona igual para ambos casos sin necesitar una convención de signos aparte.
    """
    total = 0.0
    for leg in legs:
        precio_leg = bs_price(precio, leg["strike"], max(dte, 0), vol_anual, leg["type"])
        signo = 1 if leg["side"] == "buy" else -1
        total += signo * precio_leg * 100 * qty
    return total


def _construir_iron_condor_sintetico(precio: float) -> tuple:
    """Strikes del Iron Condor, replicando la construcción de options_selector.py."""
    call_corta = round(precio * (1 + IRON_CONDOR_SHORT_PCT), 2)
    call_larga = round(precio * (1 + IRON_CONDOR_SHORT_PCT + IRON_CONDOR_WING_PCT), 2)
    put_corta = round(precio * (1 - IRON_CONDOR_SHORT_PCT), 2)
    put_larga = round(precio * (1 - IRON_CONDOR_SHORT_PCT - IRON_CONDOR_WING_PCT), 2)
    legs = [
        {"type": "call", "side": "sell", "strike": call_corta},
        {"type": "call", "side": "buy", "strike": call_larga},
        {"type": "put", "side": "sell", "strike": put_corta},
        {"type": "put", "side": "buy", "strike": put_larga},
    ]
    ancho_ala = max(call_larga - call_corta, put_corta - put_larga)
    return legs, ancho_ala


def preparar_datos(symbol: str, years: int = 3) -> pd.DataFrame:
    """
    Descarga el histórico y calcula indicadores UNA sola vez sobre la serie
    completa. Necesario para poder partir el resultado en ventanas
    entrenamiento/prueba (validación out-of-sample) sin recalcular medias
    móviles y volatilidad con distinta ventana de warm-up en cada slice
    -- eso invalidaría la comparación entre ventanas.
    """
    datos = descargar_datos_alpaca(symbol, years)
    if datos.empty:
        raise SystemExit(f"Sin datos históricos para {symbol} (Alpaca Market Data API)")

    datos["Vol_Anual"] = volatilidad_anualizada(datos)
    datos_ind = calcular_indicadores(datos)
    datos_ind["Vol_Anual"] = datos["Vol_Anual"]
    return datos_ind.dropna()


def simular_sobre_datos(datos_ind: pd.DataFrame, take_profit_pct: float = None,
                         exit_dte_buffer: int = None) -> dict:
    """
    Corre la simulación sobre una serie de datos ya preparada (con
    indicadores calculados). Recibe `take_profit_pct` / `exit_dte_buffer`
    como parámetros opcionales (default: los de config.py) para poder hacer
    grid search y validación out-of-sample sin mutar el módulo config ni
    recargar módulos.
    """
    if datos_ind.empty:
        raise SystemExit("Serie de datos vacía para simular.")

    take_profit_pct = TAKE_PROFIT_PCT if take_profit_pct is None else take_profit_pct
    exit_dte_buffer = EXIT_DTE_BUFFER if exit_dte_buffer is None else exit_dte_buffer

    equity = STARTING_BALANCE
    equity_curve = []
    posicion_abierta = None  # dict con detalles de la posición (direccional o iron_condor)
    trades = []

    for i in range(len(datos_ind)):
        fila = datos_ind.iloc[i]
        fecha = datos_ind.index[i]
        precio = float(fila["Close"])
        vol_anual = float(fila["Vol_Anual"]) if not pd.isna(fila["Vol_Anual"]) else 0.2

        sub = datos_ind.iloc[: i + 1]
        regimen = detectar_regimen(sub)

        # --- Gestionar posición abierta (mark-to-market + salida) ---
        if posicion_abierta is not None:
            dte_restante = (posicion_abierta["expiry"] - fecha).days
            valor_actual = _valor_piernas(
                posicion_abierta["legs"], precio, dte_restante, vol_anual, posicion_abierta["qty"],
            )
            pnl_flotante = valor_actual - posicion_abierta["costo_neto_apertura"]

            cerrar = False
            motivo = ""

            if posicion_abierta["kind"] == "direccional":
                # Gates de riesgo (risk_manager): stop loss y take profit sobre
                # el SUBYACENTE (igual que el algoritmo original), no sobre la
                # prima: la prima es apalancada y un stop/target basado en su
                # variación cierra posiciones por ruido normal de la opción.
                precio_entrada = posicion_abierta["precio_entrada_subyacente"]
                es_alcista = posicion_abierta["legs"][0]["type"] == "call"
                if evaluar_stop_loss(precio_entrada, precio, es_alcista):
                    cerrar, motivo = True, "stop_loss"
                elif evaluar_take_profit(precio_entrada, precio, es_alcista, take_profit_pct):
                    cerrar, motivo = True, "take_profit"
                elif dte_restante <= exit_dte_buffer:
                    cerrar, motivo = True, "vencimiento"
            else:  # iron_condor: gate propio de venta de premium (risk_manager),
                   # los gates direccionales no aplican -- pierde en cualquier dirección.
                credito_recibido = -posicion_abierta["costo_neto_apertura"]
                motivo_condor = evaluar_salida_iron_condor(pnl_flotante, credito_recibido)
                if motivo_condor:
                    cerrar, motivo = True, motivo_condor
                elif dte_restante <= exit_dte_buffer:
                    cerrar, motivo = True, "vencimiento"

            if cerrar:
                n_legs = len(posicion_abierta["legs"])
                comision = OPTIONS_COMMISSION_PER_CONTRACT * n_legs * posicion_abierta["qty"]
                pnl_neto = pnl_flotante - comision
                equity += pnl_neto
                trades.append({
                    "fecha_cierre": fecha, "regimen": posicion_abierta["regimen"],
                    "tipo": posicion_abierta["kind"], "pnl": pnl_neto, "motivo": motivo,
                })
                posicion_abierta = None

        # --- Abrir nueva posición si no hay una abierta y el régimen lo permite ---
        if posicion_abierta is None and regimen.regime != DEFENSIVO:
            # Punto medio del rango objetivo (options_selector.py filtra la
            # cadena real a [TARGET_DTE_MIN, TARGET_DTE_MAX] y toma el
            # vencimiento disponible mas cercano dentro de esa ventana; el
            # punto medio es la aproximacion sintetica mas fiel sin cadena real).
            dte_entrada = (TARGET_DTE_MIN + TARGET_DTE_MAX) // 2
            expiry = fecha + timedelta(days=dte_entrada)

            if regimen.regime in (TENDENCIAL_ALCISTA, TENDENCIAL_BAJISTA):
                if regimen.regime == TENDENCIAL_ALCISTA:
                    strike = round(precio * (1 + OTM_PCT_DIRECTIONAL), 2)
                    tipo = "call"
                else:
                    strike = round(precio * (1 - OTM_PCT_DIRECTIONAL), 2)
                    tipo = "put"

                legs = [{"type": tipo, "side": "buy", "strike": strike}]
                costo_por_contrato = _valor_piernas(legs, precio, dte_entrada, vol_anual, 1)
                costo_contrato_total = costo_por_contrato + OPTIONS_COMMISSION_PER_CONTRACT
                riesgo_max = equity * MAX_RISK_PER_TRADE_PCT
                qty = max(int(riesgo_max // costo_contrato_total), 0) if costo_contrato_total > 0 else 0

                if qty >= 1:
                    costo_neto_apertura = _valor_piernas(legs, precio, dte_entrada, vol_anual, qty)
                    equity -= OPTIONS_COMMISSION_PER_CONTRACT * len(legs) * qty
                    posicion_abierta = {
                        "kind": "direccional", "legs": legs, "expiry": expiry,
                        "qty": qty, "costo_neto_apertura": costo_neto_apertura,
                        "regimen": regimen.regime, "precio_entrada_subyacente": precio,
                    }

            else:  # RANGO_LATERAL -> Iron Condor completo (4 legs, crédito neto)
                legs, ancho_ala = _construir_iron_condor_sintetico(precio)
                credito_por_contrato = -_valor_piernas(legs, precio, dte_entrada, vol_anual, 1)

                if credito_por_contrato > 0:
                    # credito_por_contrato ya viene en dólares por contrato
                    # (_valor_piernas multiplica por 100 internamente); ancho_ala
                    # está en puntos de precio, así que ese sí se escala por 100.
                    riesgo_por_contrato = (
                        ancho_ala * 100 - credito_por_contrato
                        + OPTIONS_COMMISSION_PER_CONTRACT * len(legs)
                    )
                    riesgo_max = equity * MAX_RISK_PER_TRADE_PCT
                    qty = max(int(riesgo_max // riesgo_por_contrato), 0) if riesgo_por_contrato > 0 else 0

                    if qty >= 1:
                        costo_neto_apertura = _valor_piernas(legs, precio, dte_entrada, vol_anual, qty)
                        equity -= OPTIONS_COMMISSION_PER_CONTRACT * len(legs) * qty
                        posicion_abierta = {
                            "kind": "iron_condor", "legs": legs, "expiry": expiry,
                            "qty": qty, "costo_neto_apertura": costo_neto_apertura,
                            "regimen": regimen.regime, "precio_entrada_subyacente": precio,
                        }

        equity_curve.append({"fecha": fecha, "equity": equity, "regimen": regimen.regime})

    curva = pd.DataFrame(equity_curve).set_index("fecha")
    rendimiento_pct = (curva["equity"].iloc[-1] / STARTING_BALANCE - 1) * 100

    rendimiento_mercado = (datos_ind["Close"].iloc[-1] / datos_ind["Close"].iloc[0] - 1) * 100

    return {
        "rendimiento_estrategia_pct": round(rendimiento_pct, 2),
        "rendimiento_mercado_pct": round(rendimiento_mercado, 2),
        "n_trades": len(trades),
        "trades": trades,
        "curva": curva,
    }


def simular(symbol: str, years: int = 3, take_profit_pct: float = None,
            exit_dte_buffer: int = None) -> dict:
    """Punto de entrada de conveniencia: descarga + prepara + simula sobre el histórico completo."""
    datos_ind = preparar_datos(symbol, years)
    resultado = simular_sobre_datos(datos_ind, take_profit_pct, exit_dte_buffer)
    resultado["symbol"] = symbol
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--years", type=int, default=3)
    args = parser.parse_args()

    resultado = simular(args.symbol, args.years)
    print(f"\n=== Backtest {resultado['symbol']} ({args.years} años) ===")
    print(f"Rendimiento estrategia (opciones): {resultado['rendimiento_estrategia_pct']}%")
    print(f"Rendimiento mercado pasivo (buy & hold subyacente): {resultado['rendimiento_mercado_pct']}%")
    print(f"Número de trades: {resultado['n_trades']}")
