Contexto: hoy recalibramos `config.py` de DTE 21-45 a **DTE 7-14** (con
`EXIT_DTE_BUFFER` de 10 a 2) para que las posiciones nuevas se resuelvan
dentro de la ventana de 7 días que se juzga en el concurso (28 ago-4 sept,
deadline de envío 4 sept 15:00 UTC, confirmado en la página oficial de
lablab.ai). El loop en vivo ya corre con estos valores nuevos.

Problema: el backtest de 3 años que tenemos documentado (SPY 42.00%, AAPL
37.72%, QQQ 19.57% vs buy&hold) se corrió con **DTE 21-45**, TAKE_PROFIT_PCT
y EXIT_DTE_BUFFER ajustados para ese horizonte. Nunca se validó que la
combinación nueva (DTE 7-14 + buffer 2) siga siendo rentable — cambiamos el
parámetro más importante de la estrategia sin volver a correr los números.
Necesito esa validación antes de confiar en que el agente puede ser
rentable en la ventana real del concurso.

No es solo backtest, así que no requiere confirmación previa (esto es
análisis/backtest, no una orden real) — corre todo y repórtame.

## Parte 1 — Re-correr el backtest de 3 años con los parámetros nuevos

Corre `backtest.py` para SPY, AAPL y QQQ con `TARGET_DTE_MIN=7`,
`TARGET_DTE_MAX=14`, `EXIT_DTE_BUFFER=2` (los valores actuales de
`config.py` — ya deberían estar aplicados, pero confírmalo antes de correr).
Reporta el rendimiento de la estrategia vs. buy & hold para los 3 símbolos,
y compáralo contra los números viejos (DTE 21-45): ¿mejora, empeora, o se
mantiene similar el edge total sobre 3 años?

## Parte 2 — Repetir el análisis de ventana de 7 días, pero con la calibración nueva

Esto es lo más importante. Repite el mismo análisis que se hizo el 26-ago
sobre la calibración vieja (duración de resolución de trades, % que se
resuelve dentro de 7 días, distribución de resultados en ventanas rodantes
de 7 días) pero ahora sobre el backtest con **DTE 7-14**:

1. ¿Cuántos días en promedio/mediana tarda ahora una posición en resolverse?
2. ¿Qué porcentaje de las operaciones se resuelve dentro de 7 días corridos
   desde la apertura? Compáralo contra el 21-34% que dio la calibración
   vieja.
3. Sobre ventanas rodantes de 7 días con la calibración nueva: ¿sigue
   dominando el ruido sobre la señal en la misma magnitud, o mejoró la
   relación señal/ruido al acortar el DTE?

## Parte 3 — Sanity check de los strikes del Iron Condor para DTE corto

`IRON_CONDOR_SHORT_PCT=0.05` (strikes ~5% OTM) y `IRON_CONDOR_WING_PCT=0.03`
se calibraron originalmente pensando en DTE 21-45. El movimiento esperado
del subyacente en 7-14 días es naturalmente menor que en 21-45 días, así
que strikes a 5% OTM pueden estar demasiado lejos del precio para esa
ventana más corta -> crédito recibido muy chico en relación al riesgo
(ancho de ala), lo que empeora el ratio riesgo/recompensa del gate de
salida (`evaluar_salida_iron_condor`, que mide contra el crédito recibido).
Con datos reales de la cadena de opciones de Alpaca (SPY/AAPL/QQQ, DTE
7-14 disponible ahora mismo), consulta qué crédito neto se recibiría hoy
con los strikes actuales y evalúa si conviene acercar `IRON_CONDOR_SHORT_PCT`
(ej. a 2-3%) para esta ventana corta. No cambies el parámetro todavía —
solo reporta el número y tu recomendación.

## Parte 4 — Corrección de documentación

`MISSION_BRIEF.md` dice premio de $5,000; la página oficial del hackathon
(lablab.ai) dice **$6,000 Prize Pool**. Corrígelo ahí y en cualquier otro
doc del proyecto que repita la cifra vieja.

## Reporte

Números concretos de las 4 partes — no "mejoró"/"empeoró" sin cifras. Si la
Parte 1 o 2 muestran que la calibración nueva empeora el resultado
esperado, decilo explícitamente aunque contradiga la decisión que ya
tomamos hoy — para eso es la validación.
