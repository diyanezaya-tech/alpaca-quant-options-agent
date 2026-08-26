Requisito del hackathon (confirmado en la página oficial): construir
agentes usando "Alpaca's Trading API, MCP server and CLI". El proyecto ya
tiene el camino de ejecución vía CLI implementado y probado (`cli_executor.py`,
flag `--use-cli` en `live_agent.py`), pero **el loop que está corriendo
ahora mismo no lo está usando**: revisé `live_agent.log` y el reinicio de
hoy (13:36:37, PID 22720, tarea `AlpacaHackathonLiveAgent`) no tiene la
línea `*** MODO CLI ***` en el arranque — está ejecutando vía SDK
(`alpaca-py`) plano, no vía la CLI de Alpaca. Hay que corregir esto para
que la ejecución real (apertura y cierre de posiciones) pase por la CLI,
tal como se validó en `PROMPT_TEST_CLI_REAL.md`.

Instrucciones:

1. Confirma en `live_agent.log` que efectivamente el proceso actual (PID
   22720 u otro si ya cambió) arrancó sin `--use-cli` — busca si falta la
   línea `*** MODO CLI ***` en su bloque de arranque más reciente.

2. Revisa cómo está configurada la tarea `AlpacaHackathonLiveAgent` en el
   Programador de tareas de Windows (acción, programa, argumentos) y
   actualízala para que el argumento incluya `--use-cli` (además de lo que
   ya tenga: sin `--dry-run`, intervalo normal). Así sobrevive el próximo
   reinicio de Windows con la CLI activada, no solo este restart manual.

3. Detén el proceso actual de forma limpia (mismo cuidado que en
   `PROMPT_RESTART_LOOP_DTE.md`: esperar a que termine el ciclo en curso o
   `taskkill`, confirmar que no queda ninguna instancia viva antes de
   arrancar la próxima) y arráncalo de nuevo, esta vez con `--use-cli`.

4. Confirma en `live_agent.log` que el nuevo arranque sí muestra
   `*** MODO CLI: la ejecución real (apertura/cierre) va por el Alpaca CLI
   (subprocess), no por el SDK alpaca-py ***`, y que el ciclo corre sin
   errores para SPY/AAPL/QQQ.

5. La próxima vez que el agente abra o cierre una posición real (no ahora,
   cuando ocurra en un ciclo futuro), el log debe decir "vía Alpaca CLI" en
   vez de "vía SDK" en la línea "Ejecutando estrategia (...)" / al cerrar
   una leg. No podés forzar que abra/cierre ahora mismo solo para probarlo
   -- eso ya se validó por separado en `PROMPT_TEST_CLI_REAL.md`. Si querés
   una confirmación inmediata sin esperar, se puede on correr `live_agent.py
   --use-cli --dry-run --max-cycles 1` en paralelo (proceso aparte, no
   toca nada real) solo para loggear qué comando de CLI *hubiera* mandado;
   avísame si preferís eso.

6. NO toques `config.py` (ya está en 7-14/buffer 2, no lo vuelvas a tocar
   acá) ni las 3 posiciones abiertas.

7. Repórtame: cómo estaba configurada la tarea de Windows antes/después,
   PID viejo detenido, PID nuevo, y confirmación de la línea "MODO CLI" en
   el log del arranque nuevo.
