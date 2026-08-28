"""
Foto de las 5 posiciones reales abiertas al momento de migrar live_agent.py
de la PC de Diego a Railway (28-ago-2026, cuenta PA3SQTOC6A22).

SNAPSHOT_28AGO la importa live_agent.py (_sembrar_estado_inicial_si_corresponde)
para sembrar el volumen persistente en el primer arranque en Railway -- desde
DENTRO del proceso, después de que el volumen ya está montado. Un intento
anterior de sembrar esto vía preDeployCommand (fase previa al mount del
volumen) escribió al filesystem efímero del contenedor en vez del volumen,
y el agente arrancó sin ver las posiciones ya abiertas -> abrió duplicados
reales en SPY/AAPL/QQQ (incidente del 28-ago, remediado a mano).

Este módulo también se puede correr standalone (`python scripts/seed_state.py`)
para sembrar manualmente, pero ya no es necesario -- queda solo por si hace
falta re-sembrar algo a mano.
"""

import json
import os
from pathlib import Path

SNAPSHOT_28AGO = {
    "SPY": {
        "kind": "iron_condor",
        "option_symbols": [
            "SPY260904C00794000",
            "SPY260904C00810000",
            "SPY260904P00748000",
            "SPY260904P00733000",
        ],
        "precio_entrada_subyacente": 771.3,
        "expiry": "2026-09-04",
        "regimen": "RANGO_LATERAL",
        "opened_at": "2026-08-28T10:32:49",
        "credito_recibido": None,
    },
    "AAPL": {
        "kind": "iron_condor",
        "option_symbols": [
            "AAPL260904C00327500",
            "AAPL260904C00332500",
            "AAPL260904P00307500",
            "AAPL260904P00300000",
        ],
        "precio_entrada_subyacente": 317.02,
        "expiry": "2026-09-04",
        "regimen": "RANGO_LATERAL",
        "opened_at": "2026-08-28T10:32:53",
        "credito_recibido": None,
    },
    "QQQ": {
        "kind": "iron_condor",
        "option_symbols": [
            "QQQ260904C00742000",
            "QQQ260904C00756000",
            "QQQ260904P00699000",
            "QQQ260904P00684000",
        ],
        "precio_entrada_subyacente": 720.11,
        "expiry": "2026-09-04",
        "regimen": "RANGO_LATERAL",
        "opened_at": "2026-08-28T10:32:57",
        "credito_recibido": None,
    },
    "MSFT": {
        "kind": "direccional",
        "option_symbols": ["MSFT260904C00522500"],
        "precio_entrada_subyacente": 511.385,
        "expiry": "2026-09-04",
        "regimen": "TENDENCIAL_ALCISTA",
        "opened_at": "2026-08-28T10:32:59",
        "es_alcista": True,
    },
    "NVDA": {
        "kind": "iron_condor",
        "option_symbols": [
            "NVDA260904C00232500",
            "NVDA260904C00235000",
            "NVDA260904P00217500",
            "NVDA260904P00212500",
        ],
        "precio_entrada_subyacente": 224.76,
        "expiry": "2026-09-04",
        "regimen": "RANGO_LATERAL",
        "opened_at": "2026-08-28T10:33:03",
        "credito_recibido": None,
    },
}


def main() -> None:
    state_dir = Path(os.getenv("STATE_DIR", "."))
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "positions_state.json"
    if state_file.exists():
        print(f"[seed_state] {state_file} ya existe, no se pisa.")
        return
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(SNAPSHOT_28AGO, f, indent=2)
    print(f"[seed_state] Sembrado {state_file} con {len(SNAPSHOT_28AGO)} posiciones.")


if __name__ == "__main__":
    main()
