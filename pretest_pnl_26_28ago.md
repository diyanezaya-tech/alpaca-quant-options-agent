# P&L de los días de prueba (26–28 ago) — no cuenta para el concurso

Registro tomado el 2026-08-26 (~19:5x UTC) contra la cuenta paper
`PA3EGUEP0QCV`, antes del corte limpio para la ventana oficial juzgada
(28 ago 09:30 ET – 4 sept 15:00 UTC). Esto documenta el estado acumulado
por las pruebas pre-contest, no el resultado del concurso.

## Equity de cuenta

- `equity`: $96,737.76
- `last_equity` (día anterior): $99,998.68
- `cash`: $82,892.76
- `position_market_value`: $13,845
- `portfolio_value`: $96,737.76

## Posiciones abiertas (todas abiertas 26-ago ~15:22 ET, venc. 2026-09-02)

| Symbol | Qty | Side | Precio entrada | Precio actual | P&L flotante | P&L % |
|---|---|---|---|---|---|---|
| `SPY260902C00782000` | 202 | long | $0.41 | $0.30 | **-$2,222** | -26.83% |
| `AAPL260902P00307500` | 27 | long | $1.63 | $1.60 | **-$81** | -1.84% |
| `QQQ260902C00726000` | 21 | long | $1.91 | $1.65 | **-$546** | -13.61% |

P&L flotante total de las 3 posiciones: **-$2,849**

## Contexto

Posiciones abiertas por `live_agent.py` durante la ventana de observación
pre-contest (después de un reset de estado a las 15:22 ET del 26-ago). No
reflejan la señal/régimen que estará vigente al arrancar la ventana oficial
el 28-ago — se documentan acá solo para trazabilidad histórica de la cuenta,
no como parte del resultado juzgado.
