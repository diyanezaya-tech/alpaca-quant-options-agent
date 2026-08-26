"""
Configuración central del Agente Cuántico - Alpaca AI Trading Agents Hackathon
Hereda los parámetros del "Algoritmo Mutante" del proyecto original.
"""

# --- Universo operable ---
SYMBOLS = ["SPY", "AAPL", "QQQ"]  # subyacentes sobre los que se operan opciones

# --- Parámetros del Cerebro Matemático (heredados) ---
MEDIA_RAPIDA_VENTANA = 10
MEDIA_LENTA_VENTANA = 30
VOLATILIDAD_VENTANA = 15
VOL_PROMEDIO_VENTANA = 200          # se ajusta dinámicamente si hay poco histórico

UMBRAL_TENDENCIA = 0.007            # 0.7% - filtro de ruido / confirmación de tendencia
STOP_LOSS = 0.03                    # 3% - gestión de riesgo absoluto
COMISION = 0.001                    # 0.1% - control de costos (equities, referencia)

VOL_SPIKE_MULT = 1.5                # si vol > vol_promedio * este factor -> régimen defensivo

# --- Inteligencia de texto (NLP / sentimiento) ---
SENTIMENT_DEFENSIVE_THRESHOLD = -0.35   # score < esto fuerza modo defensivo
SENTIMENT_HEADLINE_LIMIT = 30

# --- Capa de opciones ---
# Recalibrado 26-ago para la ventana de 7 días corridos del hackathon (28 ago-4 sept):
# con DTE 21-45 el ciclo de vida de una posición excede la semana completa del concurso
# (backtest: 74-79% de los trades seguían abiertos pasados 7 días). Bajado a 7-14 para
# maximizar la probabilidad de que las posiciones se resuelvan (TP/SL/vencimiento)
# dentro de la ventana que se juzga. Aplica solo a posiciones abiertas de acá en más.
TARGET_DTE_MIN = 7                  # días a vencimiento mínimos preferidos
TARGET_DTE_MAX = 14
OTM_PCT_DIRECTIONAL = 0.02          # 2% fuera del dinero para calls/puts direccionales
IRON_CONDOR_SHORT_PCT = 0.03        # strikes cortos ~3% fuera del dinero (bajado de 0.05 el 26-ago para la ventana DTE 7-14 del hackathon)
IRON_CONDOR_WING_PCT = 0.03         # ancho de las alas del condor
PROTECTIVE_PUT_OTM_PCT = 0.03       # protective put ~3% fuera del dinero

# Salida para estructuras de crédito (Iron Condor): pierde con el subyacente
# en cualquier dirección, así que no aplican los gates direccionales
# (evaluar_stop_loss/evaluar_take_profit). Reglas estándar de venta de premium:
IRON_CONDOR_PROFIT_TARGET_PCT = 0.50   # cerrar al capturar 50% del crédito máximo recibido
IRON_CONDOR_STOP_MULT = 2.0            # cerrar si la pérdida flotante llega a 2x el crédito recibido

# --- Gestión de riesgo / tamaño de posición ---
MAX_RISK_PER_TRADE_PCT = 0.02       # máx 2% del equity en riesgo por operación
MAX_CONCURRENT_POSITIONS = 3
OPTIONS_COMMISSION_PER_CONTRACT = 0.65  # referencia Alpaca

TAKE_PROFIT_PCT = 0.05              # 5% a favor del subyacente -> toma ganancia (ajustado por grid search SPY/AAPL/QQQ)
EXIT_DTE_BUFFER = 2                  # cerrar por vencimiento cuando falten <= N días (bajado de 10 -> 2 junto con
                                     # el DTE 7-14: con buffer=10 casi toda posición nueva se cerraría por buffer
                                     # a los 0-4 días de abierta, sin dejar margen a que actúe el stop/take-profit)

# --- Cuenta ---
STARTING_BALANCE = 100_000
