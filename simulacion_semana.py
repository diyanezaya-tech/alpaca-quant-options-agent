"""
Simulacion dia-por-dia del agente sobre una semana historica puntual (ver
PROMPT_SIMULACION_SEMANA_ESPECIFICA.md). A diferencia de backtest.py (que
reporta solo el retorno acumulado de 3 anios), este script loguea la
decision de CADA dia dentro de la ventana pedida, con el mismo nivel de
detalle que live_agent.log -- como si el agente hubiera estado corriendo
en vivo esa semana.

Reusa el motor real de backtest.py: regime_engine (indicadores + regimen),
y la construccion de estrategias con Black-Scholes como proxy (misma
limitacion metodologica del backtest de 3 anios -- Alpaca no tiene
historico de precios de opciones reales para revender fechas pasadas).
NO usa options_selector.py directamente: ese modulo consulta la cadena de
opciones REAL de Alpaca con fecha de vencimiento relativa a HOY, lo cual
seria incorrecto para simular una fecha pasada.

Usa los parametros ACTUALES de config.py (DTE 7-14, buffer 2,
IRON_CONDOR_SHORT_PCT=0.03) -- la calibracion con la que va a correr el
agente durante la semana del concurso.

Uso:
    python simulacion_semana.py --symbol SPY --start 2026-08-01 --end 2026-08-07
    python simulacion_semana.py  # corre SPY, AAPL, QQQ con el rango default
"""

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd

from config import (
    STARTING_BALANCE, OTM_PCT_DIRECTIONAL, IRON_CONDOR_SHORT_PCT,
    IRON_CONDOR_WING_PCT, TARGET_DTE_MIN, TARGET_DTE_MAX,
    OPTIONS_COMMISSION_PER_CONTRACT, MAX_RISK_PER_TRADE_PCT,
    TAKE_PROFIT_PCT, EXIT_DTE_BUFFER,
)
from regime_engine import detectar_regimen, TENDENCIAL_ALCISTA, TENDENCIAL_BAJISTA, DEFENSIVO
from risk_manager import evaluar_stop_loss, evaluar_take_profit, evaluar_salida_iron_condor
from backtest import preparar_datos, _valor_piernas, _construir_iron_condor_sintetico

DEFAULT_START = "2026-08-01"
DEFAULT_END = "2026-08-07"
SYMBOLS_DEFAULT = ["SPY", "AAPL", "QQQ"]


