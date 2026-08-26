"""
Test de rendimiento REAL con ciclo de vida corto (DTE 1-3 dias), ver
PROMPT_TEST_RENDIMIENTO_REAL.md.

Objetivo: medir resultados de trades reales (apertura -> cierre) contra la
cuenta paper PA3EGUEP0QCV en 1-2 dias de calendario, en vez de esperar los
6-8 dias que tarda en resolverse un trade con el DTE 7-14 real del concurso
(config.py, usado por live_agent.py). NO toca config.py ni live_agent.py:
el DTE corto vive solo en este script (monkeypatch de options_selector
despues de importarlo), y el estado se persiste aparte
(positions_state_test.json) para no pisar el estado del loop real.

Reusa los modulos reales (regime_engine, sentiment_engine,
options_selector, risk_manager, executor/cli_executor) -- misma logica de
decision y ejecucion que live_agent.py, no una reimplementacion.

Uso:
    python test_rendimiento_dte_corto.py --use-cli --max-hours 36
    python test_rendimiento_dte_corto.py --use-cli --interval-seconds 300 --max-cycles 5
"""

import argparse
import csv
import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

import options_selector
from regime_engine import calcular_indicadores, detectar_regimen, DEFENSIVO
from sentiment_engine import analizar_sentimiento, obtener_titulares_alpaca
from options_selector import construir_estrategia
from bs_pricing import bs_price
from backtest import volatilidad_anualizada
from risk_manager import evaluar_tamano_posicion, evaluar_stop_loss, evaluar_take_profit, evaluar_salida_iron_condor
from executor import crear_cliente, ejecutar_estrategia, obtener_equity, obtener_posiciones
import cli_executor

load_dotenv()

# --- DTE corto SOLO para este script: monkeypatch de options_selector      ---
# (config.py / live_agent.py NUNCA se tocan; el loop real sigue con DTE 7-14) ---
TEST_DTE_MIN = 1
TEST_DTE_MAX = 3
TEST_EXIT_DTE_BUFFER = 1  # proporcional al buffer=2 sobre DTE 7-14 del loop real
options_selector.TARGET_DTE_MIN = TEST_DTE_MIN
options_selector.TARGET_DTE_MAX = TEST_DTE_MAX

# Universo del test: SPY/AAPL/QQQ (los del concurso) + 2 mas liquidos con
# cadena de opciones activa, para juntar mas muestras en poco tiempo.
SYMBOLS_TEST = ["SPY", "AAPL", "QQQ", "MSFT", "NVDA"]

STATE_FILE = Path(__file__).parent / "positions_state_test.json"
LOG_FILE = Path(__file__).parent / "test_rendimiento_dte_corto.log"
TRADES_CSV = Path(__file__).parent / "trades_test_dte_corto.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
_logger = logging.getLogger("test_dte_corto")


def log(msg: str):
    _logger.info(msg)


def cargar_estado() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"No se pudo leer {STATE_FILE.name} ({e}); se arranca con estado vacío.")
    return {}


def guardar_estado(estado: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, default=str)
    tmp.replace(STATE_FILE)


def registrar_trade_cerrado(symbol, entrada, motivo, pnl_usd, pnl_pct, dias_abierto):
    nuevo = not TRADES_CSV.exists()
    with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["closed_at_utc", "symbol", "regimen", "estructura", "motivo",
                        "dias_abierto", "pnl_usd", "pnl_pct", "opened_at"])
        w.writerow([
            datetime.utcnow().isoformat(timespec="seconds"), symbol, entrada["regimen"],
            entrada["kind"], motivo, dias_abierto, round(pnl_usd, 2), round(pnl_pct, 2),
            entrada["opened_at"],
        ])
    log(f"[TRADE CERRADO] {symbol} {entrada['kind']} motivo={motivo} "
        f"dias={dias_abierto} pnl=${pnl_usd:.2f} ({pnl_pct:+.2f}%)")


