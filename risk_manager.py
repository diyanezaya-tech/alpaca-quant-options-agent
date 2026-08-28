"""
Gestión de Riesgo Absoluto (heredada del proyecto original, adaptada a opciones)

Reglas institucionales que se preservan:
  1. Control de Costos: se descuenta comisión estimada por contrato antes de aceptar la operación.
  2. Filtro de Ruido: ya aplicado en regime_engine (umbral 0.7%).
  3. Stop Loss adaptativo estricto: 3% sobre el valor de la prima / del subyacente
     según el tipo de estructura.
  4. Límite de riesgo por operación: no arriesgar más del 2% del equity total.
  5. Protective Put: si hay posiciones abiertas y el régimen pasa a DEFENSIVO,
     se cubre en vez de liquidar de inmediato (a menos que no exista opción de cobertura).
"""

from dataclasses import dataclass
from typing import Optional

from config import (
    STOP_LOSS,
    TAKE_PROFIT_PCT,
    BREAKEVEN_ACTIVACION_PCT,
    IRON_CONDOR_PROFIT_TARGET_PCT,
    IRON_CONDOR_STOP_MULT,
    MAX_RISK_PER_TRADE_PCT,
    MAX_CONCURRENT_POSITIONS,
    OPTIONS_COMMISSION_PER_CONTRACT,
    PROTECTIVE_PUT_OTM_PCT,
)


@dataclass
class RiskDecision:
    aprobado: bool
    qty_sugerida: int
    razon: str


def evaluar_tamano_posicion(equity: float, prima_estimada_por_contrato: float,
                             posiciones_abiertas: int) -> RiskDecision:
    """
    Determina cuántos contratos se pueden abrir sin exceder el 2% de riesgo
    del equity total, y sin superar el máximo de posiciones concurrentes.
    """
    if posiciones_abiertas >= MAX_CONCURRENT_POSITIONS:
        return RiskDecision(False, 0, "Máximo de posiciones concurrentes alcanzado.")

    riesgo_maximo = equity * MAX_RISK_PER_TRADE_PCT
    costo_por_contrato = (prima_estimada_por_contrato * 100) + OPTIONS_COMMISSION_PER_CONTRACT

    if costo_por_contrato <= 0:
        return RiskDecision(False, 0, "Costo de contrato inválido.")

    qty = int(riesgo_maximo // costo_por_contrato)
    if qty < 1:
        return RiskDecision(False, 0, "El riesgo de 1 contrato ya excede el límite del 2% del equity.")

    return RiskDecision(True, qty, f"Aprobado: {qty} contrato(s), riesgo máx {riesgo_maximo:.2f} USD.")


def evaluar_stop_loss(precio_entrada_subyacente: float, precio_actual_subyacente: float,
                       es_alcista: bool, breakeven_activado: bool = False) -> bool:
    """
    Aplica el stop loss del 3% (regla heredada del algoritmo mutante) SIEMPRE
    sobre el precio del SUBYACENTE, nunca sobre la prima de la opción: la
    prima es apalancada (un 3% de movimiento del subyacente puede mover la
    prima 20-40%), así que un stop basado en la prima cierra posiciones por
    ruido normal en vez de por una señal real de mercado.

    es_alcista=True para long call / posiciones que ganan si el subyacente sube.
    es_alcista=False para long put / posiciones que ganan si el subyacente baja.

    breakeven_activado=True (ver evaluar_activacion_breakeven) reemplaza el
    umbral de -STOP_LOSS por 0%: la posición ya se movió lo suficiente a
    favor en algún momento, así que el stop pasa a proteger esa ganancia
    (no puede cerrar en pérdida neta desde la entrada) en vez de seguir
    tolerando hasta -3%.

    Devuelve True si se debe cerrar la posición.
    """
    if precio_entrada_subyacente <= 0:
        return False
    variacion = (precio_actual_subyacente - precio_entrada_subyacente) / precio_entrada_subyacente
    movimiento_en_contra = -variacion if es_alcista else variacion
    umbral = 0.0 if breakeven_activado else STOP_LOSS
    return movimiento_en_contra >= umbral


def evaluar_activacion_breakeven(precio_entrada_subyacente: float, precio_actual_subyacente: float,
                                  es_alcista: bool) -> bool:
    """
    True si el movimiento a favor del subyacente ya alcanzó
    BREAKEVEN_ACTIVACION_PCT (mitad del take profit) -- momento en que el
    stop loss de evaluar_stop_loss debe pasar a modo breakeven (0% desde
    entrada) para no dejar que una ganancia intermedia se revierta hasta
    -STOP_LOSS sin protección. Solo aplica a direccional: Iron Condor tiene
    su propio gate (evaluar_salida_iron_condor) sobre el crédito recibido,
    no sobre el subyacente.
    """
    if precio_entrada_subyacente <= 0:
        return False
    variacion = (precio_actual_subyacente - precio_entrada_subyacente) / precio_entrada_subyacente
    movimiento_a_favor = variacion if es_alcista else -variacion
    return movimiento_a_favor >= BREAKEVEN_ACTIVACION_PCT


def evaluar_take_profit(precio_entrada_subyacente: float, precio_actual_subyacente: float,
                         es_alcista: bool, take_profit_pct: float = None) -> bool:
    """
    Toma de ganancias a un múltiplo definido (2:1) del stop loss, sobre el
    mismo subyacente. Sin esta salida, las posiciones ganadoras se sostienen
    sin límite y el decaimiento de valor extrínseco (theta) cerca del
    vencimiento termina erosionando ganancias no realizadas.

    `take_profit_pct` es opcional (default: TAKE_PROFIT_PCT de config.py);
    permite overridearlo para grid search / validación out-of-sample sin
    mutar el módulo config.

    Devuelve True si se debe cerrar la posición por objetivo alcanzado.
    """
    if precio_entrada_subyacente <= 0:
        return False
    take_profit_pct = TAKE_PROFIT_PCT if take_profit_pct is None else take_profit_pct
    variacion = (precio_actual_subyacente - precio_entrada_subyacente) / precio_entrada_subyacente
    movimiento_a_favor = variacion if es_alcista else -variacion
    return movimiento_a_favor >= take_profit_pct


def evaluar_salida_iron_condor(pnl_flotante: float, credito_recibido: float) -> Optional[str]:
    """
    Gate de salida para estructuras de crédito (Iron Condor): pierden con el
    subyacente en cualquier dirección, así que evaluar_stop_loss/
    evaluar_take_profit (que asumen una dirección ganadora) no aplican.
    Reglas estándar de venta de premium, medidas sobre el crédito recibido:
      - stop: pérdida flotante llega a IRON_CONDOR_STOP_MULT veces el crédito.
      - take profit: se captura IRON_CONDOR_PROFIT_TARGET_PCT del crédito máximo.

    Devuelve el motivo ("stop_loss"/"take_profit") o None si sigue vigente.
    """
    if credito_recibido <= 0:
        return None
    if pnl_flotante <= -(IRON_CONDOR_STOP_MULT * credito_recibido):
        return "stop_loss"
    if pnl_flotante >= (IRON_CONDOR_PROFIT_TARGET_PCT * credito_recibido):
        return "take_profit"
    return None


def necesita_cobertura_defensiva(tiene_posiciones_abiertas: bool, regimen: str) -> bool:
    from regime_engine import DEFENSIVO
    return tiene_posiciones_abiertas and regimen == DEFENSIVO


def calcular_strike_proteccion(precio_subyacente: float) -> float:
    return round(precio_subyacente * (1 - PROTECTIVE_PUT_OTM_PCT), 2)