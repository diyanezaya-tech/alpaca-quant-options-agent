Contexto: esto retoma `PROMPT_VALIDAR_DTE_CORTO.md`, que quedó a mitad de
camino — solo se hizo la Parte 4 (premio $6,000 en `MISSION_BRIEF.md`). Las
Partes 1, 2 y 3 (backtest 3 años con DTE 7-14, análisis de ventana de 7
días, sanity check de strikes del condor) nunca se corrieron ni quedaron
documentadas en ningún archivo del proyecto. El loop (`live_agent.py`,
PID activo, `--use-cli`) sigue corriendo en `PA3EGUEP0QCV` con 3 posiciones
direccionales (SPY call, AAPL put, QQQ call, vto. 2026-09-02) — no las
toques, esto es solo backtest/análisis offline.

Cambio importante desde el prompt original: `IRON_CONDOR_SHORT_PCT` ya no
está en 0.05 — lo bajé a **0.03** en `config.py` hace un momento (Cowork,
sesión en la nube) basándome en la recomendación de la Parte 3 original,
pero **sin el sanity check de datos reales que esa misma parte pedía**.
Es una corrección provisional, no una validada. Tratalo como tal: confirmá
con datos reales si 0.03 es lo correcto para DTE 7-14, o si conviene otro
valor.

No requiere confirmación previa (es backtest/análisis, no una orden real)
— corré todo y reportá. Si algo muestra que la recalibración DTE 7-14
empeora el resultado esperado, decilo explícito aunque contradiga la
decisión que ya se tomó.

## Parte 1 — Backtest de 3 años con los parámetros actuales

Confirmá primero que `config.py` en disco tiene `TARGET_DTE_MIN=7`,
`TARGET_DTE_MAX=14`, `EXIT_DTE_BUFFER=2`, `IRON_CONDOR_SHORT_PCT=0.03`. Si
no, avisá y no sigas.

Corré `backtest.py` para SPY, AAPL y QQQ con esos valores. Reportá
rendimiento de la estrategia vs. buy & hold para los 3 símbolos, y
comparalo contra los números viejos documentados hoy en `README.md` (DTE
21-45 / buffer 10: SPY 42.00%, AAPL 37.72%, QQQ 19.57%): ¿mejora, empeora,
o se mantiene similar el edge total sobre 3 años?

## Parte 2 — Análisis de ventana de 7 días con la calibración nueva

Lo más importante de este prompt:

1. ¿Cuántos días en promedio/mediana tarda ahora una posición en
   resolverse (TP, SL, o cierre por `EXIT_DTE_BUFFER`)?
2. ¿Qué porcentaje de las operaciones se resuelve dentro de 7 días
   corridos desde la apertura? Compará contra el 21-34% de la calibración
   vieja (DTE 21-45).
3. Sobre ventanas rodantes de 7 días con la calibración nueva: ¿sigue
   dominando el ruido sobre la señal en la misma magnitud, o mejoró la
   relación señal/ruido al acortar el DTE?

## Parte 3 — Validar (no solo recomendar) los strikes del Iron Condor

Con datos reales de la cadena de opciones de Alpaca (SPY/AAPL/QQQ, DTE
7-14 disponible ahora mismo): consultá qué crédito neto se recibiría hoy
con `IRON_CONDOR_SHORT_PCT=0.03` (el valor ya aplicado) vs. el 0.05
original, y evaluá el ratio riesgo/recompensa contra `IRON_CONDOR_WING_PCT`
y el gate de salida (`evaluar_salida_iron_condor`). Si 0.03 no es el
número correcto, corregilo vos mismo en `config.py` y decime a qué valor y
por qué — esto sí es un cambio de código, no una orden real, así que no
hace falta que me esperes.

## Parte 4 — Documentación

Reemplazá en `README.md` la tabla de backtest que todavía muestra
`EXIT_DTE_BUFFER=10` (sección "Backtest con datos reales") por los
resultados nuevos de la Parte 1, dejando ambas tablas (vieja y nueva) para
que se entienda el porqué del cambio. Sumá un párrafo corto con los
números de la Parte 2 (días de resolución, % dentro de 7 días) — ahí es
donde más se nota si la recalibración cumplió su objetivo.

## Reporte

Números concretos de las 4 partes, no "mejoró"/"empeoró" sin cifras.
Cuando termines, dejá el resumen corto de siempre para que se lo pase a
Claude (Cowork).