def descargar_datos_alpaca(data_client, symbol, dias=200):
    req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day,
                            start=datetime.now() - timedelta(days=dias))
    barras = data_client.get_stock_bars(req).df
    if barras.empty:
        return pd.DataFrame()
    if isinstance(barras.index, pd.MultiIndex):
        barras = barras.xs(symbol, level=0)
    barras = barras.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                     "close": "Close", "volume": "Volume"})
    return barras[["Open", "High", "Low", "Close", "Volume"]]


def _prima_estimada_para_sizing(legs, precio_actual, vol_anual):
    """Igual que en live_agent.py: BS con vol realizada como proxy, para que el
    sizing en vivo replique el que ya se valido en el backtest."""
    if len(legs) == 1:
        leg = legs[0]
        dte = max((leg.expiry - date.today()).days, 0)
        return bs_price(precio_actual, leg.strike, dte, vol_anual, leg.contract_type)

    credito_por_share = 0.0
    for leg in legs:
        dte = max((leg.expiry - date.today()).days, 0)
        p = bs_price(precio_actual, leg.strike, dte, vol_anual, leg.contract_type)
        credito_por_share += p if leg.side == "sell" else -p
    credito_usd = credito_por_share * 100
    strikes_call = sorted(l.strike for l in legs if l.contract_type == "call")
    strikes_put = sorted(l.strike for l in legs if l.contract_type == "put")
    ancho_ala = max(strikes_call[-1] - strikes_call[0], strikes_put[-1] - strikes_put[0])
    return (ancho_ala * 100 - credito_usd) / 100


def _cerrar_legs(client, option_symbols, posiciones_alpaca, use_cli):
    """
    IMPORTANTE (seguridad): solo cierra symbols que vienen de option_symbols,
    que a su vez SOLO sale del estado propio de este script
    (positions_state_test.json). El loop real (positions_state.json) es un
    dict completamente separado en memoria y en disco -- nunca se leen sus
    symbols aca, asi que no hay forma de que este script cierre una leg del
    loop real por accidente aunque comparta la misma cuenta.
    """
    presentes = {getattr(p, "symbol", None) for p in posiciones_alpaca}
    fallidas = []
    for occ_symbol in option_symbols:
        if occ_symbol not in presentes:
            continue
        try:
            if use_cli:
                cli_executor.cerrar_posicion_cli(occ_symbol, confirmar_real=True)
            else:
                client.close_position(occ_symbol)
        except Exception as e:
            log(f"  Error cerrando leg {occ_symbol}: {e}")
            fallidas.append(occ_symbol)
    return (len(fallidas) == 0), fallidas


