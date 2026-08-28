"""
Agente en vivo - punto de entrada para correr durante la semana del hackathon.

Uso (en tu computador, con Python 3.10+ y las dependencias instaladas):

    python live_agent.py                              # loop normal, cada 15 min, ejecución vía SDK (alpaca-py)
    python live_agent.py --dry-run                     # evalúa todo pero NO envía órdenes
    python live_agent.py --dry-run --interval-seconds 30 --max-cycles 2   # ciclo rápido de prueba
    python live_agent.py --dry-run --use-cli --max-cycles 1   # modo agente-por-CLI, sin enviar nada real
    python live_agent.py --use-cli                     # ejecución real vía el Alpaca CLI (subprocess) en vez del SDK

Requiere el archivo .env con ALPACA_API_KEY / ALPACA_SECRET_KEY de la
cuenta paper dedicada al concurso ("Alpaca Hackathon 2026").

Este script corre un ciclo (por defecto cada 15 minutos en horario de
mercado) que, por símbolo:
  1. Revisa si hay una posición abierta (persistida en positions_state.json)
     y la cierra si toca stop loss / take profit / buffer de vencimiento.
  2. Si no hay posición abierta y el régimen lo permite: descarga datos,
     calcula el régimen (regime_engine), consulta sentimiento
     (sentiment_engine), construye la estructura de opciones
     (options_selector), aplica los risk gates (risk_manager) y ejecuta
     (executor).

Estado y logging:
  - El estado de posiciones abiertas persiste en positions_state.json para
    sobrevivir reinicios (necesario para poder evaluar el stop loss/take
    profit sobre el precio de entrada del SUBYACENTE, que Alpaca no expone
    directamente sobre una posición de opción).
  - Los logs se escriben en consola y en live_agent.log, para poder revisar
    qué hizo el agente aunque se haya cerrado la terminal.

Correr como servicio / sobrevivir reinicios: ver README.md, sección
"Correr el agente en vivo".
"""

import argparse
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

from config import SYMBOLS, MAX_CONCURRENT_POSITIONS, EXIT_DTE_BUFFER
from regime_engine import calcular_indicadores, detectar_regimen, DEFENSIVO
from sentiment_engine import analizar_sentimiento, obtener_titulares_alpaca
from options_selector import construir_estrategia
from bs_pricing import bs_price
from backtest import volatilidad_anualizada
from risk_manager import (
    evaluar_tamano_posicion,
    necesita_cobertura_defensiva,
    evaluar_stop_loss,
    evaluar_take_profit,
    evaluar_salida_iron_condor,
)
from executor import crear_cliente, ejecutar_estrategia, obtener_equity, obtener_posiciones
import cli_executor

load_dotenv()

STATE_DIR = Path(os.getenv("STATE_DIR", Path(__file__).parent))
STATE_FILE = STATE_DIR / "positions_state.json"
LOG_FILE = Path(__file__).parent / "live_agent.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
_logger = logging.getLogger("live_agent")


def log(msg: str):
    _logger.info(msg)


# --- Persistencia de estado (sobrevive reinicios) ---

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
    tmp.replace(STATE_FILE)  # escritura atómica: evita corromper el archivo si se cae a mitad de escritura


def descargar_datos_alpaca(data_client: StockHistoricalDataClient, symbol: str, dias: int = 200) -> pd.DataFrame:
    """Trae barras diarias históricas del subyacente vía Alpaca Market Data API."""
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=dias),
    )
    barras = data_client.get_stock_bars(req).df
    if barras.empty:
        return pd.DataFrame()
    if isinstance(barras.index, pd.MultiIndex):
        barras = barras.xs(symbol, level=0)
    barras = barras.rename(columns={
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
    })
    return barras[["Open", "High", "Low", "Close", "Volume"]]


DEFAULT_CICLO_SEGUNDOS = 15 * 60  # cada 15 minutos


