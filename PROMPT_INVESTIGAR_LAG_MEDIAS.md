Contexto: se refutó con datos reales que `UMBRAL_TENDENCIA` cause el
whipsaw (subir de 0.007 a 0.015 no cambió el P&L ni un centavo en las 3
semanas ya vistas — las pérdidas grandes tienen separación de medias de
2.0%-3.4%, muy por encima de cualquier umbral probado). La hipótesis que
sigue es distinta: el lag estructural del cruce de medias 10/30 en sí —
para cuando confirma, el movimiento ya está mayormente hecho y revierte
después. Diego decidió seguir investigando esto, sabiendo que es un
cambio más profundo (toca `regime_engine.py`, no solo un umbral) y que
quedan ~1.5 días antes del concurso — mismo rigor que la vez pasada, no
más margen para cambios sin evidencia clara.

No requiere confirmación previa para el análisis/backtest. Si tocás
`config.py` (`MEDIA_RAPIDA_VENTANA`/`MEDIA_LENTA_VENTANA`), mismo
protocolo que la vez pasada: verificá primero que no afecte la evaluación
de las 3 posiciones ya abiertas en el loop en vivo antes de aplicar nada.

## Parte 1 — Cuantificar el lag antes de probar nada

Antes de cambiar parámetros: para las entradas direccionales que
resultaron en pérdida en las 3 semanas ya vistas, medí cuánto se había
movido ya el precio (en % desde el mínimo/máximo reciente relevante, o
desde N días antes) en el momento exacto en que el cruce 10/30 confirmó
régimen y el agente entró. Esto da un número concreto de "cuánto tarde
llega la señal", no solo la sospecha.

## Parte 2 — Probar medias más cortas

Con esa referencia, probá 2-3 pares de medias más cortas que 10/30 (ej.
5/20, 8/21, o los que tengan sentido según el lag medido en la Parte 1 —
no arbitrarios). Re-corré `simulacion_semana.py` sobre las MISMAS 3
semanas (03-07 ago, 13-17 jul, 17-21 ago), SPY/AAPL/QQQ, para cada par.

## Parte 3 — Mismo estándar de rigor que la vez pasada

Para cada candidato, no alcanza con el P&L agregado:
- ¿El lag medido en la Parte 1 realmente baja (entra más cerca del inicio
  real del movimiento) con medias más cortas, o el problema persiste
  igual?
- ¿Aparecen MÁS falsas señales (entradas por ruido de corto plazo que
  antes el filtro de 10/30 evitaba) que compensen cualquier mejora de
  timing? Las medias cortas reaccionan más rápido pero también a ruido —
  cuantificá cuántas entradas nuevas aparecen que antes no estaban, y
  cuántas de esas también terminan en pérdida.
- Si mejora el P&L pero es porque cambia qué días caen en qué régimen de
  forma que coincide con esta muestra puntual (3 semanas), decilo
  explícito — mismo riesgo de sobreajuste que ya venimos evitando en todo
  el proyecto.

## Parte 4 — Decisión y aplicación (con el mismo chequeo de seguridad)

Si algún candidato muestra mejora real y explicable (no solo P&L más
alto, sino menos lag Y sin explosión de falsas señales): antes de tocar
`config.py`, confirmá otra vez si `MEDIA_RAPIDA_VENTANA`/`MEDIA_LENTA_VENTANA`
puede afectar la evaluación de las 3 posiciones ya abiertas en el loop
real (aplica el mismo razonamiento que ya usaste para `UMBRAL_TENDENCIA`,
pero verificalo de nuevo para este cambio específico, no asumas que es
igual). Si es seguro, aplicá. Si ningún candidato mejora de verdad, no
apliques nada — decilo tal cual, como la vez pasada.

## Reporte

El lag cuantificado de la Parte 1, la tabla comparativa de candidatos de
la Parte 2-3 (P&L, lag medido, conteo de falsas señales nuevas), la
verificación de seguridad, y qué quedó aplicado (o por qué no se aplicó
nada). Si a esta altura el análisis no da una mejora clara y honesta, decí
eso explícitamente — no es necesario forzar una conclusión positiva.
