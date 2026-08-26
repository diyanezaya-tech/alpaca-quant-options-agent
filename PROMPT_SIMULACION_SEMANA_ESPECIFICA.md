Contexto: Diego quiere ver, en minutos y no en días, qué decisiones habría
tomado el agente durante una semana histórica puntual — no el agregado de
3 años, el detalle día por día. Esto es independiente del test en curso
(`test_rendimiento_dte_corto.py`, real, corriendo en background) — no lo
toques, dejalo corriendo.

No requiere confirmación previa (es simulación offline con datos
históricos reales, no toca la cuenta ni coloca órdenes) — corré todo y
reportá.

## Objetivo

Reutilizar el motor real de `backtest.py` (regime_engine, options_selector
con Black-Scholes como proxy, risk_manager) pero acotado a una ventana
puntual — por defecto **2026-08-01 a 2026-08-07** — y en vez de reportar
solo el retorno acumulado, mostrar el log de decisión día por día, como si
el agente hubiera estado corriendo en vivo esa semana.

## Qué armar

Un script nuevo (ej. `simulacion_semana.py`, o una función/flag agregada a
`backtest.py` si es más simple sin duplicar lógica) que:

1. Acepte `--symbol`, `--start` y `--end` (default `2026-08-01` /
   `2026-08-07`).
2. Descargue el histórico real necesario (igual que `backtest.py`), con
   suficiente warm-up ANTES de `--start` para que las medias móviles
   (10/30) y la volatilidad (15/200) ya estén calculadas al llegar al
   primer día de la ventana — no arrancar el cálculo de indicadores el
   mismo `--start`, se necesita historial previo real para que el primer
   día del reporte ya tenga régimen válido.
3. Para cada día de trading dentro de `--start`..`--end` (recorriendo
   fecha por fecha, no todo de una), loguear en el mismo formato/nivel de
   detalle que `live_agent.log`:
   - Fecha, régimen detectado (con los valores de medias/volatilidad que
     lo explican, igual que loguea `live_agent.py`).
   - Si abrió posición: estructura elegida, strike(s), crédito o costo,
     tamaño (contratos), motivo del régimen.
   - Si mantuvo una posición abierta: P&L flotante ese día.
   - Si cerró: motivo (TP/SL/buffer DTE/vencimiento natural en la
     simulación) y P&L realizado.
4. Al final: P&L acumulado de la semana simulada, comparado contra
   buy&hold del mismo período para el mismo símbolo.
5. Corré esto para **SPY, AAPL y QQQ** (los 3 del concurso) con los
   parámetros ACTUALES de `config.py` (DTE 7-14, buffer 2,
   `IRON_CONDOR_SHORT_PCT=0.03`) — el objetivo es ver cómo se habría
   comportado el agente que va a correr la semana del concurso, no una
   configuración vieja.

## Nota sobre precios de opciones simulados

Igual que en `backtest.py`, el precio de las opciones en la ventana
histórica se estima con Black-Scholes (no hay datos de opciones
históricas reales de Alpaca para revender fechas pasadas) — dejalo
explícito en el reporte, es la misma limitación metodológica que ya
documenta `README.md` para el backtest de 3 años.

## Reporte

El log día por día completo de los 3 símbolos (pegalo o dejalo en un
archivo, ej. `simulacion_semana_01_07ago.log`), más el resumen de P&L de
la semana simulada vs. buy&hold por símbolo. Si algún día no hay datos de
mercado (feriado, fin de semana), decilo explícito en vez de saltearlo en
silencio.
