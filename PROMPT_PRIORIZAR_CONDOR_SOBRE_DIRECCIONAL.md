Contexto: dos hipótesis de whipsaw ya se probaron y se refutaron con datos
reales (`UMBRAL_TENDENCIA` no importó, medias más cortas tampoco — ni con
5 días de media rápida cambió una sola de las 5 entradas perdedoras). De
las 12 combinaciones símbolo/semana/estructura probadas en las 3 semanas
(03-07 ago, 13-17 jul, 17-21 ago), la ÚNICA ganadora fue un Iron Condor
(QQQ, 13-17 jul). Esto tiene lógica real, no es casualidad de muestra:
vender premium gana con el simple paso del tiempo si el subyacente no se
mueve mucho; una posición direccional necesita acertar dirección Y timing
en una ventana de 7 días, mucho más exigente.

Diego quiere mejorar las chances reales de terminar la semana del concurso
en positivo. **No podemos prometer eso — 7 días es una muestra chica y
ruidosa para cualquier estrategia — pero sí podemos, con evidencia, sesgar
el diseño hacia la estructura que consistentemente funcionó mejor.** Esto
es una decisión de producto legítima (options theory real: theta decay
favorece al vendedor de premium en ventanas cortas), NO un ajuste para que
el backtest de estas 3 semanas dé mejor — hay que separar bien las dos
cosas en el reporte.

No requiere confirmación previa para el análisis/backtest. Antes de tocar
`config.py`/`regime_engine.py`/`options_selector.py` para el loop real,
mismo protocolo de siempre: verificá que no afecte las 3 posiciones ya
abiertas antes de aplicar.

## Parte 1 — Diagnóstico: ¿por qué el agente casi no abre condores?

Contá, en las 3 semanas ya simuladas, cuántos días-símbolo estuvieron en
RANGO_LATERAL (candidato a condor) vs. TENDENCIAL (candidato a
direccional). Si RANGO_LATERAL es raro comparado con TENDENCIAL, el
problema no es solo la preferencia de estructura — es que el régimen casi
nunca lo clasifica como lateral. Si es así, decilo, porque cambia la
solución (no alcanza con preferir condor si el régimen casi nunca lo
detecta).

## Parte 2 — Diseñar el sesgo hacia condor, con criterio explícito

Con lo que encuentres en la Parte 1, proponé un cambio concreto a
`regime_engine.py`/`options_selector.py` que aumente cuándo el agente
elige Iron Condor en vez de direccional, por ejemplo (elegí lo que tenga
sentido, no apliques las tres a ciegas):
- Ensanchar el rango de "no hay tendencia clara" (hoy la separación de
  medias > `UMBRAL_TENDENCIA` ya define TENDENCIAL; si la separación es
  positiva pero débil, hoy igual entra direccional — evaluá si conviene
  que esa zona "débil" caiga a RANGO_LATERAL en vez de TENDENCIAL).
- Revisar si hay alguna condición boolean que hoy prioriza direccional
  sobre condor cuando ambos aplicarían, y invertirla.
Documentá la lógica exacta del cambio, no solo el resultado.

## Parte 3 — Revalidar en las mismas 3 semanas, con el mismo rigor

Re-corré `simulacion_semana.py` con el cambio para las 3 semanas ya
conocidas. Reportá:
- Cuántas operaciones que antes eran direccionales ahora son condor (y
  cuántas de esas condor habrían ganado o perdido).
- P&L total comparado contra el baseline actual (-$4,920.35 en las 3
  semanas/9 combos).
- Si el cambio simplemente reduce actividad direccional sin aumentar
  condores reales (porque el régimen sigue sin detectar lateral), decilo
  — no es la solución, hay que volver a la Parte 1.

## Parte 4 — Chequeo de honestidad (importante)

Explicá en el reporte, en dos frases separadas y claras:
1. Por qué este cambio tiene sentido más allá de estas 3 semanas
   (argumento de options theory / estructura de riesgo, no "dio mejor
   número").
2. Qué NO garantiza este cambio (no asegura una semana positiva, solo
   sesga hacia la estructura que estadísticamente se comporta mejor en
   ventanas cortas según lo que vimos).

## Reporte

Números concretos de las 4 partes. Si con este cambio el P&L de las 3
semanas sigue siendo negativo en conjunto, decilo tal cual — la pregunta a
responder es si mejora relativo al baseline y por qué, no si queda en
positivo a toda costa.
