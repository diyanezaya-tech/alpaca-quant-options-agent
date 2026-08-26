Contexto: las 3 semanas simuladas (03-07 ago, 13-17 jul, 17-21 ago) dieron
8 de 9 combinaciones símbolo/semana sin ganar, con un patrón que se repite
en las 3: el agente compra Long Call/Put justo antes de que el precio
revierta en contra. La única ganadora fue el Iron Condor de QQQ. Diego
decidió investigar si esto se debe a que `UMBRAL_TENDENCIA=0.007` (0.7%)
es demasiado sensible — confirma tendencia con una separación de medias
móviles chica, así que puede estar entrando en reversiones que todavía
parecen tendencia y no lo son. Vamos a probarlo, no a asumirlo.

No requiere confirmación previa (análisis + backtest, no toca la cuenta
real) — corré todo y reportá con números. Sí pedime confirmación antes de
tocar el `config.py` que usa el loop en vivo (ver Parte 3).

## Parte 1 — Probar 2-3 valores más altos de UMBRAL_TENDENCIA

Elegí 2-3 candidatos por encima de 0.007 (ej. 0.010, 0.012, 0.015 — o los
que tengan sentido según la distribución real de separación de medias que
veas en los datos, no números arbitrarios). Para cada uno, re-corré
`simulacion_semana.py` sobre las MISMAS 3 semanas ya vistas (03-07 ago,
13-17 jul, 17-21 ago), SPY/AAPL/QQQ — no elijas semanas nuevas para esto,
así comparamos manzana con manzana contra el resultado ya conocido de
0.007.

## Parte 2 — Análisis del patrón, no solo el número final

Para cada candidato, además de P&L agregado vs. buy&hold:
- ¿Cuántas de las entradas direccionales que antes (con 0.007) terminaron
  en pérdida por reversión inmediata ahora NO se toman (el umbral más alto
  las filtra)?
- ¿Cuántas entradas que SÍ eran buenas (hubieran ganado) también se
  pierden por el umbral más estricto? Si el umbral filtra casi todo
  (direccional y bueno por igual) y el resultado "mejora" solo porque el
  agente casi no opera, decilo explícito — eso no es arreglar el whipsaw,
  es esconderlo dejando de operar.
- ¿El régimen pasa más tiempo en "sin tendencia clara" (ninguna estructura
  definida) con el umbral más alto? Si es así, ¿qué hace el agente en ese
  caso — nada, o cae a otra rama de `regime_engine`?

## Parte 3 — Decisión y aplicación (con confirmación)

Con los números de las Partes 1 y 2, elegí el valor que mejor balance dé
entre reducir el whipsaw real y seguir capturando tendencias genuinas (no
el valor que dé el P&L más alto sin más — si ves que "mejora" solo por
operar menos, decilo y no lo recomiendes como si fuera la solución).

Antes de tocar `config.py`: verificá si `UMBRAL_TENDENCIA` afecta de
alguna forma la evaluación de las 3 posiciones YA abiertas en el loop en
vivo (SPY/AAPL/QQQ, vto. 2026-09-02) — específicamente si `risk_manager.py`
usa el régimen recalculado cada ciclo para decidir mantener/cerrar, o si
esas decisiones son solo por precio (stop/take-profit) y DTE, independientes
del régimen. Reportame esto ANTES de aplicar el cambio — si el régimen
recalculado SÍ puede gatillar un cierre distinto en las posiciones ya
abiertas, no apliques el cambio todavía, avisame primero. Si confirmás que
es seguro (las 3 posiciones abiertas no se ven afectadas porque
`MAX_CONCURRENT_POSITIONS` ya está en el tope y el cierre es solo por
precio/DTE), aplicá el valor elegido a `config.py`.

## Reporte

Tabla comparativa de los candidatos (P&L agregado vs. buy&hold, conteo de
entradas filtradas buenas vs. malas) para las 3 semanas, tu lectura de si
esto es un arreglo real o solo "operar menos", la verificación de
seguridad sobre las posiciones abiertas, y qué valor final quedó aplicado
(o por qué decidiste no aplicar ninguno).
