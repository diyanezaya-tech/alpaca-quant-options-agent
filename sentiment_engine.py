"""
Inteligencia de Texto - Sentimiento de Noticias (NLP)

Usa VADER (vía NLTK) para analizar titulares macroeconómicos/de mercado y
producir un score de -1 (pánico) a 1 (euforia). Actúa como interruptor de
emergencia del régimen: si el score cae bajo el umbral, fuerza DEFENSIVO
antes de que el precio lo refleje.

Fuente de titulares: Alpaca News API (alpaca-py NewsClient), gratuita para
cuentas paper/live. Si no hay conexión (p.ej. corriendo en el sandbox sin
salida a internet), degrada con gracia devolviendo score neutro.
"""

from dataclasses import dataclass
from typing import List

from config import SENTIMENT_DEFENSIVE_THRESHOLD, SENTIMENT_HEADLINE_LIMIT

try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)

    _ANALYZER = SentimentIntensityAnalyzer()
except Exception:
    _ANALYZER = None


@dataclass
class SentimentResult:
    score: float
    defensive: bool
    n_headlines: int
    detalle: str


def _score_headlines(headlines: List[str]) -> float:
    if not headlines or _ANALYZER is None:
        return 0.0
    scores = [_ANALYZER.polarity_scores(h)["compound"] for h in headlines]
    return sum(scores) / len(scores)


def analizar_sentimiento(symbol: str, headlines: List[str] = None) -> SentimentResult:
    """
    headlines: lista de titulares ya obtenidos (p.ej. de Alpaca News API).
    Se pasa explícito para que el módulo no dependa de la red al testear.
    """
    headlines = (headlines or [])[:SENTIMENT_HEADLINE_LIMIT]
    score = _score_headlines(headlines)
    defensive = score < SENTIMENT_DEFENSIVE_THRESHOLD

    detalle = (
        f"{len(headlines)} titulares analizados para {symbol}. "
        f"Score compuesto promedio VADER: {score:.3f}."
    )
    if defensive:
        detalle += " Por debajo del umbral defensivo -> gatillo de pánico activado."

    return SentimentResult(score=score, defensive=defensive, n_headlines=len(headlines), detalle=detalle)


def obtener_titulares_alpaca(symbol: str, api_key: str, secret_key: str, limit: int = 30) -> List[str]:
    """Trae titulares recientes desde Alpaca News API. Requiere red real (correr en tu PC)."""
    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest

    client = NewsClient(api_key, secret_key)
    req = NewsRequest(symbols=symbol, limit=limit)
    news = client.get_news(req)
    return [n.headline for n in news.data.get("news", news.data if isinstance(news.data, list) else [])] \
        if hasattr(news, "data") else [n.headline for n in news]
