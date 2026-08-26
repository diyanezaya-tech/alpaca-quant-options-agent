"""
Infraestructura de Ejecución - Blindaje de Alpaca

Envía las órdenes reales (paper) a Alpaca Trading API para las estrategias
de opciones construidas por options_selector.py. Cada leg se manda como
orden de mercado individual (Alpaca no soporta multi-leg nativo vía API
pública para todas las cuentas; se ejecuta pierna por pierna respetando
el orden correcto: cobertura primero cuando aplica).
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from options_selector import OptionStrategy, OptionLeg


def crear_cliente(api_key: str, secret_key: str, paper: bool = True) -> TradingClient:
    return TradingClient(api_key, secret_key, paper=paper)


def ejecutar_leg(client: TradingClient, leg: OptionLeg, qty: int = 1):
    side = OrderSide.BUY if leg.side == "buy" else OrderSide.SELL
    orden = MarketOrderRequest(
        symbol=leg.symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY,
    )
    return client.submit_order(orden)


def ejecutar_estrategia(client: TradingClient, estrategia: OptionStrategy, qty: int = 1):
    """
    Ejecuta todas las legs de una estrategia de opciones en orden.
    Para el Iron Condor se abren primero las patas COMPRADAS (cobertura) y
    luego las VENDIDAS (crédito): al mandar cada leg como orden de mercado
    individual (no como spread multi-leg nativo), una pata vendida sin su
    cobertura ya en la cuenta se evalúa como "uncovered" y Alpaca la
    rechaza -- confirmado en vivo contra la cuenta paper (error 40310000,
    "account not eligible to trade uncovered option contracts").
    """
    resultados = []
    legs_ordenadas = sorted(estrategia.legs, key=lambda l: 0 if l.side == "buy" else 1)
    for leg in legs_ordenadas:
        resultado = ejecutar_leg(client, leg, qty=qty)
        resultados.append(resultado)
    return resultados


def cerrar_posicion(client: TradingClient, symbol: str):
    return client.close_position(symbol)


def obtener_equity(client: TradingClient) -> float:
    cuenta = client.get_account()
    return float(cuenta.equity)


def obtener_posiciones(client: TradingClient):
    return client.get_all_positions()