def evaluar_y_cerrar_posicion(client, symbol, entrada, precio_actual, posiciones_alpaca, use_cli):
    expiry = date.fromisoformat(entrada["expiry"])
    dte_restante = (expiry - date.today()).days
    dias_abierto = (date.today() - date.fromisoformat(entrada["opened_at"][:10])).days

    legs_alpaca = [p for p in posiciones_alpaca if getattr(p, "symbol", None) in entrada["option_symbols"]]
    pnl_flotante = sum(float(p.unrealized_pl) for p in legs_alpaca) if legs_alpaca else None
    cost_basis_abs = sum(abs(float(p.cost_basis)) for p in legs_alpaca) if legs_alpaca else None

    cerrar, motivo = False, ""

    if entrada["kind"] == "direccional":
        if evaluar_stop_loss(entrada["precio_entrada_subyacente"], precio_actual, entrada["es_alcista"]):
            cerrar, motivo = True, "stop_loss"
        elif evaluar_take_profit(entrada["precio_entrada_subyacente"], precio_actual, entrada["es_alcista"]):
            cerrar, motivo = True, "take_profit"
        elif dte_restante <= TEST_EXIT_DTE_BUFFER:
            cerrar, motivo = True, "vencimiento"
    else:
        credito = entrada.get("credito_recibido")
        if credito is None and len(legs_alpaca) == len(entrada["option_symbols"]):
            credito = -sum(float(p.cost_basis) for p in legs_alpaca)
            entrada["credito_recibido"] = credito
            log(f"{symbol}: crédito recibido confirmado: {credito:.2f} USD.")
        if credito is not None and pnl_flotante is not None:
            motivo_condor = evaluar_salida_iron_condor(pnl_flotante, credito)
            if motivo_condor:
                cerrar, motivo = True, motivo_condor
        if not cerrar and dte_restante <= TEST_EXIT_DTE_BUFFER:
            cerrar, motivo = True, "vencimiento"

    log(f"{symbol}: posición {entrada['kind']} ({dias_abierto}d abierta, {dte_restante}d restantes a venc., "
        f"pnl_flotante={pnl_flotante if pnl_flotante is not None else 'N/D'}) -> "
        f"{'cerrar por ' + motivo if cerrar else 'se mantiene'}")

    if not cerrar:
        return False

    ok, fallidas = _cerrar_legs(client, entrada["option_symbols"], posiciones_alpaca, use_cli)
    if not ok:
        log(f"{symbol}: no se pudieron cerrar todas las legs ({fallidas}); se reintenta el próximo ciclo.")
        return False

    pnl_usd = pnl_flotante if pnl_flotante is not None else 0.0
    base_pct = credito if entrada["kind"] == "iron_condor" and entrada.get("credito_recibido") else cost_basis_abs
    pnl_pct = (pnl_usd / base_pct * 100) if base_pct else 0.0
    registrar_trade_cerrado(symbol, entrada, motivo, pnl_usd, pnl_pct, dias_abierto)
    return True


def _campo(resultado, nombre):
    if isinstance(resultado, dict):
        return resultado.get(nombre, "?")
    return getattr(resultado, nombre, "?")


