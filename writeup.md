# Agente Cuántico de Opciones — Alpaca AI Trading Agents Hackathon

## Qué hace

Un agente de trading que opera **opciones** (requisito obligatorio del
concurso) sobre un universo de **10 activos líquidos** — SPY, AAPL, QQQ
(los del concurso) más MSFT, NVDA, TSLA, AMZN, GOOGL, META y AMD, todos
con cadena de opciones semanal real confirmada vía Alpaca.

**Cuenta paper oficial del hackathon: `PA3SQTOC6A22`, creada 28-ago-2026,
balance inicial $100,000.** `PA3EGUEP0QCV` fue solo la cuenta de
desarrollo/pruebas pre-contest, no la que se juzga.

**Infraestructura: desde el 28-ago-2026 corre en Railway**, no en la PC,
para no depender de la conectividad de Diego durante la semana juzgada —
mismo código, misma cuenta, ejecución real sigue vía Alpaca CLI (binario
Linux instalado en el build, no un fallback a SDK). La migración expuso y
corrigió dos bugs reales de infraestructura (documentados como evidencia
de hardening, no ocultados): un `preDeployCommand` que sembraba el estado
de posiciones antes de que el volumen persistente estuviera montado
-- causó apertura duplicada real de 3 Iron Condors, remediada a mano
cerrando los legs extra contra el broker -- y un `config.py` con el
universo de 10 símbolos sin commitear a git, por lo que el primer intento
de deploy corría silenciosamente con el universo viejo de 3. Ambos
corregidos antes de cortar el proceso de la PC.

Reutiliza el "Algoritmo Mutante" del proyecto App
Trading original como cerebro de detección de régimen, y traduce cada
régimen a una estructura de opciones concreta en vez de operar el
subyacente directo. Ampliar de 3 a 10 activos (26-ago) fue una decisión
deliberada de producto, no solo técnica: demuestra el dinamismo real del
agente (analiza y opera sobre 10 nombres cada ciclo, no 3) y busca
diversificar el riesgo — aunque un sanity check de 2 semanas mostró que
esa diversificación es más débil de lo esperado (ver más abajo).

## Lógica de IA: régimen → estructura

`regime_engine.py` calcula medias móviles (10/30) y volatilidad realizada
sobre el histórico diario, y clasifica el mercado en 4 regímenes:
**tendencial alcista/bajista**, **rango lateral** o **defensivo** (spike de
volatilidad o sentimiento de noticias negativo — NLP vía VADER sobre
titulares de Alpaca News API, `sentiment_engine.py`, actúa como interruptor
de emergencia que puede forzar defensivo aunque el precio no lo refleje
todavía).

`options_selector.py` mapea cada régimen a una estructura, consultando la
cadena de opciones real de Alpaca:

| Régimen | Estructura |
|---|---|
| Tendencial alcista | Long Call (~2% OTM) |
| Tendencial bajista | Long Put (~2% OTM) |
| Rango lateral | Iron Condor (4 legs, mismo vencimiento, vende premium) |
| Defensivo | No abrir posiciones nuevas |

## Risk gates (`risk_manager.py`)

- Sizing: máx 2% del equity en riesgo por operación.
- Stop loss 3% / take profit 5% sobre el precio del **subyacente** (nunca
  sobre la prima — la prima es apalancada, un stop sobre ella cierra
  posiciones por ruido normal).
- Para el Iron Condor: stop a 2x el crédito recibido, take profit al
  capturar 50% del crédito máximo (reglas estándar de venta de premium,
  ya que un condor pierde con el subyacente en cualquier dirección).
- Salida forzada `EXIT_DTE_BUFFER` días antes del vencimiento, para evitar
  el crush de theta/gamma de los últimos días.
- Máximo de posiciones concurrentes, contadas por símbolo/estrategia (no
  por leg individual).

Estos parámetros se validaron con backtest de 3 años de datos reales de
Alpaca y con una validación out-of-sample que mostró que reoptimizar por
símbolo sobreajusta (`oos_validation.py`) — se usan los mismos parámetros
globales en los tres símbolos, elegidos por robustez cruzada, no por
maximizar uno.

El 26-ago se recalibró la ventana de opciones (`TARGET_DTE_MIN/MAX` de
21-45 a 7-14 días, `EXIT_DTE_BUFFER` de 10 a 2) para que las posiciones se
resuelvan dentro de la semana de 7 días que juzga el concurso, en vez de en
un horizonte de 3-6 semanas. Resultado medido sobre el propio backtest:
el % de operaciones que se resuelve en ≤7 días corridos subió de 21-34% a
**38.3%** (mediana 8 días), la mejora real que buscaba el cambio. Los
retornos de 3 años bajo esta calibración corta no se citan como edge
probado — sobre ~90-100 trades por símbolo, un solo cambio de parámetro
movió el resultado en un rango demasiado amplio (de -60% a +160% relativo)
para distinguirse de sobreajuste por muestra chica; el diseño se defiende
por la mejora de resolución temporal, no por el retorno del backtest.
`IRON_CONDOR_SHORT_PCT` se bajó de 0.05 a 0.03 y sí quedó validado con
datos reales de la cadena de opciones de hoy: a 0.05 el crédito neto de un
condor a 7-14 DTE es casi nulo (~0.5% del riesgo por ancho de ala) una vez
descontada la comisión de las 4 patas; a 0.03 el crédito sube a ~1.8%.

