Contexto: la simulación de la semana 03-07 ago encontró algo importante,
no solo "mal rendimiento" — un bug de sizing. SPY nunca pudo abrir el Iron
Condor en los 3 días que estuvo en RANGO_LATERAL: el riesgo por contrato
(~$2,060-2,100, viene de `IRON_CONDOR_WING_PCT=0.03` sobre el precio de
SPY ~$765-780) siempre supera `MAX_RISK_PER_TRADE_PCT=0.02` de $100,000
($2,000), así que el sizing calcula qty=0 y la operación se rechaza. Esto
no es específico de esa semana — con estos parámetros, el Iron Condor de
SPY probablemente NUNCA puede abrirse, en ninguna semana, mientras el
precio de SPY siga en este rango. Hay que confirmarlo y arreglarlo.

No requiere confirmación previa (análisis + fix de código + backtest, no
toca la cuenta real) — corré todo y reportá con números.

## Parte 1 — Diagnóstico

Confirmá el cálculo exacto: para SPY al precio actual, ¿cuánto da el
riesgo máximo real de un Iron Condor con `IRON_CONDOR_WING_PCT=0.03`
(ancho de ala en USD, menos el crédito recibido, x100 por contrato)? ¿A
partir de qué precio de SPY o qué `IRON_CONDOR_WING_PCT` el riesgo de 1
contrato SÍ entraría en el presupuesto de $2,000 (2% de $100k)? Hacé el
mismo chequeo para AAPL y QQQ — ¿tienen el mismo problema, o por su precio
más bajo el condor ahí sí es sizeable?

## Parte 2 — Arreglo

Con datos concretos de la Parte 1, ajustá lo que corresponda para que el
Iron Condor sea sizeable en al menos 1 contrato para los 3 símbolos sin
violar el límite de riesgo del 2%: `IRON_CONDOR_WING_PCT` más chico,
`MAX_RISK_PER_TRADE_PCT` más grande, o lo que el número real indique. Si
hay trade-off (ala más angosta = menos crédito recibido = peor ratio
riesgo/recompensa), decilo explícito y elegí con criterio, no el valor que
dé mejor P&L en la semana ya simulada — esto es un fix de sizing, no una
calibración a una semana puntual.

## Parte 3 — Revalidar con el fix

Re-corré `simulacion_semana.py` para la misma semana (03-07 ago,
SPY/AAPL/QQQ) con el fix aplicado. Confirmá que SPY ahora sí puede abrir
el Iron Condor cuando el régimen lo indica.

## Parte 4 — Ampliar la muestra (esto es lo más importante)

No juzgues el rendimiento del agente por una sola semana. Corré la misma
simulación día por día para 2-3 semanas históricas más, de regímenes
distintos a la de 03-07 ago (ej. una semana de mediados de julio y otra de
mediados de agosto, o las que el histórico disponible permita, elegí
semanas con carácter de mercado distinto si podés identificarlo: una más
tendencial, una más lateral). Mismo formato de reporte día por día que ya
armaste para la primera semana.

## Reporte

Números concretos de las 4 partes: el cálculo exacto de la Parte 1, qué
parámetro cambiaste y a qué valor en la Parte 2, la confirmación de que
SPY ya abre condor en la Parte 3, y las tablas de P&L vs buy&hold de cada
semana adicional de la Parte 4. Si en alguna de las semanas nuevas el
agente también da mal, decilo tal cual — el objetivo es entender el
rendimiento real, no confirmar que "ya está bien".