def ciclo(client, data_client, symbol, estado, use_cli):
    log(f"--- Evaluando {symbol} (test DTE {TEST_DTE_MIN}-{TEST_DTE_MAX}) ---")

    datos = descargar_datos_alpaca(data_client, symbol, dias=200)
    if datos.empty:
        log("Sin datos históricos, se omite este ciclo.")
        return
    datos_ind = calcular_indicadores(datos)
    if datos_ind.empty:
        log("Datos insuficientes tras calcular indicadores.")
        return

    precio_actual = float(datos_ind["Close"].iloc[-1])
    vol_serie = volatilidad_anualizada(datos)
    vol_anual = float(vol_serie.iloc[-1]) if not pd.isna(vol_serie.iloc[-1]) else 0.2

    posiciones = obtener_posiciones(client)

    try:
        titulares = obtener_titulares_alpaca(symbol, os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))
    except Exception as e:
        log(f"No se pudieron obtener titulares ({e}); se usa sentimiento neutro.")
        titulares = []

    sentimiento = analizar_sentimiento(symbol, titulares)
    regimen = detectar_regimen(datos_ind, sentimiento.score, sentimiento.defensive)
    log(f"Régimen: {regimen.regime} -> {regimen.razon}")

    entrada = estado.get(symbol)
    if entrada is not None:
        cerrada = evaluar_y_cerrar_posicion(client, symbol, entrada, precio_actual, posiciones, use_cli)
        if cerrada:
            del estado[symbol]
            guardar_estado(estado)
        return

    if regimen.regime == DEFENSIVO:
        log("Régimen defensivo sin posiciones abiertas -> no se opera este ciclo.")
        return

    estrategia = construir_estrategia(regimen, client, symbol)
    if estrategia is None:
        log("No se pudo construir una estrategia de opciones viable (cadena no disponible a DTE 1-3).")
        return

    equity = obtener_equity(client)
    prima_estimada = _prima_estimada_para_sizing(estrategia.legs, precio_actual, vol_anual)
    decision = evaluar_tamano_posicion(equity, prima_estimada, len(estado))
    log(f"Risk gate: {decision.razon}")
    if not decision.aprobado:
        return

    log(f"Ejecutando estrategia (test, {'CLI' if use_cli else 'SDK'}): "
        f"{estrategia.nombre} ({len(estrategia.legs)} leg(s)) — {estrategia.descripcion}")

    if use_cli:
        resultados = cli_executor.ejecutar_estrategia_cli(estrategia, qty=decision.qty_sugerida, dry_run=False)
    else:
        resultados = ejecutar_estrategia(client, estrategia, qty=decision.qty_sugerida)
    for r in resultados:
        log(f"Orden enviada: {_campo(r, 'symbol')} status={_campo(r, 'status')}")

    kind = "iron_condor" if len(estrategia.legs) == 4 else "direccional"
    nueva_entrada = {
        "kind": kind,
        "option_symbols": [leg.symbol for leg in estrategia.legs],
        "precio_entrada_subyacente": precio_actual,
        "expiry": estrategia.legs[0].expiry.isoformat() if hasattr(estrategia.legs[0].expiry, "isoformat")
                  else str(estrategia.legs[0].expiry),
        "regimen": regimen.regime,
        "opened_at": datetime.now().isoformat(timespec="seconds"),
    }
    if kind == "direccional":
        nueva_entrada["es_alcista"] = estrategia.legs[0].contract_type == "call"
    else:
        nueva_entrada["credito_recibido"] = None

    estado[symbol] = nueva_entrada
    guardar_estado(estado)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=int, default=300,
                         help="Segundos entre ciclos (default 300 = 5 min; mas rapido que el loop real "
                              "porque acá el objetivo es velocidad de iteración, no fidelidad al concurso).")
    parser.add_argument("--max-cycles", type=int, default=None)
    parser.add_argument("--max-hours", type=float, default=None,
                         help="Termina el loop despues de N horas de pared (ademas de --max-cycles, si se da).")
    parser.add_argument("--use-cli", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise SystemExit("Falta ALPACA_API_KEY / ALPACA_SECRET_KEY en .env")

    client = crear_cliente(api_key, secret_key, paper=True)
    data_client = StockHistoricalDataClient(api_key, secret_key)

    cuenta = client.get_account()
    log(f"Conectado a cuenta {cuenta.id} ({cuenta.account_number}) — equity: {cuenta.equity}")
    if cuenta.account_number != "PA3EGUEP0QCV":
        raise SystemExit(f"ABORT: account_number {cuenta.account_number} != PA3EGUEP0QCV esperado.")
    log(f"*** TEST RENDIMIENTO REAL — DTE {TEST_DTE_MIN}-{TEST_DTE_MAX}, buffer={TEST_EXIT_DTE_BUFFER}, "
        f"símbolos={SYMBOLS_TEST}, estado separado en {STATE_FILE.name} ***")
    if args.use_cli:
        log("*** MODO CLI ***")

    estado = cargar_estado()
    if estado:
        log(f"Estado de test cargado: posiciones abiertas en {list(estado.keys())}")

    inicio = datetime.now()
    ciclos_corridos = 0
    while args.max_cycles is None or ciclos_corridos < args.max_cycles:
        if args.max_hours is not None and (datetime.now() - inicio).total_seconds() > args.max_hours * 3600:
            log(f"Se alcanzó --max-hours={args.max_hours}. Terminando.")
            break
        for symbol in SYMBOLS_TEST:
            try:
                ciclo(client, data_client, symbol, estado, args.use_cli)
            except Exception as e:
                log(f"Error evaluando {symbol}: {e}")

        ciclos_corridos += 1
        if args.max_cycles is not None and ciclos_corridos >= args.max_cycles:
            log(f"Se alcanzó --max-cycles={args.max_cycles}. Terminando.")
            break

        log(f"Ciclo de test completo. Durmiendo {args.interval_seconds}s...\n")
        try:
            time.sleep(args.interval_seconds)
        except KeyboardInterrupt:
            log("Interrumpido por el usuario. Saliendo.")
            break


if __name__ == "__main__":
    main()
