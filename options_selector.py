"""
Capa de Opciones - traduce el régimen detectado por el Cerebro Matemático en
una estructura de opciones concreta, cumpliendo el requisito obligatorio del
hackathon: "All strategies must include options trading".

Mapeo de régimen -> estructura:
    TENDENCIAL_ALCISTA -> Long Call (ligeramente OTM)
    TENDENCIAL_BAJISTA -> Long Put (ligeramente OTM)
    RANGO_LATERAL       -> Iron Condor (venta de premium, riesgo definido)
    DEFENSIVO            -> Protective Put sobre posiciones abiertas / no abrir nuevas
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.trading.enums import ContractType, AssetStatus

from config import (
    TARGET_DTE_MIN,
    TARGET_DTE_MAX,
    OTM_PCT_DIRECTIONAL,
    IRON_CONDOR_SHORT_PCT,
    IRON_CONDOR_WING_PCT,
    PROTECTIVE_PUT_OTM_PCT,
)
from regime_engine import (
    TENDENCIAL_ALCISTA,
    TENDENCIAL_BAJISTA,
    RANGO_LATERAL,
    DEFENSIVO,
)


@dataclass
class OptionLeg:
    symbol: str          # símbolo OCC del contrato
    side: str             # "buy" o "sell"
    contract_type: str    # "call" o "put"
    strike: float
    expiry: date
    qty: int = 1


@dataclass
class OptionStrategy:
    regimen: str
    nombre: str
    legs: List[OptionLeg] = field(default_factory=list)
    max_riesgo_estimado: Optional[float] = None
    descripcion: str = ""


def obtener_cadena_opciones(trading_client, underlying_symbol: str, contract_type: ContractType,
                             strike_min: float = None, strike_max: float = None):
    """
    Consulta la cadena de opciones vigente vía Alpaca Trading API, acotada a
    la ventana de vencimiento objetivo (TARGET_DTE_MIN..TARGET_DTE_MAX).
    Sin este filtro, la API puede devolver contratos de cualquier
    vencimiento (incluyendo 0 DTE) y `_mas_cercano` los elegiría solo por
    cercanía de strike, ignorando el horizonte temporal de la estrategia.
    """
    hoy = date.today()
    req = GetOptionContractsRequest(
        underlying_symbols=[underlying_symbol],
        status=AssetStatus.ACTIVE,
        type=contract_type,
        strike_price_gte=str(strike_min) if strike_min else None,
        strike_price_lte=str(strike_max) if strike_max else None,
        expiration_date_gte=hoy + timedelta(days=TARGET_DTE_MIN),
        expiration_date_lte=hoy + timedelta(days=TARGET_DTE_MAX),
    )
    return trading_client.get_option_contracts(req).option_contracts


def construir_estrategia(regimen_result, trading_client, underlying_symbol: str) -> Optional[OptionStrategy]:
    """
    Punto de entrada principal: dado el resultado del régimen y el precio
    actual del subyacente, construye la estructura de opciones a ejecutar.
    Devuelve None si el régimen es DEFENSIVO y no hay posición que cubrir
    (es decir, "no operar" es la decisión correcta).
    """
    precio = regimen_result.precio
    regimen = regimen_result.regime

    if regimen == TENDENCIAL_ALCISTA:
        strike_obj = precio * (1 + OTM_PCT_DIRECTIONAL)
        contratos = obtener_cadena_opciones(
            trading_client, underlying_symbol, ContractType.CALL,
            strike_min=strike_obj * 0.98, strike_max=strike_obj * 1.05,
        )
        contrato = _mas_cercano(contratos, strike_obj)
        if not contrato:
            return None
        leg = OptionLeg(
            symbol=contrato.symbol, side="buy", contract_type="call",
            strike=float(contrato.strike_price), expiry=contrato.expiration_date,
        )
        return OptionStrategy(
            regimen=regimen, nombre="Long Call",
            legs=[leg],
            descripcion=f"Compra de call {leg.strike} venc. {leg.expiry} — "
                        f"expresa régimen tendencial alcista detectado por el algoritmo mutante.",
        )

    if regimen == TENDENCIAL_BAJISTA:
        strike_obj = precio * (1 - OTM_PCT_DIRECTIONAL)
        contratos = obtener_cadena_opciones(
            trading_client, underlying_symbol, ContractType.PUT,
            strike_min=strike_obj * 0.95, strike_max=strike_obj * 1.02,
        )
        contrato = _mas_cercano(contratos, strike_obj)
        if not contrato:
            return None
        leg = OptionLeg(
            symbol=contrato.symbol, side="buy", contract_type="put",
            strike=float(contrato.strike_price), expiry=contrato.expiration_date,
        )
        return OptionStrategy(
            regimen=regimen, nombre="Long Put",
            legs=[leg],
            descripcion=f"Compra de put {leg.strike} venc. {leg.expiry} — "
                        f"expresa régimen tendencial bajista detectado por el algoritmo mutante.",
        )

    if regimen == RANGO_LATERAL:
        return _construir_iron_condor(trading_client, underlying_symbol, precio, regimen)

    if regimen == DEFENSIVO:
        # La cobertura (protective put) se decide en risk_manager sobre posiciones
        # abiertas existentes; aquí no se abren posiciones nuevas.
        return None

    return None


def _mas_cercano(contratos, strike_obj: float):
    if not contratos:
        return None
    return min(contratos, key=lambda c: abs(float(c.strike_price) - strike_obj))


def _construir_iron_condor(trading_client, underlying_symbol: str, precio: float, regimen: str) -> Optional[OptionStrategy]:
    call_corta_obj = precio * (1 + IRON_CONDOR_SHORT_PCT)
    call_larga_obj = precio * (1 + IRON_CONDOR_SHORT_PCT + IRON_CONDOR_WING_PCT)
    put_corta_obj = precio * (1 - IRON_CONDOR_SHORT_PCT)
    put_larga_obj = precio * (1 - IRON_CONDOR_SHORT_PCT - IRON_CONDOR_WING_PCT)

    calls = obtener_cadena_opciones(trading_client, underlying_symbol, ContractType.CALL,
                                     strike_min=call_corta_obj * 0.95, strike_max=call_larga_obj * 1.05)
    puts = obtener_cadena_opciones(trading_client, underlying_symbol, ContractType.PUT,
                                    strike_min=put_larga_obj * 0.95, strike_max=put_corta_obj * 1.05)

    # Las 4 legs deben compartir vencimiento (un Iron Condor real no mezcla
    # expiraciones). Se fija primero el vencimiento común disponible más
    # cercano y recién ahí se elige el strike más cercano dentro de esa
    # expiración -- si se elige por strike antes de fijar la expiración,
    # cada leg puede terminar en un vencimiento distinto.
    expiraciones_comunes = sorted(
        {c.expiration_date for c in calls} & {p.expiration_date for p in puts}
    )
    if not expiraciones_comunes:
        return None
    vencimiento = expiraciones_comunes[0]
    calls = [c for c in calls if c.expiration_date == vencimiento]
    puts = [p for p in puts if p.expiration_date == vencimiento]

    call_corta = _mas_cercano(calls, call_corta_obj)
    call_larga = _mas_cercano(calls, call_larga_obj)
    put_corta = _mas_cercano(puts, put_corta_obj)
    put_larga = _mas_cercano(puts, put_larga_obj)

    if not all([call_corta, call_larga, put_corta, put_larga]):
        return None
    if len({call_corta.strike_price, call_larga.strike_price}) < 2 or \
       len({put_corta.strike_price, put_larga.strike_price}) < 2:
        return None  # cadena demasiado angosta: ala corta y larga cayeron en el mismo strike

    legs = [
        OptionLeg(call_corta.symbol, "sell", "call", float(call_corta.strike_price), call_corta.expiration_date),
        OptionLeg(call_larga.symbol, "buy", "call", float(call_larga.strike_price), call_larga.expiration_date),
        OptionLeg(put_corta.symbol, "sell", "put", float(put_corta.strike_price), put_corta.expiration_date),
        OptionLeg(put_larga.symbol, "buy", "put", float(put_larga.strike_price), put_larga.expiration_date),
    ]
    ancho_ala = abs(float(call_larga.strike_price) - float(call_corta.strike_price))

    return OptionStrategy(
        regimen=regimen, nombre="Iron Condor",
        legs=legs,
        max_riesgo_estimado=ancho_ala * 100,  # riesgo máx aprox por contrato (ancho de ala x 100)
        descripcion="Venta de premium (Iron Condor) — régimen de rango lateral, "
                     "monetiza baja volatilidad con riesgo definido por el ancho de las alas.",
    )
