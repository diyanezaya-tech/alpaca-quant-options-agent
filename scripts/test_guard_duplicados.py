"""
Test aislado (sin red, sin tocar ninguna cuenta real) del guard agregado en
ciclo() (live_agent.py) contra duplicados: si el bróker ya tiene una
posición real para un símbolo que `estado` (positions_state.json local) no
conoce, no debe abrir una nueva.

Mockea descargar_datos_alpaca, obtener_titulares_alpaca y obtener_posiciones
-- cero llamadas HTTP. Corre con: python scripts/test_guard_duplicados.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
import live_agent  # noqa: E402


def _fake_datos(n=260):
    rng = np.random.default_rng(42)
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 400 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"Close": close}, index=idx)


def main():
    logs = []
    live_agent.log = lambda msg: logs.append(msg)

    live_agent.descargar_datos_alpaca = lambda data_client, symbol, dias=200: _fake_datos()
    live_agent.obtener_titulares_alpaca = lambda symbol, api_key, secret_key: []

    fake_pos = SimpleNamespace(symbol="MSFT260904C00515000")
    live_agent.obtener_posiciones = lambda client: [fake_pos]

    def _fail_si_se_llama(*args, **kwargs):
        raise AssertionError("construir_estrategia no debería llamarse: el guard debió cortar antes")
    live_agent.construir_estrategia = _fail_si_se_llama

    estado = {}  # sin registro local para MSFT -- el caso que debe frenar el guard
    live_agent.ciclo(client=object(), data_client=object(), symbol="MSFT",
                      estado=estado, dry_run=True, use_cli=False)

    esperado = "Ya hay posición real en el bróker para MSFT sin registro local"
    encontrado = any(esperado in m for m in logs)

    print("\n".join(logs))
    print()
    if encontrado:
        print("PASS: el guard frenó la apertura y logueó el mensaje esperado.")
        sys.exit(0)
    else:
        print("FAIL: no se encontró el mensaje esperado del guard.")
        sys.exit(1)


if __name__ == "__main__":
    main()
