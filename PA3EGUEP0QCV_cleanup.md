# Limpieza de `PA3EGUEP0QCV` (cuenta vieja, sandbox, no juzgada) — 28-ago-2026

Cuenta de desarrollo/pruebas pre-contest. No cuenta para el juicio del
hackathon, pero fue dinero (paper) real moviéndose, así que queda
registrado.

## Cierre de los duplicados de MSFT/NVDA (27-ago)

Duplicación real por solape de dos instancias del loop (27-ago 15:39 ET y
15:46 ET, 7 minutos de diferencia) — ver `writeup.md` para el detalle de
causa raíz y el guard agregado en `live_agent.py` que lo previene.

Cerrado el 28-ago 19:25:03 UTC vía `alpaca position close` (posición
completa, misma opción para el tramo original y el duplicado, no se puede
separar vendiendo contratos sueltos):

| Symbol | Qty | Avg entry | Precio cierre | P&L realizado |
|---|---|---|---|---|
| MSFT260904C00515000 | 13 | $4.0115 | $6.05 | **+$2,650.00** |
| NVDA260904C00232500 | 8 | $3.275 | $0.51 | **-$2,212.00** |

## Otras posiciones sin explicar, cerradas en la misma tanda

Reportadas por Claude el 28-ago (hallazgo no pedido, encontrado al
verificar el estado de la cuenta antes de cerrar los duplicados) — Diego
decidió cerrarlas también en el mismo momento, ya que la cuenta no se usa
para nada real. Origen no investigado (probablemente acumulación de
múltiples corridas de `test_rendimiento_dte_corto.py` u otros scripts de
prueba contra esta misma cuenta a lo largo de varios días):

| Symbol | Qty | Avg entry | Precio cierre | P&L realizado |
|---|---|---|---|---|
| AAPL260902P00307500 | 27 | $1.63 | $0.32 | **-$3,537.00** |
| QQQ260902C00726000 | 21 | $1.91 | $0.81 | **-$2,310.00** |
| SPY260902C00782000 | 202 | $0.41 | $0.07 | **-$6,868.00** |

## Total realizado en esta limpieza

**-$12,277.00** (paper, sin impacto real ni en el juicio del hackathon).

## Verificación

`GET /v2/positions` contra `PA3EGUEP0QCV` (28-ago, post-cierre): MSFT y
NVDA no aparecen. Quedan 3 legs residuales sin valor (vencimiento
260828 = hoy, `market_value: 0`, del batch de pruebas de DTE corto del
27-ago) — `AAPL260828C00330000` (qty 2), `QQQ260828C00755000` (qty 1),
`SPY260828C00809000` (qty 1). Sin acción necesaria, expiran solas.
