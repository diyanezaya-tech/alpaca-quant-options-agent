# Brief de misión — Agente Cuántico de Opciones (Alpaca Hackathon)

Contexto: agente de trading de opciones para el "Alpaca AI Trading Agents
Hackathon" (28 ago – 4 sept 2026, $6,000 en premios, juzgado por P&L y
creatividad/engagement). **Cuenta paper oficial del hackathon:
`PA3SQTOC6A22`, creada 28-ago-2026, balance inicial $100,000.**
`PA3EGUEP0QCV` fue solo la cuenta de desarrollo/pruebas pre-contest, no
la que se juzga.
Requisito obligatorio: todas las estrategias deben incluir opciones.

Estado actual (confirmado en backtest con datos reales de Alpaca, 3 años):
con `TAKE_PROFIT_PCT = 0.05` y `EXIT_DTE_BUFFER = 10` en `config.py`:

| Symbol | Estrategia | Buy & Hold |
|---|---|---|
| SPY | 42.00% | 38.45% |
| AAPL | 37.72% | 40.08% |
| QQQ | 19.57% | 43.84% |

Trabaja de forma autónoma (modo auto) sobre los siguientes bloques, en
orden. No pidas confirmación para cambios de código o backtests — solo
detente y pregunta si vas a **ejecutar una orden real** contra la cuenta
paper (`live_agent.py` o cualquier script que llame a `executor.py`), o si
encuentras una decisión de producto/estrategia que no puedas resolver con
los datos disponibles.

## Bloque 1 — Robustecer el backtest de RANGO_LATERAL
Actualmente `backtest.py` simplifica el régimen RANGO_LATERAL a una venta
de call cubierta sintética (no simula el Iron Condor de 4 legs completo
que sí ejecuta `options_selector.py` en vivo). Extiende el motor de
backtest para simular el Iron Condor real (4 legs, crédito neto, riesgo
definido por el ancho de las alas) y vuelve a correr los 3 símbolos.
Reporta si cambia la conclusión.

## Bloque 2 — Validación out-of-sample
El grid search de TAKE_PROFIT_PCT/EXIT_DTE_BUFFER se hizo sobre el mismo
período que se reporta el resultado (riesgo de overfitting). Separa los 3
años en 2 años de "entrenamiento" (ajuste de parámetros) y 1 año de
"prueba" (validación out-of-sample) para SPY, AAPL y QQQ. Reporta si los
parámetros ganadores siguen funcionando en el período de prueba.

## Bloque 3 — Robustez del `live_agent.py`
Revisa `live_agent.py` con ojo crítico de producción:
- Manejo de errores de red/API sin tumbar el loop completo.
- Aplicar el mismo take-profit / EXIT_DTE_BUFFER validados en el backtest
  (hoy el loop en vivo no cierra posiciones por esas reglas, solo abre).
- Logging a archivo (no solo consola) para poder revisar qué hizo el
  agente durante la semana del concurso aunque cierres la terminal.
- Considera correrlo con un scheduler de Windows o como servicio para que
  sobreviva reinicios; deja documentado cómo en el README, no hace falta
  configurarlo tú mismo.

## Bloque 4 — Dry run controlado
Antes de dejarlo corriendo la semana completa: ejecuta `live_agent.py`
por un ciclo o dos (puedes bajar temporalmente el intervalo para probar
rápido) contra la cuenta paper del hackathon y confirma que:
- Se conecta bien y trae datos.
- Construye una estrategia de opciones coherente con el régimen detectado.
- Los risk gates rechazan/aprueban como se espera.
- Detente ahí — no lo dejes operando en loop indefinido todavía sin avisar.

## Bloque 5 — Documentación
Actualiza `README.md` con los resultados finales de backtest (tabla) y
cualquier decisión de diseño relevante que hayas tomado en los bloques
anteriores, para que quede como referencia del proyecto.

---

Cuando termines cada bloque, deja un resumen corto (como los que ya
vienes haciendo) para que Diego se lo pueda pasar a Claude (Cowork), que
está coordinando el resto del proyecto (write-up de una página, registro
en el hackathon, decisiones de producto).
