Otra sesión de Claude (en la nube, trabajando sobre este mismo proyecto)
recalibró hoy `config.py` para que el DTE de las opciones encaje en la
ventana de 7 días corridos del concurso (28 ago-4 sept):

- `TARGET_DTE_MIN`: 21 -> 7
- `TARGET_DTE_MAX`: 45 -> 14
- `EXIT_DTE_BUFFER`: 10 -> 2 (si no, con DTE 7-14 casi toda posición nueva
  se cerraría por buffer a los 0-4 días de abierta, sin dejar margen a que
  actúe el stop loss / take-profit)

El archivo en disco ya tiene estos valores nuevos. El problema: el proceso
`python live_agent.py` que está corriendo ahora mismo arrancó ANTES de este
cambio (vía Programador de tareas de Windows, disparado "al iniciar el
equipo") y tiene `config.py` importado en memoria con los valores viejos
(21-45 / 10) desde que arrancó. El cambio en disco no aplica hasta que se
reinicie el proceso — Python no relee el módulo solo.

Instrucciones:

1. Verifica primero que `config.py` en disco realmente tiene
   `TARGET_DTE_MIN=7`, `TARGET_DTE_MAX=14`, `EXIT_DTE_BUFFER=2`. Si no los
   tiene, avísame y no sigas — no asumas.

2. Identifica el/los proceso(s) `python live_agent.py` corriendo ahora
   mismo (PID, hora de inicio aproximada por `live_agent.log`).

3. Detenlos de forma limpia (dale tiempo a terminar el ciclo en curso si
   está a mitad de un ciclo; si no responde, `taskkill`). Confirma que no
   quede NINGÚN proceso `live_agent.py` corriendo antes de arrancar uno
   nuevo — dos instancias en paralelo sobre la misma cuenta paper
   duplicarían órdenes.

4. Reinicia el loop en modo real (sin `--dry-run`) contra la cuenta paper
   del concurso (PA3EGUEP0QCV), de la misma forma en que estaba corriendo
   antes (revisa si la tarea del Programador de Windows necesita
   re-dispararse manualmente, o si alcanza con lanzarlo a mano ahora y
   dejar que la tarea existente lo tome en el próximo reinicio de Windows).

5. Confirma en `live_agent.log` que arrancó limpio: línea "Conectado a
   cuenta..." nueva, y al menos un ciclo completo sin errores para los 3
   símbolos (SPY, AAPL, QQQ).

6. NO toques las 3 posiciones abiertas (SPY Iron Condor, AAPL Long Put
   307.5, QQQ Long Call 725) — su cierre/reset antes del 28 ya está
   resuelto por otra tarea programada tuya, fuera de este prompt.

7. Repórtame: PID(s) viejo(s) detenido(s), PID nuevo, hora exacta del
   reinicio, y confirmación de que corrió al menos un ciclo sin error.
