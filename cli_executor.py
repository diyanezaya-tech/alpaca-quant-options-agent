"""
Capa de ejecución vía el CLI oficial de Alpaca (github.com/alpacahq/cli),
complementaria a executor.py (que usa el SDK alpaca-py).

El hackathon pide explícitamente "Trading API, MCP server and CLI" como
infraestructura de Alpaca. alpaca-py se mantiene para todo lo que es datos
históricos, cadena de opciones y consultas de cuenta (options_selector.py,
backtest.py, live_agent.py sin --use-cli); este módulo es solo para la
EJECUCIÓN real de órdenes, invocando el binario `alpaca` por subprocess.

El binario no pide confirmación ("no confirmation prompts... every command
executes immediately" -- README oficial), así que el guardado de "no
mandar nada real sin dry_run=False explícito" lo hace este módulo, no el CLI.

Requiere el binario `alpaca` en PATH o en ./tools/alpaca.exe (Windows) --
ver README.md, sección "Alpaca CLI". Usa las mismas variables de entorno
que ya trae `.env` (ALPACA_API_KEY / ALPACA_SECRET_KEY): el CLI las lee
directo del proceso, sin necesitar login/perfil aparte. No se setea
ALPACA_LIVE_TRADE, así que el CLI opera en paper por default (confirmado
con `alpaca doctor` -> "active profile: paper").
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path

from options_selector import OptionStrategy, OptionLeg

logger = logging.getLogger("cli_executor")

_TOOLS_BINARY = Path(__file__).parent / "tools" / "alpaca.exe"


def _resolver_binario() -> str:
    """Prefiere un `alpaca` en PATH; si no está, usa el binario vendorizado en tools/."""
    en_path = shutil.which("alpaca")
    if en_path:
        return en_path
    if _TOOLS_BINARY.exists():
        return str(_TOOLS_BINARY)
    raise RuntimeError(
        "No se encontró el binario `alpaca` (ni en PATH ni en tools/alpaca.exe). "
        "Ver README.md, sección 'Alpaca CLI', para instalarlo."
    )


class CliOrderError(RuntimeError):
    """El CLI devolvió un error (exit code != 0) al intentar una orden."""


def _correr_cli(args: list) -> dict:
    """
    Corre el binario `alpaca` con los args dados, loggea el comando exacto y
    su salida cruda (evidencia de "agente autónomo operando por CLI"), y
    devuelve el JSON parseado de stdout.
    """
    binario = _resolver_binario()
    comando = [binario] + args
    logger.info(f"[CLI] $ {' '.join(comando)}")

    resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30)

    logger.info(f"[CLI] stdout: {resultado.stdout.strip()}")
    if resultado.stderr.strip():
        logger.info(f"[CLI] stderr: {resultado.stderr.strip()}")

    if resultado.returncode != 0:
        raise CliOrderError(
            f"`alpaca {' '.join(args)}` salió con código {resultado.returncode}: "
            f"{resultado.stderr.strip() or resultado.stdout.strip()}"
        )

    try:
        return json.loads(resultado.stdout)
    except json.JSONDecodeError as e:
        raise CliOrderError(f"Salida no-JSON de `alpaca {' '.join(args)}`: {e}") from e


def ejecutar_leg_cli(leg: OptionLeg, qty: int = 1, dry_run: bool = True) -> dict:
    """
    Envía (o previsualiza, si dry_run=True) una orden de mercado para una
    leg de opción vía `alpaca order submit`. dry_run=True por default:
    solo un caller que pase dry_run=False explícito manda una orden real.
    """
    args = [
        "order", "submit",
        "--symbol", leg.symbol,
        "--side", leg.side,
        "--qty", str(qty),
        "--type", "market",
        "--time-in-force", "day",
    ]
    if dry_run:
        args.append("--dry-run")
    return _correr_cli(args)


def ejecutar_estrategia_cli(estrategia: OptionStrategy, qty: int = 1, dry_run: bool = True) -> list:
    """
    Ejecuta todas las legs de una estrategia de opciones vía el CLI, en el
    mismo orden defensivo que executor.py: primero las COMPRADAS (cobertura),
    luego las VENDIDAS (crédito) -- mandar una leg vendida como orden de
    mercado individual antes de tener su cobertura en cuenta la deja
    "uncovered" y Alpaca la rechaza (confirmado en vivo, error 40310000).
    """
    resultados = []
    legs_ordenadas = sorted(estrategia.legs, key=lambda l: 0 if l.side == "buy" else 1)
    for leg in legs_ordenadas:
        resultado = ejecutar_leg_cli(leg, qty=qty, dry_run=dry_run)
        resultados.append(resultado)
    return resultados


def cerrar_posicion_cli(symbol: str, confirmar_real: bool = False) -> dict:
    """
    Cierra una posición vía `alpaca position close`.

    A diferencia de `order submit`, este subcomando NO tiene `--dry-run`
    (confirmado con `alpaca position close --help`) -- ejecuta de inmediato,
    sin previsualización posible a nivel CLI. Por eso no reusa el patrón
    `dry_run=True` por default de las demás funciones de este módulo, que
    daría una falsa sensación de que hay una previsualización cuando no la
    hay: hay que pasar `confirmar_real=True` explícito para que haga algo,
    y si no se pasa, esta función no llama al CLI en absoluto (falla clara
    en vez de ejecutar por accidente).
    """
    if not confirmar_real:
        raise RuntimeError(
            "cerrar_posicion_cli no tiene modo dry-run (el CLI no lo soporta para "
            "`position close`); pasa confirmar_real=True explícito para ejecutar de verdad."
        )
    args = ["position", "close", "--symbol-or-asset-id", symbol]
    return _correr_cli(args)