def _prima_estimada_para_sizing(legs: list, precio_actual: float, vol_anual: float) -> float:
    """
    Estima la prima "por contrato" que espera `risk_manager.evaluar_tamano_posicion`
    (que multiplica por 100 y suma la comisión), usando Black-Scholes con la
    volatilidad realizada como proxy -- la misma metodología que usa
    backtest.py para dimensionar posiciones, así que el sizing en vivo
    replica el que ya se validó en el backtest.

    Para direccional (1 leg) es la prima de esa leg. Para el Iron Condor
    (4 legs) `evaluar_tamano_posicion` reconstruye el riesgo máximo como
    prima*100 + comisión, así que se devuelve (riesgo_máximo_usd / 100) para
    que esa reconstrucción caiga en el riesgo real de la estructura (ancho
    de ala menos crédito neto), no en la prima de una sola leg.
    """
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
    riesgo_usd = ancho_ala * 100 - credito_usd
    return riesgo_usd / 100


def _cerrar_legs(client, option_symbols: list, posiciones_alpaca: list, dry_run: bool,
                  use_cli: bool = False) -> tuple:
    """
    Cierra cada leg de la posición individualmente. Devuelve (ok, fallidas).

    Solo intenta cerrar legs que Alpaca todavía reporta como abiertas: una
    leg que ya no aparece en `posiciones_alpaca` se considera resuelta (se
    cerró en un intento previo, expiró, etc.), evitando que un fallo parcial
    dejara ese símbolo bloqueado para siempre reintentando cerrar legs que
    ya no existen (cada leg fallida antes se reintentaba indefinidamente).

    `use_cli=True` cierra vía el Alpaca CLI (cli_executor) en vez del SDK.
    El subcomando `alpaca position close` no soporta `--dry-run`, así que en
    modo dry-run esta función solo loggea la intención igual que en modo SDK
    -- nunca invoca el CLI mientras dry_run sea True.
    """
    presentes = {getattr(p, "symbol", None) for p in posiciones_alpaca}
    fallidas = []
    for occ_symbol in option_symbols:
        if occ_symbol not in presentes:
            continue
        if dry_run:
            log(f"  [DRY-RUN] cerraría {occ_symbol}{' (via CLI)' if use_cli else ''}")
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


def evaluar_y_cerrar_posicion(client, symbol: str, entrada: dict, precio_actual: float,
                               posiciones_alpaca: list, dry_run: bool, use_cli: bool = False) -> bool:
    """
    Evalúa si la posición abierta de `symbol` (según el estado persistido)
    debe cerrarse, y la cierra si corresponde. Devuelve True si se cerró
    (o se habría cerrado, en dry-run) y debe borrarse del estado.
    """
    expiry = date.fromisoformat(entrada["expiry"])
    dte_restante = (expiry - date.today()).days

    legs_alpaca = [p for p in posiciones_alpaca if getattr(p, "symbol", None) in entrada["option_symbols"]]
    pnl_flotante = sum(float(p.unrealized_pl) for p in legs_alpaca) if legs_alpaca else None

    cerrar = False
    motivo = ""

    if entrada["kind"] == "direccional":
        if evaluar_stop_loss(entrada["precio_entrada_subyacente"], precio_actual, entrada["es_alcista"]):
            cerrar, motivo = True, "stop_loss"
        elif evaluar_take_profit(entrada["precio_entrada_subyacente"], precio_actual, entrada["es_alcista"]):
            cerrar, motivo = True, "take_profit"
        elif dte_restante <= EXIT_DTE_BUFFER:
            cerrar, motivo = True, "vencimiento"

    else:  # iron_condor: gate propio sobre el crédito recibido (no direccional)
        credito = entrada.get("credito_recibido")
        if credito is None:
            if len(legs_alpaca) == len(entrada["option_symbols"]):
                credito = -sum(float(p.cost_basis) for p in legs_alpaca)
                entrada["credito_recibido"] = credito
                log(f"{symbol}: crédito recibido confirmado por Alpaca: {credito:.2f} USD.")
            else:
                log(f"{symbol}: aún no se puede confirmar el crédito recibido del condor "
                    f"({len(legs_alpaca)}/{len(entrada['option_symbols'])} legs visibles en la cuenta); "
                    f"se reintenta el próximo ciclo.")
        if credito is not None and pnl_flotante is not None:
            motivo_condor = evaluar_salida_iron_condor(pnl_flotante, credito)
            if motivo_condor:
                cerrar, motivo = True, motivo_condor
        if not cerrar and dte_restante <= EXIT_DTE_BUFFER:
            cerrar, motivo = True, "vencimiento"

    log(f"{symbol}: posición {entrada['kind']} abierta ({dte_restante}d restantes, "
        f"pnl_flotante={pnl_flotante if pnl_flotante is not None else 'N/D'}) -> "
        f"{'cerrar por ' + motivo if cerrar else 'se mantiene'}")

    if not cerrar:
        return False

    ok, fallidas = _cerrar_legs(client, entrada["option_symbols"], posiciones_alpaca, dry_run, use_cli)
    if not ok:
        log(f"{symbol}: no se pudieron cerrar todas las legs ({fallidas}); se reintenta el próximo ciclo.")
        return False

    log(f"{symbol}: posición cerrada ({motivo}).")
    return True


