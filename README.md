# Agente Cuántico de Opciones — Alpaca AI Trading Agents Hackathon

Agente construido para el hackathon de Alpaca (28 ago – 4 sept 2026). Reutiliza
el "Algoritmo Mutante" del proyecto App Trading original, adaptado para operar
**opciones** (requisito obligatorio del concurso) en vez del subyacente directo.

Universo operable (`config.py` -> `SYMBOLS`, 10 activos, ampliado de 3 el 26-ago
para demostrar dinamismo real y diversificar riesgo): SPY, AAPL, QQQ, MSFT,
NVDA, TSLA, AMZN, GOOGL, META, AMD — cadena de opciones semanal (7-14 DTE)
confirmada real vía Alpaca para los 10 antes de sumarlos. Ver `writeup.md`
para el detalle de por qué se amplió y qué mostró el sanity check (más
actividad real, pero diversificación más débil de lo esperado en la muestra).

**Cuenta paper oficial del hackathon: `PA3SQTOC6A22`, creada 28-ago-2026,
balance inicial $100,000.** `PA3EGUEP0QCV` fue solo la cuenta de
desarrollo/pruebas pre-contest (usada del 24 al 27-ago), no la que se juzga
— el mail de kickoff exige cuenta paper nueva y dedicada para la entrega.

**Infraestructura: desde el 28-ago-2026 (~17:20 UTC) el agente corre en
Railway** (proyecto `stellar-blessing`, servicio `live-agent`), no en la PC
de Diego, para no depender de su conectividad durante la semana juzgada.
Mismo código, misma cuenta, mismo comportamiento (10 símbolos, Iron
Condor/direccional según régimen) — solo cambia dónde corre. Build vía
`Dockerfile` (no Nixpacks/Railpack, que son el default de Railway pero no
dan control fino sobre la instalación del binario Linux del Alpaca CLI):
instala el CLI oficial (`github.com/alpacahq/cli`, pin v0.0.13) en
`/usr/local/bin/alpaca`, así que la ejecución real sigue siendo por CLI, no
un fallback a SDK. `positions_state.json` vive en un volumen persistente de
Railway (`STATE_DIR=/data`), no en el filesystem del contenedor.

**Chequear el estado del agente en Railway** (Claude no tiene acceso directo
desde una sesión cloud): correr `powershell -File scripts\snapshot_status.ps1`
desde la raíz del proyecto. Sobrescribe `railway_status.log` (últimas 150
líneas de log del deploy activo) y `railway_account_status.json` (cuenta +
posiciones reales de `PA3SQTOC6A22`) — ninguno de los dos va a git.

## Sobre el acceso a red

El proyecto se desarrolló originalmente asumiendo que el entorno cloud no
tendría salida a `alpaca.markets` (por eso existe `smoke_test.py`, con datos
sintéticos, como validación sin red). En la práctica el entorno usado para
las últimas iteraciones sí tuvo salida real a Alpaca (Market Data API y
Trading API), así que el backtest, la validación out-of-sample y el dry-run
del agente en vivo se corrieron y validaron ahí mismo. Si en algún momento
vuelves a correr esto desde un entorno sin salida a internet, `smoke_test.py`
sigue siendo la validación de lógica sin red disponible.

