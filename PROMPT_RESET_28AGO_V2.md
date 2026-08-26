Contexto (actualizado 26-ago, retoma `PROMPT_RESET_28AGO.md` con datos
concretos): la ventana oficial juzgada por el hackathon es **28 ago 09:30
ET (apertura de mercado) – 4 sept 15:00 UTC (deadline de envío)**. Ahora
mismo (26-ago) hay 3 posiciones reales abiertas en `PA3EGUEP0QCV`, todas
abiertas hoy a las 15:22 ET, vencimiento 2026-09-02:

- SPY: Long Call 782 (direccional, régimen TENDENCIAL_ALCISTA)
- AAPL: Long Put 307.5 (direccional, TENDENCIAL_BAJISTA)
- QQQ: Long Call 725 (direccional, TENDENCIAL_ALCISTA)

Con `EXIT_DTE_BUFFER=2`, el cierre forzado por vencimiento sería recién
~31-ago — es decir, si no se hace nada, estas 3 posiciones van a seguir
abiertas cuando arranque la ventana oficial el 28-ago, con ~2 días y medio
de P&L acumulado de ANTES del inicio del concurso ya mezclado en el equity
de la cuenta. Ejecutá esto la mañana del 28-ago, antes de las 09:30 ET.

## Paso 0 — Verificar identidad de cuenta (siempre primero)

`GET /v2/account`, confirmá `account_number == PA3EGUEP0QCV`. Si no
coincide, parate y avisá — no sigas.

## Paso 1 — Registrar el P&L de los días de prueba (26-28 ago) por separado

Antes de tocar nada: traé el P&L flotante actual de las 3 posiciones
(`obtener_posiciones()` o `GET /v2/positions`) y el equity actual de la
cuenta. Guardalo en un archivo aparte (ej. `pretest_pnl_26_28ago.md`) —
esto NO es parte del resultado del concurso, es solo para tener registro
de los días de observación previos.

## Paso 2 — Decidir el enfoque de corte limpio

Dos caminos, en este orden de preferencia:

**A) Solo documentar el corte (preferido, más simple y sin fricción):**
si no hace falta un reset real porque lo que se va a juzgar son los
trades/actividad con timestamp dentro de la ventana 28ago-4sept (y no un
snapshot de equity total), alcanza con: cerrar las 3 posiciones actuales
(ver Paso 3) y documentar en `README.md`/`writeup.md` la fecha, hora exacta
(ET y UTC) y equity de cuenta en el momento exacto en que arranca el
track record oficial, para que quede clara la ventana que corresponde
juzgar aunque la cuenta tenga historial previo.

**B) Reset real de la cuenta paper:** solo si confirmás que Alpaca permite
resetear el historial/equity de una cuenta paper existente sin crear una
nueva (revisá el dashboard web, `Reset Account` si existe la opción). Si
la única forma es crear una cuenta paper nueva (nuevas API keys, hay que
actualizar `.env` y volver a apuntar `live_agent.py`), **no lo hagas solo
— avisame primero**, es un cambio estructural más grande que closing +
documentar.

## Paso 3 — Cerrar las 3 posiciones actuales

Cerrá las 3 posiciones reales (vía CLI o SDK, el mismo camino que usa
`live_agent.py`). Confirmá con `GET /v2/positions` que la lista queda
vacía (`[]`) después.

## Paso 4 — Limpiar estado y reiniciar el loop

Mismo procedimiento ya validado en `PROMPT_LIMPIAR_ESTADO_Y_REINICIAR.md`:
`positions_state.json` a `{}`, confirmar que no queda ningún proceso
`live_agent.py` corriendo, reiniciar en modo real sin `--dry-run` CON
`--use-cli`, y confirmar en el log el arranque limpio con posiciones
abiertas `[]` y al menos un ciclo completo sin errores para SPY/AAPL/QQQ.

## Paso 5 — Documentación final

Agregá a `README.md` y `writeup.md` una línea clara: "Track record oficial
del concurso arranca 28-ago-2026 [hora exacta ET/UTC], equity de
referencia $[monto]" — así un juez que mire el historial completo de la
cuenta entiende qué corresponde a la semana juzgada.

## Reporte

Cuál de los dos caminos (A o B) usaste y por qué, P&L de los días de
prueba (guardado aparte), confirmación de las 3 posiciones cerradas,
`positions_state.json` en `{}`, PID del loop nuevo, y la línea del log que
confirma arranque limpio.
