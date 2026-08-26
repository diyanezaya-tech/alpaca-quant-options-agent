Se acaba de agregar gestión de salida de posiciones a `live_agent.py` (antes el
loop solo abría posiciones y nunca las cerraba) y se recalibró el DTE objetivo
de 21-45 a 7-14 días. Necesito verificar esto contra la API real de Alpaca
antes de arrancar el loop en vivo para la semana del concurso (28 ago-4 sept).

`smoke_test.py` ya corrió sin red y confirmó que `evaluar_stop_loss`,
`evaluar_take_profit`, `evaluar_buffer_dte` y `position_state.py` funcionan
como funciones aisladas. Lo que falta verificar es la integración real:
la cadena de opciones filtrada por DTE y el cierre efectivo de posiciones
contra la cuenta paper (PA3EGUEP0QCV).

Instrucciones:

1. Verifica que el mercado esté abierto antes de mandar nada.

2. **Cadena de opciones filtrada por DTE**: usando el cliente de Alpaca ya
   configurado (mismas credenciales de `.env`), llama a
   `options_selector.obtener_cadena_opciones()` para SPY con `ContractType.CALL`
   y confirma que TODOS los contratos devueltos vencen entre 7 y 14 días desde
   hoy (`TARGET_DTE_MIN`/`TARGET_DTE_MAX` de `config.py`). Si la cadena viene
   vacía, prueba con AAPL o QQQ — puede ser que SPY no tenga vencimientos
   semanales en ese rango exacto ese día; documenta cuál símbolo sí tuvo
   contratos disponibles.

3. **Ciclo completo con posición real de prueba**: corre manualmente UN ciclo
   de `live_agent.ciclo()` (o el equivalente paso a paso) para un símbolo con
   cadena disponible, dejando que abra una posición real (paper) si el régimen
   lo permite. Confirma que:
   - Se ejecuta la orden (igual que en pruebas anteriores).
   - Se crea/actualiza `positions_state.json` con el símbolo, precio de
     entrada del subyacente, vencimiento y tipo correctos.

4. **Forzar y verificar el cierre**: sin esperar a que el mercado se mueva un
   3% de verdad, simula un gatillo de salida de la forma más simple posible —
   por ejemplo, edita temporalmente `positions_state.json` para que el
   `precio_entrada_subyacente` de la posición recién abierta implique un
   stop loss ya activado (o que `expiry` quede a ≤2 días), y corre otro ciclo.
   Confirma que:
   - `cerrar_posicion()` se llama y Alpaca acepta la orden de cierre.
   - La posición desaparece de `obtener_posiciones(client)`.
   - `positions_state.json` se limpia para ese símbolo (`position_state.limpiar`).
   Después de la prueba, restaura o borra `positions_state.json` para que no
   quede un registro falso antes del 28.

5. No dejes el loop (`while True` de `live_agent.main()`) corriendo en
   background al terminar — esto es una prueba puntual, no el arranque
   oficial. El arranque real del loop para el concurso es un paso aparte.

6. Repórtame: si la cadena vino filtrada correctamente por DTE, si la
   apertura registró bien el estado, si el cierre forzado funcionó de punta a
   punta (orden enviada + estado limpiado), y cualquier error o comportamiento
   inesperado con números/logs concretos — no solo "funcionó".