**Toda la data histórica y en vivo proviene de Alpaca Market Data API**
(`StockHistoricalDataClient`) y Alpaca Trading API (`TradingClient` +
Alpaca CLI, ver abajo), no de Yahoo Finance — cumpliendo el requisito del
concurso de usar la infraestructura de Alpaca de punta a punta, incluyendo
el CLI que el hackathon menciona explícitamente ("Trading API, MCP server
and CLI").

## Alpaca CLI (capa de ejecución del agente autónomo)

Además del SDK `alpaca-py` (usado para datos históricos, cadena de opciones
y consultas de cuenta), el agente puede ejecutar órdenes reales vía el
**CLI oficial de Alpaca** ([`alpacahq/cli`](https://github.com/alpacahq/cli),
[anuncio oficial](https://alpaca.markets/blog/alpaca-introduces-cli-for-trading-api/)) —
diseñado explícitamente para agentes de IA: sin prompts de confirmación,
salida JSON estructurada, flags `--dry-run`/`--schema`/`--quiet`. Esto
refuerza el enfoque de "agente autónomo que decide y actúa por sí mismo"
del hackathon: `live_agent.py` arma el comando `alpaca` y lo ejecuta él
mismo por subprocess, logueando cada comando y su output crudo.

### Instalación en Windows

El README oficial del CLI documenta `go install` y Homebrew (Mac/Linux). En
Windows, sin toolchain de Go instalado, el camino más simple es el binario
precompilado de GitHub Releases:

```bash
# Descargar el .zip de la última release para windows_amd64 desde
# https://github.com/alpacahq/cli/releases, verificar su sha256 contra
# checksums.txt (mismo release), y extraer alpaca.exe a tools/alpaca.exe
```

`cli_executor.py` busca el binario primero en `PATH` (`alpaca`) y si no lo
encuentra usa `tools/alpaca.exe`. Si tenés Go instalado, `go install
github.com/alpacahq/cli/cmd/alpaca@latest` también funciona y queda en tu
`PATH` de Go.

**Verificar instalación:**
```bash
alpaca version
alpaca doctor      # confirma "active profile: paper" y conectividad a Trading/Data API
```

El CLI lee `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` directo del entorno (los
mismos nombres que ya usa `.env`) y opera en **paper por default** — hace
falta `ALPACA_LIVE_TRADE=true` explícito para operar en vivo, que este
proyecto nunca setea.

### Cómo se usa

```bash
python live_agent.py --dry-run --use-cli --max-cycles 1   # evalúa todo, ejecución simulada vía CLI
python live_agent.py --use-cli                             # ejecución real vía CLI en vez del SDK
```

`--use-cli` solo cambia CÓMO se abren/cierran posiciones (subprocess al
binario `alpaca` en vez de `TradingClient.submit_order()`); todo lo demás
(datos, régimen, cadena de opciones, risk gates) sigue igual.

**Mismo orden defensivo que con el SDK:** las legs se mandan compradas
primero, vendidas después (`cli_executor.ejecutar_estrategia_cli`), por el
mismo motivo que en `executor.py` — una leg vendida sin su cobertura ya en
la cuenta se rechaza como "uncovered" (confirmado en vivo contra la cuenta
paper, ambos caminos SDK y CLI).

**Límite real encontrado:** `alpaca position close` no tiene `--dry-run`
(solo `order submit` lo soporta) -- ejecuta directo, sin previsualización a
nivel CLI. Por eso `cli_executor.cerrar_posicion_cli` no reutiliza el
patrón `dry_run=True` por default de las demás funciones del módulo: pide
`confirmar_real=True` explícito, y sin eso no llama al CLI en absoluto (para
no dar una falsa sensación de que hay preview cuando no la hay).

**Mejora futura no implementada:** el CLI soporta órdenes multi-leg
nativas (`order submit --order-class mleg --legs '...'`), que mandarían
las 4 patas del Iron Condor como un solo spread atómico -- eliminando de
raíz el problema de "uncovered options" en vez de resolverlo por orden de
ejecución. No se implementó en esta pasada (el pedido era replicar el fix
secuencial ya validado), pero queda como camino más robusto a futuro.

## Alpaca MCP server (capa conversacional de consulta/monitoreo)

El requisito del hackathon menciona explícitamente "Trading API, MCP server
and CLI". Las dos primeras piezas cubren la ejecución (SDK `alpaca-py` +
CLI oficial, ambas arriba); el **MCP server oficial de Alpaca**
([`alpacahq/alpaca-mcp-server`](https://github.com/alpacahq/alpaca-mcp-server))
cubre un rol distinto y complementario: **consulta y monitoreo
conversacional** de la cuenta y del mercado desde Claude Code, no un
segundo camino de ejecución.

**Por qué no ejecuta órdenes:** `live_agent.py` es el único proceso que
abre/cierra posiciones reales (vía SDK o CLI, según `--use-cli`). Si el
MCP server también pudiera colocar órdenes, dos "traders" (el loop
autónomo y quien esté conversando con Claude Code) podrían pisarse sobre
la misma cuenta paper sin coordinación entre sí. Por eso la instalación
se limitó a un conjunto de herramientas de solo lectura: cuenta, histórico
de fills/actividad, datos de mercado (barras, quotes, trades), cadena de
opciones con griegos/IV, noticias, y documentación de la API. No incluye
ninguna herramienta de colocar, modificar o cancelar órdenes ni de
cerrar posiciones.

**Instalación:**
```bash
claude mcp add alpaca --scope user --transport stdio uvx alpaca-mcp-server \
  --env ALPACA_API_KEY=<key de .env> \
  --env ALPACA_SECRET_KEY=<secret de .env> \
  --env ALPACA_PAPER_TRADE=true
```
Verificar conexión en Claude Code con `/mcp`.

**Evidencia real (26-ago-2026, contra la cuenta paper `PA3EGUEP0QCV`):**

- *Consulta:* estado de cuenta actual →
  `equity: $97,568.76`, `cash: $82,892.76`, `position_market_value: $14,676`
  (vía `mcp__alpaca__get_account_info`).
- *Consulta:* actividad de fills recientes de las 3 posiciones abiertas
  (`SPY260902C00782000`, `AAPL260902P00307500`, `QQQ260902C00726000`) →
  confirmados los fills de apertura del ciclo de `live_agent.py` de las
  15:22 del 26-ago (vía `mcp__alpaca__get_account_activities`, tipo `FILL`).
- *Consulta:* cadena de opciones de SPY a 7-14 DTE (venc. 2026-09-02) →
  devolvió strikes, bid/ask, IV y griegos reales (ej. `SPY260902C00804000`
  bid 0.04 / ask 0.05, delta ≈ 0.004) usados para el análisis de calibración
  del Iron Condor a DTE corto (vía `mcp__alpaca__get_option_chain`).

## Instalación (en tu PC)

```bash
cd alpaca-hackathon
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

El archivo `.env` ya viene con las API keys de la cuenta paper oficial del
concurso (cuenta `PA3SQTOC6A22`, creada 28-ago-2026, balance $100,000).
No las compartas ni las subas a un repo público.

## Verificar la conexión

```bash
python test_connection.py
```

Debe mostrar el equity ($100,000) y el estado de la cuenta.

## Backtest con datos reales

```bash
python backtest.py --symbol SPY --years 3
```

Compara el rendimiento de la estrategia de opciones (motor completo: Long
Call / Long Put / Iron Condor de 4 legs, con Black-Scholes usando volatilidad
realizada como proxy) contra buy & hold del subyacente. Ajusta `--symbol`
(SPY, AAPL, QQQ, etc.) y `--years`.

### Resultados finales (3 años, motor con Iron Condor completo)

Con `TAKE_PROFIT_PCT = 0.05` y `EXIT_DTE_BUFFER = 10` en `config.py`:

| Symbol | Estrategia | Buy & Hold | Trades |
|---|---|---|---|
| SPY | 33.58% | 38.45% | 44 |
| AAPL | 17.95% | 40.08% | 56 |
| QQQ | 16.18% | 43.84% | 46 |

Estos números bajaron frente a una iteración anterior (SPY 42.00% / AAPL
37.72% / QQQ 19.57%) que simplificaba el régimen `RANGO_LATERAL` a "no
operar nada". Al implementar el Iron Condor de 4 legs real para ese régimen,
el capital que antes quedaba ocioso durante las rachas laterales ahora se
compromete por 1-3 semanas en un condor — lo cual a veces bloquea una
oportunidad direccional más rentable que habría abierto si el símbolo salía
del régimen lateral antes. Es un costo de oportunidad real del diseño
"una posición a la vez por símbolo", no un error de la simulación: los
condores en sí dieron P&L neto positivo o cercano a cero en los tres
símbolos (ver desglose por `tipo` en `trades` si se llama `simular()`
directamente).

### Recalibración para la ventana de 7 días del concurso (26-ago)

Con `TARGET_DTE_MIN=7`, `TARGET_DTE_MAX=14`, `EXIT_DTE_BUFFER=2` y
`IRON_CONDOR_SHORT_PCT=0.03` (bajado de 0.05, ver más abajo):

| Symbol | Estrategia | Buy & Hold | Trades |
|---|---|---|---|
| SPY | 14.35% | 38.92% | 93 |
| AAPL | 260.43% | 41.48% | 97 |
| QQQ | 87.06% | 44.87% | 87 |

SPY empeora frente a la tabla de `DTE 21-45`/buffer 10 de arriba (33.58%→14.35%,
ahora bien por debajo de buy & hold); AAPL y QQQ mejoran mucho (17.95%→260.43%,
16.18%→87.06%). Un cambio de esa magnitud en un solo parámetro, sobre ~90-100
trades por símbolo, es la misma señal de sobreajuste por muestra chica que ya
documenta la sección de "Lecciones metodológicas" del proyecto original — no
tomar estos números como edge confirmado, solo como la validación de que la
recalibración cumple su objetivo real: **resolver posiciones dentro de la
semana del concurso**, no necesariamente mejorar el retorno.

Ahí sí hay mejora clara: con la calibración vieja (DTE 21-45) solo 21-34% de
las operaciones se resolvían en 7 días corridos. Con DTE 7-14, sobre 277
trades combinados (SPY/AAPL/QQQ), **38.3%** se resuelve en ≤7 días (SPY 41.9%,
AAPL 36.1%, QQQ 36.8%), con mediana de 8 días hasta resolución (media 6.9). El
ruido semanal sigue dominando sobre la señal (ventanas rodantes de 7 días:
media 1.22%, desvío 5.78% → ratio ruido/señal ≈4.75), pero la ventana de
resolución está mucho más alineada con el plazo del concurso que antes.

**Sobre `IRON_CONDOR_SHORT_PCT`:** a 0.05 (original) el crédito neto real de
un Iron Condor a 7-14 DTE es casi nulo (SPY, datos de mercado del 26-ago:
~$11/contrato de crédito contra ~$2,400-2,600 de riesgo por ancho de ala —
ratio ≈0.5%, la comisión de las 4 patas ya se come casi todo). Se bajó a 0.03
(~$43.5/contrato de crédito, ratio ≈1.8%). Se validó contra 0.02 corriendo el
backtest completo de 3 años con los tres valores: SPY y QQQ mejoran monótono
al bajar el strike (0.05→0.03→0.02: SPY 9.96%→14.35%→34.59%, QQQ
74.83%→87.06%→122.35%), pero AAPL no — 0.03 es su mejor valor de los tres
(224.95%→**260.43%**→165.48% con 0.02). Promediando los 3 símbolos, 0.03 da el
mejor resultado combinado (120.61% vs. 103.25% en 0.05 y 107.47% en 0.02).
Como el proyecto usa parámetros globales por diseño (ver conclusión de
`oos_validation.py` más abajo: no reoptimizar por símbolo), **0.03 queda
como el valor validado**, no solo recomendado.

### Validación out-of-sample (`oos_validation.py`)

```bash
python oos_validation.py
```

Parte cada símbolo en ventana de entrenamiento (grid search de
`TAKE_PROFIT_PCT` × `EXIT_DTE_BUFFER`) + ~1 año de prueba nunca visto durante
ese ajuste. Nota sobre el tamaño real de la ventana: el split pide "últimos
365 días" para test, pero `calcular_indicadores` descarta ~215 filas de
warm-up (rolling de `Volatilidad`=15 + `Vol_Promedio`=200), así que
entrenamiento queda en ~14 meses (286 filas, 2024-07-03 a 2025-08-22) sobre
~3 años de historial total, no ~2 años.

Hallazgo principal (este sí es limpio, sin fuga): el combo que ganó en
entrenamiento para SPY (`TP=0.05, DTE=14`) pasa de +17.43% en train a
**-0.29% fuera de muestra** — prácticamente break-even, un ejemplo directo
de sobreajuste al reoptimizar por símbolo sobre una ventana corta.

| Symbol | Ganador en TRAIN | Estrategia en TEST (con esos params) | Buy & Hold (TEST) |
|---|---|---|---|
| SPY | TP=0.05 DTE=14 (+17.43% en train) | **-0.29%** | 18.83% |
| AAPL | TP=0.10 DTE=3 (+20.70% en train) | 16.78% | 36.62% |
| QQQ | TP=0.06 DTE=14 (+19.78% en train) | 4.51% | 23.85% |

*Nota de metodología:* el script también compara esto contra correr el
default global (`TP=0.05, DTE=10`) sobre la misma ventana de test, y el
default gana con margen en los tres símbolos. Esa comparación tiene fuga de
información -- el default se eligió por grid search sobre el período
**completo** de 3 años (turno anterior de este proyecto), que incluye la
ventana de test -- así que no es una prueba limpia de generalización, solo
un chequeo de consistencia. La evidencia realmente limpia de que el default
no está sobreajustado es la meseta ancha del grid original: `EXIT_DTE_BUFFER
>= 7` rinde 15-21% en QQQ para *todo* `TAKE_PROFIT_PCT` entre 0.04 y 0.12,
mientras que buffer 3/5 es negativo en toda la grilla -- una superficie de
parámetros así de plana es mejor evidencia de robustez que un solo punto
out-of-sample con ~20-30 trades.

Conclusión práctica: **no re-optimizar por símbolo** sobre ventanas cortas
-- quedarse con el default global (elegido por la forma de la meseta, no
por maximizar un símbolo) y usar `oos_validation.py` para chequear
cualquier cambio de parámetros antes de adoptarlo.

### Limitación conocida del pricing

El backtest valora las opciones con Black-Scholes usando la volatilidad
realizada del subyacente como proxy de la implícita, sin prima de riesgo de
volatilidad ni bid-ask spread. En la práctica las opciones cotizan por
encima de la volatilidad realizada, así que una estrategia de opciones
largas (Long Call/Put) está comprando sistemáticamente más barato que en
mercado real — los números de arriba son optimistas en magnitud absoluta,
aunque la dirección de la mejora (take-profit + salida antes del
vencimiento) es estructuralmente válida.

## Correr el agente en vivo (paper trading real)

```bash
python live_agent.py                                            # loop normal, cada 15 min, indefinido
python live_agent.py --dry-run --max-cycles 2 --interval-seconds 30   # prueba rápida, no envía órdenes
```

Flags disponibles:
- `--dry-run`: corre el ciclo completo (régimen, sentimiento, estrategia,
  risk gates) y loggea qué haría, pero nunca llama `submit_order` ni cierra
  posiciones reales. Úsalo para validar antes de dejarlo operando en serio.
- `--interval-seconds N`: segundos entre ciclos (default 900 = 15 min). No
  se hardcodeó un valor bajo en el archivo para pruebas rápidas — se pasa
  por flag para no arriesgar dejarlo corriendo accidentalmente a un
  intervalo de prueba.
- `--max-cycles N`: corre N ciclos y termina, en vez de loop infinito.

Por símbolo (los definidos en `config.py` -> `SYMBOLS`), cada ciclo primero
revisa si ya hay una posición abierta (persistida en `positions_state.json`)
y la cierra si toca stop loss / take profit / buffer de vencimiento; si no
hay posición y el régimen lo permite, construye y ejecuta una estrategia
nueva.

**Estado y logs:**
- `positions_state.json` (se crea junto al script) guarda las posiciones
  abiertas -- necesario porque Alpaca no expone el precio del SUBYACENTE al
  momento de abrir una posición de opción, y las reglas de stop
  loss/take profit se miden sobre ese precio, no sobre la prima. Sobrevive
  reinicios del script.
- `live_agent.log` recibe todo lo que también se imprime en consola, para
  poder revisar qué hizo el agente durante la semana del concurso aunque
  hayas cerrado la terminal.

**Manejo de errores:** la conexión inicial reintenta hasta 5 veces con
backoff antes de abortar; dentro del loop, un error de red/API al evaluar
un símbolo se loggea y el ciclo sigue con el resto de los símbolos (no
tumba el proceso completo). Si falla el cierre de alguna leg de una
posición, solo esa leg se reintenta en el próximo ciclo -- las legs que sí
se cerraron no se vuelven a tocar (se detectan por ausencia en
`obtener_posiciones`).

**Por verificar en el primer Iron Condor real que se llene:** el crédito
recibido se calcula como `-sum(cost_basis)` de las 4 legs reportadas por
Alpaca, asumiendo que Alpaca reporta `cost_basis` negativo para las legs
vendidas. Esto no se pudo probar contra un fill real desde acá. Cuando
corra el primer condor en vivo, revisa en `live_agent.log` la línea
`crédito recibido confirmado por Alpaca: X` -- X debería ser positivo y del
orden de $100-400 para los anchos de ala configurados (`IRON_CONDOR_WING_PCT
= 0.03`). Si sale negativo o con una magnitud rara, el take profit/stop del
condor va a estar invertido y hay que ajustar el signo en
`evaluar_y_cerrar_posicion` (`live_agent.py`).

**Para que sobreviva reinicios de Windows / cierre de sesión**, no hace
falta un cambio de código -- corre el proceso vía el **Programador de
tareas de Windows**:
1. Programador de tareas -> Crear tarea básica.
2. Desencadenador: "Al iniciar el equipo" (o el que prefieras).
3. Acción: "Iniciar un programa" -> programa `python`, argumentos
   `live_agent.py`, "Iniciar en" = la carpeta del proyecto (para que
   encuentre `.env` y `positions_state.json`).
4. En Configuración, marca "Ejecutar la tarea tan pronto como sea posible
   después de una hora de inicio programada omitida" para que se recupere
   si el equipo estaba apagado.

Alternativa: dejarlo corriendo dentro de una sesión de `screen`/`tmux` si
corres esto en Linux/WSL, o como servicio con `nssm` en Windows si quieres
que sobreviva también al cierre de sesión del usuario (no solo reinicios).

## Arquitectura

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Parámetros centrales (heredados del algoritmo mutante original + take profit / DTE buffer / reglas de condor validados por backtest) |
| `regime_engine.py` | Cerebro Matemático: detecta régimen (tendencial alcista/bajista, rango lateral, defensivo) |
| `sentiment_engine.py` | NLP (VADER) sobre noticias de Alpaca News API — interruptor de emergencia |
| `options_selector.py` | Traduce el régimen a una estructura de opciones concreta vía la cadena de Alpaca (respeta la ventana de vencimiento `TARGET_DTE_MIN..MAX` y fija un vencimiento común para las 4 legs del Iron Condor) |
| `risk_manager.py` | Sizing (2% equity/operación), stop loss 3% y take profit 5% sobre el subyacente (direccionales), gate de salida por crédito para el Iron Condor |
| `executor.py` | Envía las órdenes reales a Alpaca Trading API (paper) vía SDK `alpaca-py`, pierna por pierna |
| `cli_executor.py` | Envía las órdenes reales vía el Alpaca CLI (subprocess), como camino alternativo a `executor.py` -- activado con `live_agent.py --use-cli` |
| `bs_pricing.py` | Pricing Black-Scholes (usado solo en el backtest offline) |
| `backtest.py` | Backtest histórico con datos reales de Alpaca Market Data API (Long Call/Put + Iron Condor de 4 legs) |
| `oos_validation.py` | Valida que los parámetros de salida no estén sobreajustados (split train/test por fecha) |
| `live_agent.py` | Loop principal para operar en vivo: abre posiciones nuevas y cierra las existentes por stop loss/take profit/vencimiento, con estado persistido y logging a archivo |

## Mapeo régimen → estructura de opciones

| Régimen | Estructura | Lógica | Salida |
|---|---|---|---|
| Tendencial alcista | Long Call (~2% OTM) | Expresa la tendencia con riesgo limitado a la prima | Stop loss 3% / take profit 5% sobre el subyacente, o `EXIT_DTE_BUFFER` días antes del vencimiento |
| Tendencial bajista | Long Put (~2% OTM) | Expresa la tendencia bajista con riesgo limitado a la prima | Igual que Long Call, invertido |
| Rango lateral | Iron Condor (4 legs, mismo vencimiento) | Vende premium, riesgo definido por el ancho de las alas | Stop a `IRON_CONDOR_STOP_MULT`x el crédito recibido, take profit al capturar `IRON_CONDOR_PROFIT_TARGET_PCT` del crédito, o `EXIT_DTE_BUFFER` |
| Defensivo (vol. alta / sentimiento negativo) | No abrir nuevas posiciones | Prioriza preservar capital | Si hay una posición abierta y el régimen pasa a defensivo, se loggea para revisión manual (no se fuerza el cierre automáticamente; ver `necesita_cobertura_defensiva`) |

## Notas para el write-up del concurso

Ver `writeup.md` en este mismo directorio — resume la lógica de IA, los risk
gates y la implementación de infraestructura Alpaca en una página, listo
para adjuntar en la entrega.