`UMBRAL_TENDENCIA` se subió de 0.7% a 2.5% (26-ago): decisión de producto
para sesgar el diseño hacia Iron Condor sobre direccional — vender premium
gana con el paso del tiempo (theta) si el subyacente no se mueve mucho,
mientras que una posición direccional necesita acertar dirección *y*
timing en la ventana corta del concurso, una exigencia más alta. Validado
en 3 semanas históricas: 0 entradas direccionales buenas descartadas, 4-5
malas evitadas, mejora de ~$3,200 en el mismo backtest. Con muestra más
amplia (6 semanas) el sesgo se sostiene sin eliminar por completo ninguna
dirección de tendencia (se había visto ese riesgo de sobreajuste en la
muestra chica, no se confirmó con más datos).

## Universo de 10 activos (dinamismo + intento de diversificación)

`SYMBOLS` se amplió de 3 a 10 (26-ago): SPY, AAPL, QQQ + MSFT, NVDA, TSLA,
AMZN, GOOGL, META, AMD — los 7 nuevos confirmados con cadena de opciones
real a 7-14 DTE vía Alpaca antes de sumarlos. `MAX_CONCURRENT_POSITIONS`
subió de 3 a 5 (10% del equity total en riesgo simultáneo, el tope que nos
propusimos no superar). Honestidad sobre el resultado: en un sanity check
de 2 semanas, el universo ampliado sí generó más actividad real (8 de 10
símbolos abrieron posición en una semana, vs. 2 de 3 antes), pero **no
demostró la diversificación esperada** — en la semana 17-21 ago, 5 de los
7 símbolos nuevos perdieron simultáneamente (large-cap tech correlacionado
en semanas de riesgo), empeorando el P&L agregado de esa semana en vez de
amortiguarlo. El valor real del cambio es el dinamismo (más activos
analizados y operados en vivo cada ciclo), no una reducción de riesgo
comprobada.

## Backtest final consolidado (6 semanas, config completa)

Con toda la configuración final aplicada (DTE 7-14, buffer 2,
`IRON_CONDOR_WING_PCT=0.02`, `IRON_CONDOR_SHORT_PCT=0.03`,
`UMBRAL_TENDENCIA=0.025`), se simuló día por día SPY/AAPL/QQQ sobre 6
semanas históricas reales (13-jul a 21-ago 2026 — el feed de datos de
Alpaca disponible no alcanza más atrás de 06-jul-2026, así que las 6
semanas están concentradas en ~7 semanas de calendario, no en momentos de
mercado independientes entre sí). Resultado: **-$1,006.48** agregado sobre
18 combinaciones símbolo/semana (7 positivas, 6 negativas, 5 sin operar).
Mejora real de +$3,201.59 sobre las mismas 3 semanas con la config vieja
(-$4,920.35), pero las 3 semanas nuevas (nunca usadas para ajustar nada)
dieron signo opuesto a las 3 conocidas (+$712.28 vs. -$1,718.76) — la
varianza semana a semana es mayor que cualquier tendencia central. No
prometemos una semana positiva; el número honesto es que el diseño mejoró
de forma medible sobre el mismo terreno de prueba, sin que eso garantice
el resultado de la semana del concurso.

## Infraestructura Alpaca (de punta a punta)

- **Market Data API** (`alpaca-py`, `StockHistoricalDataClient`): histórico
  diario para backtest y para el régimen en vivo.
- **News API** (`alpaca-py`, `NewsClient`): titulares para el sentimiento.
- **Trading API** (`alpaca-py`, `TradingClient`): cadena de opciones,
  cuenta, posiciones, y ejecución de órdenes (`executor.py`).
- **Alpaca CLI** (`alpacahq/cli`, oficial): capa de ejecución alternativa
  vía subprocess (`cli_executor.py`, activada con `live_agent.py
  --use-cli`), y refuerza el enfoque de agente autónomo: el motor de
  régimen decide, y el agente arma y ejecuta el comando `alpaca` él mismo,
  logueando cada comando y su output crudo.
- **Alpaca MCP server** (`alpacahq/alpaca-mcp-server`, oficial): capa
  conversacional de consulta/monitoreo desde Claude Code — cuenta,
  actividad de fills, datos de mercado y cadena de opciones con
  griegos/IV. Instalado con un conjunto de herramientas restringido a
  solo lectura, sin colocar/cancelar órdenes: el único camino de
  ejecución real sigue siendo `live_agent.py` (SDK o CLI), para no tener
  dos procesos operando la misma cuenta paper sin coordinarse. Entre las
  tres piezas (Trading API, CLI, MCP server) cubren de punta a punta el
  requisito explícito del hackathon de usar "Trading API, MCP server and
  CLI" — detalle de instalación y evidencia de uso real en `README.md`.

## Agente autónomo: decide y actúa

`live_agent.py` corre en loop (cada 15 min en mercado abierto): descarga
datos, detecta régimen, consulta sentimiento, construye la estructura de
opciones, aplica los risk gates, y si aprueba, ejecuta — vía SDK o vía CLI
(`--use-cli`) — sin intervención humana en el ciclo. El mismo loop gestiona
el cierre de posiciones abiertas por stop loss/take profit/vencimiento en
cada ciclo. Estado persistido en `positions_state.json` (sobrevive
reinicios) y logging completo en `live_agent.log`.

## Validado en la cuenta paper real

Una orden de prueba real (Iron Condor completo, 4 legs, qty=1) se ejecutó
contra `PA3EGUEP0QCV` para verificar el sistema de punta a punta: régimen →
estrategia → risk gate → ejecución → contabilidad de crédito. Crédito
recibido: +$126.00 (signo correcto). En el camino se encontraron y
corrigieron 3 bugs reales que solo un test contra la cuenta real podía
revelar: contratos con 0 días a vencimiento (`options_selector.py` no
filtraba por ventana de DTE), las 4 legs del condor con vencimientos
distintos entre sí, y el orden de ejecución de legs rechazado por Alpaca
como "uncovered options" (se corrigió a comprar cobertura antes de vender).
