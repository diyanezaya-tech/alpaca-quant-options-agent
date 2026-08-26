Autorizado: ejecuta UNA sola orden real de prueba (paper, cuenta
PA3EGUEP0QCV) usando el camino `--use-cli` (Alpaca CLI real, no el SDK
alpaca-py) para verificar que esa ruta de ejecución funciona de punta a
punta contra la cuenta real.

Instrucciones:
1. Verifica que el mercado esté abierto antes de mandar nada (igual que la
   vez anterior con el SDK).
2. Elige la operación más simple y de menor riesgo posible para esta
   prueba (por ejemplo una sola leg, no un Iron Condor completo de 4 legs
   — no necesitamos repetir esa complejidad, solo confirmar que
   `cli_executor.py` manda la orden, Alpaca la acepta, y el parseo del
   JSON de respuesta es correcto).
3. Usa `--use-cli` explícitamente. Documenta el comando exacto que se
   ejecutó y el JSON crudo de respuesta.
4. Verifica que la orden aparece reflejada correctamente en
   `positions_state.json` (o donde corresponda) igual que las órdenes
   hechas por el camino SDK.
5. Cierra la posición de prueba después de verificar (no la dejes abierta
   sin necesidad, para no acumular posiciones de prueba innecesarias) a
   menos que prefieras dejarla y avisarme por qué.
6. No dejes ningún loop ni proceso corriendo en background al terminar.
7. Repórtame: comando ejecutado, resultado, y si el parseo/la integración
   funcionó igual de bien que con el SDK.
