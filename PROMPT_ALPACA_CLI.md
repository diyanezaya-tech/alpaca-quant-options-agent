Vamos a incorporar el CLI oficial de Alpaca (`alpacahq/cli`) al proyecto, que
está explícitamente diseñado para agentes de IA (flags `--dry-run`,
`--schema`, `--quiet`, salida JSON estructurada, sin estado). El hackathon
pide textualmente: "Build AI trading agents on Alpaca — autonomous agents
and trading apps using Alpaca's Trading API, MCP server and CLI." Hoy el
proyecto solo usa el SDK `alpaca-py`; queremos sumar el CLI real para la
capa de EJECUCIÓN, reforzando el enfoque de agente autónomo (una IA que
decide y luego actúa por línea de comandos, no solo un script que llama a
un SDK).

## Qué necesito

1. **Instala el CLI oficial** (`go install github.com/alpacahq/cli/cmd/alpaca@latest`
   o el método que corresponda en Windows). Verifica con `alpaca version` y
   `alpaca doctor`, apuntado a la cuenta paper del concurso (usa las
   credenciales de `.env`, revisa cómo el CLI espera la config — variables
   de entorno o archivo de config propio).

2. **Nueva capa de ejecución vía CLI** (`cli_executor.py` o similar):
   sustituye/complementa `executor.py` para que el envío de órdenes reales
   (equities y cada leg de las estructuras de opciones) se haga invocando el
   binario `alpaca` por subprocess, parseando su salida JSON, en vez de (o
   además de) usar `TradingClient.submit_order()` de `alpaca-py`. Mantén
   `alpaca-py` para todo lo que es datos históricos, cadena de opciones y
   consultas de cuenta — el CLI es para la parte de EJECUCIÓN, que es la
   pieza que el hackathon menciona explícitamente.

3. **Modo agente autónomo explícito**: la idea central del hackathon es que
   una IA decide y actúa. Diseña `live_agent.py` (o un modo nuevo) para que
   el flujo sea: el motor de régimen + capa de opciones deciden QUÉ hacer,
   y luego el agente arma y ejecuta el/los comando(s) `alpaca` necesarios
   él mismo, logueando cada comando ejecutado y su output crudo (para que
   quede evidencia clara de "agente autónomo operando por CLI" en el
   write-up / demo del concurso). Respeta el mismo orden defensivo que ya
   descubriste en el bug de "uncovered options" (comprar coberturas antes
   de vender descubierto).

4. **Todo cambio de ejecución real se prueba primero con `--dry-run`** del
   propio CLI de Alpaca (además del `--dry-run` que ya tiene `live_agent.py`).
   No mandes ninguna orden real sin que yo lo autorice explícitamente, igual
   que la vez anterior.

5. **Actualiza README.md y writeup.md**: agrega una sección que explique
   que el agente usa tanto `alpaca-py` (datos/backtest) como el Alpaca CLI
   real (ejecución), cumpliendo literalmente el requisito de infraestructura
   del hackathon, y enfatiza el enfoque de "agente autónomo" (decide +
   ejecuta por sí mismo, con logs verificables de cada comando).

6. Al terminar, dame un resumen de: qué archivos cambiaron, cómo quedó la
   arquitectura de ejecución (SDK vs CLI, quién hace qué), y si encontraste
   algún problema de instalación/compatibilidad en Windows que yo deba
   saber.

No dejes ningún loop ni proceso corriendo en background al terminar, y no
ejecutes ninguna orden real — solo `--dry-run` en esta etapa.
