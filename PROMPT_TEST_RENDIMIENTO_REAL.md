Contexto: la decisión de cuenta para la entrega final queda para después.
Ahora lo que importa es medir el **rendimiento real** del agente — no el
backtest teórico, sino resultados de trades reales, de apertura a cierre,
ejecutados vía CLI/API/Alpaca real — antes de comprometernos a que corra
así toda la semana del concurso.

Problema: con DTE 7-14 (el config real de `live_agent.py`), un trade tarda
6-8 días en resolverse en promedio. No tenemos ese tiempo para iterar y
medir rendimiento real ahora. Necesitamos un ciclo de vida corto (real, no
simulado) para juntar varios trades completos (abrir → cerrar) en 1-2 días
de calendario real.

No requiere confirmación previa (test aislado, no toca la cuenta ni el
loop de la competencia) — corré todo y reportá con números.

## Diseño del test

**No tocar `live_agent.py` ni `config.py`.** El loop actual (3 posiciones
DTE 7-14 en `PA3EGUEP0QCV`) sigue corriendo tal cual, es señal real
también, no lo interrumpas.

Armá un script de test aparte (ej. `test_rendimiento_dte_corto.py`) que:

1. Reutilice los mismos módulos reales que usa `live_agent.py`
   (`regime_engine`, `sentiment_engine`, `options_selector`,
   `risk_manager`, `executor`/`cli_executor` según `--use-cli`) — la
   misma lógica de decisión y ejecución, no una reimplementación.
2. Use un `TARGET_DTE_MIN`/`TARGET_DTE_MAX` corto (ej. 1-3 días) SOLO
   dentro de este script, sin tocar los valores globales de `config.py`
   que usa el loop real.
3. Use un archivo de estado separado (ej. `positions_state_test.json`),
   para no pisar ni confundirse con `positions_state.json` del loop real.
4. Contra la cuenta paper real `PA3EGUEP0QCV` (vía CLI o SDK, real, no
   dry-run) — SPY, AAPL, QQQ, y si alcanza el tiempo, 2-3 símbolos más
   para tener más muestras (elegí símbolos líquidos con cadena de
   opciones activa).
5. Corra en loop (mismo intervalo de 15 min o el que decidas, dado que
   acá el objetivo es velocidad de iteración, no fidelidad al intervalo
   del concurso) durante las próximas 24-48h, dejando que cada posición
   llegue a su resolución real: take-profit, stop-loss, o cierre por
   `EXIT_DTE_BUFFER` corto (ajustalo proporcionalmente, ej. buffer=1 para
   DTE 1-3).

## Qué reportar (esto es lo que importa)

Por cada trade **cerrado de verdad** (no floating):
- Símbolo, régimen detectado al abrir, estructura (call/put/condor),
  motivo del cierre (TP/SL/buffer DTE), días reales que estuvo abierto,
  P&L realizado en USD y en %.

Y agregado:
- Win rate real (% de trades cerrados con P&L positivo).
- P&L total realizado del test.
- Comparación explícita contra lo que el backtest de 3 años predecía para
  trades con DTE corto (los números de `README.md`, sección "Recalibración
  para la ventana de 7 días") — ¿el comportamiento real se parece, o el
  backtest (con Black-Scholes como proxy) se aleja de lo que pasa con
  precios reales de mercado?

No reportes solo "funcionó" — números concretos de cada trade cerrado, y
si algo no se resuelve a tiempo, decilo explícito (mejor unos pocos trades
reales completos que muchos a medias).

## Seguridad

No canceles ni toques las 3 posiciones del loop real (SPY/AAPL/QQQ vto.
2026-09-02) desde este script — son procesos y estados completamente
separados, pero comparten la misma cuenta, así que doble chequeo antes de
cualquier cierre: que el símbolo/`option_symbol` que estás cerrando es del
test, no del loop real.
