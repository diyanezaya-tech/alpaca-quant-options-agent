"""
Validación out-of-sample de TAKE_PROFIT_PCT / EXIT_DTE_BUFFER.

Parte el histórico de cada símbolo en una ventana de "entrenamiento" (donde
se hace grid search de parámetros) y una ventana de "prueba" (últimos 365
días, nunca vistos durante el ajuste). Corre los parámetros ganadores de
entrenamiento sobre la ventana de prueba para ver si la mejora sigue
sosteniéndose fuera de muestra.

Nota: sobre ~3 años de historial, la ventana de entrenamiento resultante es
de ~14 meses, no ~2 años -- calcular_indicadores() descarta las primeras
~215 filas por warm-up de rolling windows (Volatilidad=15, Vol_Promedio=200)
antes de que empiece la simulación.

Uso:
    python oos_validation.py
"""

import pandas as pd

from backtest import preparar_datos, simular_sobre_datos
from config import TAKE_PROFIT_PCT as TP_DEFAULT, EXIT_DTE_BUFFER as DTE_DEFAULT

SYMBOLS = ["SPY", "AAPL", "QQQ"]
TP_GRID = [0.04, 0.05, 0.06, 0.08, 0.10, 0.12]
DTE_GRID = [3, 5, 7, 10, 14]


def partir_train_test(datos_ind: pd.DataFrame, dias_test: int = 365):
    corte = datos_ind.index.max() - pd.Timedelta(days=dias_test)
    train = datos_ind[datos_ind.index < corte]
    test = datos_ind[datos_ind.index >= corte]
    return train, test


def grid_search(train: pd.DataFrame):
    mejor = None
    for tp in TP_GRID:
        for dte in DTE_GRID:
            r = simular_sobre_datos(train, take_profit_pct=tp, exit_dte_buffer=dte)
            if mejor is None or r["rendimiento_estrategia_pct"] > mejor["rendimiento_estrategia_pct"]:
                mejor = {"tp": tp, "dte": dte, **r}
    return mejor


def main():
    print(f"Default actual en config.py: TAKE_PROFIT_PCT={TP_DEFAULT}, EXIT_DTE_BUFFER={DTE_DEFAULT}\n")

    for symbol in SYMBOLS:
        print(f"=== {symbol} ===")
        datos_ind = preparar_datos(symbol, years=3)
        train, test = partir_train_test(datos_ind)
        print(f"  Train: {train.index.min().date()} -> {train.index.max().date()} ({len(train)} filas)")
        print(f"  Test:  {test.index.min().date()} -> {test.index.max().date()} ({len(test)} filas)")

        ganador = grid_search(train)
        print(f"  Ganador en TRAIN: TP={ganador['tp']} DTE={ganador['dte']} "
              f"-> estrategia={ganador['rendimiento_estrategia_pct']}% "
              f"(mercado={ganador['rendimiento_mercado_pct']}%, trades={ganador['n_trades']})")

        oos_ganador = simular_sobre_datos(test, take_profit_pct=ganador["tp"], exit_dte_buffer=ganador["dte"])
        print(f"  OOS con params ganadores en TEST: estrategia={oos_ganador['rendimiento_estrategia_pct']}% "
              f"(mercado={oos_ganador['rendimiento_mercado_pct']}%, trades={oos_ganador['n_trades']})")

        oos_default = simular_sobre_datos(test, take_profit_pct=TP_DEFAULT, exit_dte_buffer=DTE_DEFAULT)
        print(f"  OOS con default de config.py en TEST: estrategia={oos_default['rendimiento_estrategia_pct']}% "
              f"(mercado={oos_default['rendimiento_mercado_pct']}%, trades={oos_default['n_trades']})")
        print()


if __name__ == "__main__":
    main()