def _campo(resultado, nombre: str):
    """Lee un campo de un resultado de orden sea objeto SDK (alpaca-py) o dict (CLI/JSON)."""
    if isinstance(resultado, dict):
        return resultado.get(nombre, "?")
    return getattr(resultado, nombre, "?")


def ciclo(client, data_client, symbol: str, estado: dict, dry_run: bool, use_cli: bool = False):
    log(f"--- Evaluando {symbol} ---")

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
        titulares = obtener_titulares_alpaca(
            symbol, os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
        )
    except Exception as e:
        log(f"No se pudieron obtener titulares ({e}); se usa sentimiento neutro.")
        titulares = []

    sentimiento = analizar_sentimiento(symbol, titulares)
    regimen = detectar_regimen(datos_ind, sentimiento.score, sentimiento.defensive)
    log(f"Régimen: {regimen.regime} -> {regimen.razon}")
    log(sentimiento.detalle)

    # --- Gestionar posición abierta persistida para este símbolo (siempre,
    # independiente del régimen: el stop loss/take profit/vencimiento debe
    # evaluarse todos los ciclos, no solo cuando el régimen sigue siendo el
    # mismo que al abrir) ---
    entrada = estado.get(symbol)
    if entrada is not None:
        cerrada = evaluar_y_cerrar_posicion(client, symbol, entrada, precio_actual, posiciones, dry_run, use_cli)
        if cerrada:
            if not dry_run:
                del estado[symbol]
                guardar_estado(estado)
            return  # no abrir una nueva posición en el mismo ciclo en que se cerró la anterior

        if necesita_cobertura_defensiva(True, regimen.regime):
            log("Régimen DEFENSIVO con posición abierta -> se prioriza cobertura/cierre (revisar manualmente "
                "o extender lógica de protective put automático); no se fuerza el cierre solo por régimen.")
        return  # sigue abierta: no evaluar apertura de una nueva mientras tanto

    if regimen.regime == DEFENSIVO:
        log("Régimen defensivo sin posiciones abiertas -> no se opera este ciclo.")
        return

    estrategia = construir_estrategia(regimen, client, symbol)
    if estrategia is None:
        log("No se pudo construir una estrategia de opciones viable (cadena no disponible).")
        return

    equity = obtener_equity(client)
    prima_estimada = _prima_estimada_para_sizing(estrategia.legs, precio_actual, vol_anual)
    # Cuenta posiciones por símbolo/estrategia abiertas (estado), no legs individuales:
    # un solo Iron Condor son 4 legs y contarlas crudo saturaría MAX_CONCURRENT_POSITIONS de inmediato.
    decision = evaluar_tamano_posicion(equity, prima_estimada, len(estado))
    log(f"Risk gate: {decision.razon}")

    if not decision.aprobado:
        return

    log(f"{'[DRY-RUN] ' if dry_run else ''}Ejecutando estrategia{' (via Alpaca CLI)' if use_cli else ' (via SDK)'}: "
        f"{estrategia.nombre} ({len(estrategia.legs)} leg(s)) — {estrategia.descripcion}")

    if dry_run:
        for leg in estrategia.legs:
            log(f"  [DRY-RUN] {leg.side} {leg.contract_type} {leg.symbol} strike={leg.strike} "
                f"venc={leg.expiry} qty={decision.qty_sugerida}")
        return

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
        nueva_entrada["credito_recibido"] = None  # se confirma con cost_basis real en el próximo ciclo

    estado[symbol] = nueva_entrada
    guardar_estado(estado)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                         help="Evalúa el ciclo completo (régimen, estrategia, risk gates) pero no envía "
                              "órdenes reales ni cierra posiciones -- solo loggea la intención.")
    parser.add_argument("--interval-seconds", type=int, default=DEFAULT_CICLO_SEGUNDOS,
                         help=f"Segundos entre ciclos (default: {DEFAULT_CICLO_SEGUNDOS}).")
    parser.add_argument("--max-cycles", type=int, default=None,
                         help="Corre solo N ciclos y termina (default: infinito). Útil para pruebas.")
    parser.add_argument("--use-cli", action="store_true",
                         help="Ejecuta órdenes reales vía el Alpaca CLI (subprocess, cli_executor.py) en vez "
                              "del SDK alpaca-py -- modo 'agente autónomo operando por CLI'. Solo afecta "
                              "apertura/cierre de posiciones; datos, régimen y cadena de opciones siguen "
                              "usando alpaca-py igual que siempre. No cambia nada en modo --dry-run.")
    args = parser.parse_args()

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise SystemExit("Falta ALPACA_API_KEY / ALPACA_SECRET_KEY en .env")

    client = crear_cliente(api_key, secret_key, paper=True)
    data_client = StockHistoricalDataClient(api_key, secret_key)

    cuenta = None
    for intento in range(1, 6):
        try:
            cuenta = client.get_account()
            break
        except Exception as e:
            log(f"No se pudo conectar a Alpaca (intento {intento}/5): {e}")
            if intento < 5:
                time.sleep(min(5 * intento, 30))
    if cuenta is None:
        raise SystemExit("No se pudo conectar a Alpaca tras 5 intentos. Revisa red / API keys y reintenta.")

    log(f"Conectado a cuenta {cuenta.id} — equity: {cuenta.equity} — estado: {cuenta.status}")
    if args.dry_run:
        log("*** MODO DRY-RUN: no se enviarán órdenes ni se cerrarán posiciones reales ***")
    if args.use_cli:
        log("*** MODO CLI: la ejecución real (apertura/cierre) va por el Alpaca CLI (subprocess), "
            "no por el SDK alpaca-py ***")

    estado = cargar_estado()
    if estado:
        log(f"Estado cargado de {STATE_FILE.name}: posiciones abiertas en {list(estado.keys())}")

    ciclos_corridos = 0
    while args.max_cycles is None or ciclos_corridos < args.max_cycles:
        for symbol in SYMBOLS:
            try:
                ciclo(client, data_client, symbol, estado, args.dry_run, args.use_cli)
            except Exception as e:
                log(f"Error evaluando {symbol}: {e}")

        ciclos_corridos += 1
        if args.max_cycles is not None and ciclos_corridos >= args.max_cycles:
            log(f"Se alcanzó --max-cycles={args.max_cycles}. Terminando.")
            break

        log(f"Ciclo completo. Durmiendo {args.interval_seconds}s...\n")
        try:
            time.sleep(args.interval_seconds)
        except KeyboardInterrupt:
            log("Interrumpido por el usuario. Saliendo.")
            break


if __name__ == "__main__":
    main()