def simular_semana(symbol: str, start: str, end: str, out_lines: list) -> dict:
    start_dt = pd.Timestamp(start, tz="UTC")
    end_dt = pd.Timestamp(end, tz="UTC")

    out_lines.append(f"\n{'='*70}\n{symbol} — simulación {start} a {end} "
                      f"(config actual: DTE {TARGET_DTE_MIN}-{TARGET_DTE_MAX}, "
                      f"buffer={EXIT_DTE_BUFFER}, IRON_CONDOR_SHORT_PCT={IRON_CONDOR_SHORT_PCT})\n{'='*70}")

    # years=1 alcanza de sobra de warm-up real para una ventana de ago-2026
    # (MA200/Vol_Promedio necesitan ~200 filas previas; calcular_indicadores
    # ya las descarta con dropna() antes de que preparar_datos devuelva la serie).
    datos_ind = preparar_datos(symbol, years=1)

    fechas_normalizadas = datos_ind.index.normalize()
    ventana = datos_ind[(fechas_normalizadas >= start_dt) & (fechas_normalizadas <= end_dt)]
    if ventana.empty:
        out_lines.append(f"SIN DATOS DE MERCADO para {symbol} entre {start} y {end} "
                          f"(fines de semana/feriados, o rango fuera del histórico disponible).")
        return {"symbol": symbol, "sin_datos": True}

    dias_calendario = pd.date_range(start_dt, end_dt, freq="D")
    fechas_con_sesion = set(fechas_normalizadas)
    dias_sin_sesion = [d.date().isoformat() for d in dias_calendario if d not in fechas_con_sesion]
    if dias_sin_sesion:
        out_lines.append(f"Sin sesión de mercado (feriado/fin de semana) en: {', '.join(dias_sin_sesion)}")

    idx_inicio = datos_ind.index.get_loc(ventana.index[0])
    idx_fin = datos_ind.index.get_loc(ventana.index[-1])

    equity = STARTING_BALANCE
    posicion_abierta = None
    pnl_realizado_semana = 0.0
    trades_cerrados = []

    for i in range(idx_inicio, idx_fin + 1):
        fila = datos_ind.iloc[i]
        fecha = datos_ind.index[i]
        precio = float(fila["Close"])
        vol_anual = float(fila["Vol_Anual"]) if not pd.isna(fila["Vol_Anual"]) else 0.2

        sub = datos_ind.iloc[: i + 1]
        regimen = detectar_regimen(sub)

        out_lines.append(f"\n[{fecha.date()}] {symbol} — Close=${precio:.2f} | régimen={regimen.regime}")
        out_lines.append(f"    razón: {regimen.razon} (MA_rapida={regimen.media_rapida:.2f} "
                          f"MA_lenta={regimen.media_lenta:.2f} vol={regimen.volatilidad:.2f} "
                          f"vol_prom={regimen.vol_promedio:.2f})")

        if posicion_abierta is not None:
            dte_restante = (posicion_abierta["expiry"] - fecha).days
            valor_actual = _valor_piernas(posicion_abierta["legs"], precio, dte_restante, vol_anual, posicion_abierta["qty"])
            pnl_flotante = valor_actual - posicion_abierta["costo_neto_apertura"]

            cerrar, motivo = False, ""
            if posicion_abierta["kind"] == "direccional":
                precio_entrada = posicion_abierta["precio_entrada_subyacente"]
                es_alcista = posicion_abierta["legs"][0]["type"] == "call"
                if evaluar_stop_loss(precio_entrada, precio, es_alcista):
                    cerrar, motivo = True, "stop_loss"
                elif evaluar_take_profit(precio_entrada, precio, es_alcista, TAKE_PROFIT_PCT):
                    cerrar, motivo = True, "take_profit"
                elif dte_restante <= EXIT_DTE_BUFFER:
                    cerrar, motivo = True, "vencimiento (buffer DTE)"
            else:
                credito_recibido = -posicion_abierta["costo_neto_apertura"]
                motivo_condor = evaluar_salida_iron_condor(pnl_flotante, credito_recibido)
                if motivo_condor:
                    cerrar, motivo = True, motivo_condor
                elif dte_restante <= EXIT_DTE_BUFFER:
                    cerrar, motivo = True, "vencimiento (buffer DTE)"

            if cerrar:
                n_legs = len(posicion_abierta["legs"])
                comision = OPTIONS_COMMISSION_PER_CONTRACT * n_legs * posicion_abierta["qty"]
                pnl_neto = pnl_flotante - comision
                equity += pnl_neto
                pnl_realizado_semana += pnl_neto
                dias_abierto = (fecha - posicion_abierta["fecha_apertura"]).days
                out_lines.append(f"    CIERRA posición {posicion_abierta['kind']} — motivo={motivo}, "
                                  f"abierta {dias_abierto}d, P&L realizado=${pnl_neto:+.2f}")
                trades_cerrados.append({"fecha_apertura": posicion_abierta["fecha_apertura"], "fecha_cierre": fecha,
                                         "kind": posicion_abierta["kind"], "motivo": motivo, "pnl": pnl_neto})
                posicion_abierta = None
            else:
                out_lines.append(f"    Mantiene posición {posicion_abierta['kind']} abierta "
                                  f"({dte_restante}d a vencimiento) — P&L flotante=${pnl_flotante:+.2f}")

        if posicion_abierta is None and regimen.regime != DEFENSIVO:
            dte_entrada = (TARGET_DTE_MIN + TARGET_DTE_MAX) // 2
            expiry = fecha + timedelta(days=dte_entrada)

            if regimen.regime in (TENDENCIAL_ALCISTA, TENDENCIAL_BAJISTA):
                if regimen.regime == TENDENCIAL_ALCISTA:
                    strike, tipo = round(precio * (1 + OTM_PCT_DIRECTIONAL), 2), "call"
                else:
                    strike, tipo = round(precio * (1 - OTM_PCT_DIRECTIONAL), 2), "put"
                legs = [{"type": tipo, "side": "buy", "strike": strike}]
                costo_por_contrato = _valor_piernas(legs, precio, dte_entrada, vol_anual, 1)
                costo_contrato_total = costo_por_contrato + OPTIONS_COMMISSION_PER_CONTRACT
                riesgo_max = equity * MAX_RISK_PER_TRADE_PCT
                qty = max(int(riesgo_max // costo_contrato_total), 0) if costo_contrato_total > 0 else 0

                if qty >= 1:
                    costo_neto_apertura = _valor_piernas(legs, precio, dte_entrada, vol_anual, qty)
                    equity -= OPTIONS_COMMISSION_PER_CONTRACT * len(legs) * qty
                    posicion_abierta = {
                        "kind": "direccional", "legs": legs, "expiry": expiry, "qty": qty,
                        "costo_neto_apertura": costo_neto_apertura, "regimen": regimen.regime,
                        "precio_entrada_subyacente": precio, "fecha_apertura": fecha,
                    }
                    out_lines.append(f"    ABRE {'Long Call' if tipo=='call' else 'Long Put'} — strike={strike}, "
                                      f"venc={expiry.date()} ({dte_entrada}d), qty={qty}, "
                                      f"costo=${costo_neto_apertura:+.2f} (prima+comisión) — régimen {regimen.regime}")
                else:
                    out_lines.append(f"    Régimen {regimen.regime} pero NO abre: costo por contrato "
                                      f"(${costo_contrato_total:.2f}) excede el 2% de riesgo del equity (qty=0).")

            else:  # RANGO_LATERAL -> Iron Condor
                legs, ancho_ala = _construir_iron_condor_sintetico(precio)
                credito_por_contrato = -_valor_piernas(legs, precio, dte_entrada, vol_anual, 1)

                if credito_por_contrato > 0:
                    riesgo_por_contrato = ancho_ala * 100 - credito_por_contrato + OPTIONS_COMMISSION_PER_CONTRACT * len(legs)
                    riesgo_max = equity * MAX_RISK_PER_TRADE_PCT
                    qty = max(int(riesgo_max // riesgo_por_contrato), 0) if riesgo_por_contrato > 0 else 0

                    if qty >= 1:
                        costo_neto_apertura = _valor_piernas(legs, precio, dte_entrada, vol_anual, qty)
                        equity -= OPTIONS_COMMISSION_PER_CONTRACT * len(legs) * qty
                        posicion_abierta = {
                            "kind": "iron_condor", "legs": legs, "expiry": expiry, "qty": qty,
                            "costo_neto_apertura": costo_neto_apertura, "regimen": regimen.regime,
                            "precio_entrada_subyacente": precio, "fecha_apertura": fecha,
                        }
                        strikes_txt = ", ".join(f"{l['side']} {l['type']} {l['strike']}" for l in legs)
                        out_lines.append(f"    ABRE Iron Condor — {strikes_txt}, venc={expiry.date()} ({dte_entrada}d), "
                                         f"qty={qty}, crédito recibido=${-costo_neto_apertura:+.2f} — "
                                         f"régimen {regimen.regime}")
                    else:
                        out_lines.append(f"    Régimen RANGO_LATERAL pero NO abre condor: riesgo por contrato "
                                          f"(${riesgo_por_contrato:.2f}) excede el 2% del equity (qty=0).")
                else:
                    out_lines.append(f"    Régimen RANGO_LATERAL pero NO abre condor: crédito neto estimado "
                                      f"<=0 con los strikes actuales (cadena sintética demasiado angosta).")
        elif posicion_abierta is None and regimen.regime == DEFENSIVO:
            out_lines.append("    Régimen DEFENSIVO, sin posición abierta -> no opera este día.")

    # --- Resumen de la semana ---
    precio_inicio = float(ventana["Close"].iloc[0])
    precio_fin = float(ventana["Close"].iloc[-1])
    rendimiento_buyhold_pct = (precio_fin / precio_inicio - 1) * 100

    pnl_flotante_final = 0.0
    if posicion_abierta is not None:
        fecha_fin = ventana.index[-1]
        precio_fin_bar = float(datos_ind.loc[fecha_fin, "Close"])
        vol_fin = float(datos_ind.loc[fecha_fin, "Vol_Anual"])
        dte_restante = (posicion_abierta["expiry"] - fecha_fin).days
        valor_final = _valor_piernas(posicion_abierta["legs"], precio_fin_bar, dte_restante, vol_fin, posicion_abierta["qty"])
        pnl_flotante_final = valor_final - posicion_abierta["costo_neto_apertura"]

    out_lines.append(f"\n--- Resumen semana {symbol} ---")
    out_lines.append(f"P&L realizado (trades cerrados dentro de la ventana): ${pnl_realizado_semana:+.2f}")
    if posicion_abierta is not None:
        out_lines.append(f"Posición {posicion_abierta['kind']} sigue abierta al cierre de la ventana "
                          f"(venc. {posicion_abierta['expiry']}) — P&L flotante: ${pnl_flotante_final:+.2f}")
    out_lines.append(f"P&L total semana (realizado + flotante de lo que sigue abierto): "
                      f"${pnl_realizado_semana + pnl_flotante_final:+.2f}")
    out_lines.append(f"Buy & hold {symbol} en el mismo período (${precio_inicio:.2f} -> ${precio_fin:.2f}): "
                      f"{rendimiento_buyhold_pct:+.2f}%")
    out_lines.append(f"Trades cerrados en la ventana: {len(trades_cerrados)}")

    return {
        "symbol": symbol, "pnl_realizado": pnl_realizado_semana, "pnl_flotante_final": pnl_flotante_final,
        "buyhold_pct": rendimiento_buyhold_pct, "n_trades_cerrados": len(trades_cerrados),
        "posicion_abierta_al_final": posicion_abierta is not None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=None, help="Si se omite, corre SPY/AAPL/QQQ.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else SYMBOLS_DEFAULT

    out_lines = [
        f"SIMULACIÓN DÍA POR DÍA — {args.start} a {args.end}",
        f"Config actual: TARGET_DTE={TARGET_DTE_MIN}-{TARGET_DTE_MAX}, EXIT_DTE_BUFFER={EXIT_DTE_BUFFER}, "
        f"IRON_CONDOR_SHORT_PCT={IRON_CONDOR_SHORT_PCT}, TAKE_PROFIT_PCT={TAKE_PROFIT_PCT}",
        "NOTA METODOLÓGICA: precios de opciones estimados con Black-Scholes usando volatilidad "
        "realizada del subyacente como proxy de la implícita (no hay histórico de precios de "
        "opciones reales de Alpaca para fechas pasadas) — misma limitación que el backtest de 3 "
        "años documentado en README.md. Tampoco se usa sentimiento de noticias (obtener_titulares_alpaca "
        "trae noticias ACTUALES, no del período histórico simulado) — a diferencia del agente en vivo, "
        "que sí lo consulta cada ciclo; el régimen aquí es puramente técnico (regime_engine), igual que "
        "en backtest.py. Se asume la cuenta arranca FLAT al primer día de la ventana (no arrastra "
        "posiciones de antes del --start).",
    ]

    resultados = []
    for symbol in symbols:
        r = simular_semana(symbol, args.start, args.end, out_lines)
        resultados.append(r)

    out_lines.append(f"\n\n{'='*70}\nRESUMEN COMPARATIVO ({args.start} a {args.end})\n{'='*70}")
    for r in resultados:
        if r.get("sin_datos"):
            out_lines.append(f"{r['symbol']}: sin datos de mercado en la ventana.")
            continue
        total = r["pnl_realizado"] + r["pnl_flotante_final"]
        estado = "posición sigue abierta" if r["posicion_abierta_al_final"] else "cerrado/flat al final"
        out_lines.append(f"{r['symbol']}: P&L total ${total:+.2f} ({estado}, "
                          f"{r['n_trades_cerrados']} trade(s) cerrado(s)) vs. buy&hold {r['buyhold_pct']:+.2f}%")

    reporte = "\n".join(out_lines)
    print(reporte)

    nombre_archivo = f"simulacion_semana_{args.start.replace('-', '')}_{args.end.replace('-', '')}.log"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(reporte)
    print(f"\n\n[Reporte guardado en {nombre_archivo}]")


if __name__ == "__main__":
    main()
