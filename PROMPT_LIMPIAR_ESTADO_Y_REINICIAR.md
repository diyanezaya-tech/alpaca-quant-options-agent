Contexto: hoy se cerraron a mano (por otra sesión de Claude Code, vía REST
directo contra Alpaca) las 3 posiciones reales que tenía el hackathon:
Iron Condor de SPY, call de QQQ, put de AAPL — todo en la cuenta paper
`PA3EGUEP0QCV`. Ese cierre NO pasó por `live_agent.py`, así que
`positions_state.json` (el archivo que el propio loop usa para saber qué
tiene abierto) quedó desactualizado: todavía dice que las 3 posiciones
siguen abiertas. Además el proceso `live_agent.py` está parado ahora mismo
(se interrumpió, no está corriendo).

Riesgo concreto si se reinicia el loop sin arreglar esto primero: como
`MAX_CONCURRENT_POSITIONS=3`, el bot va a pensar que tiene los 3 cupos
ocupados por esas posiciones fantasma y **no va a poder abrir ninguna
posición nueva en toda la semana del concurso**, sin ningún error visible
en el log — simplemente no va a operar.

Instrucciones — seguir el orden exacto, no saltear pasos:

1. Confirmá identidad de cuenta ANTES de cualquier otra cosa: consultá
   `GET /v2/account` (o el método equivalente del SDK/CLI que uses) y
   verificá que `account_number` sea exactamente `PA3EGUEP0QCV`. Si no
   coincide, parate y avisame — no sigas con los pasos siguientes.

2. Con la cuenta confirmada, traé las posiciones reales actuales
   (`GET /v2/positions` o `obtener_posiciones()` del SDK) y confirmá que
   la lista está vacía (`[]`). Si aparece CUALQUIER posición, no la toques
   todavía — decime cuál es antes de seguir, puede ser que el cierre de
   hoy no haya sido completo.

3. Solo si el paso 2 confirmó `[]`: abrí `positions_state.json` en
   `C:\Users\drpal\Downloads\alpaca-hackathon\` y reemplazá su contenido
   completo por `{}` (un objeto JSON vacío). No borres el archivo, dejalo
   existente con `{}` adentro.

4. Reiniciá `live_agent.py`:
   - Confirmá primero que no queda ningún proceso `live_agent.py` corriendo
     (buscá por PID, igual que en el reinicio anterior de hoy).
   - Arrancalo de nuevo en modo real, sin `--dry-run`, CON `--use-cli`
     (el modo CLI ya quedó validado hoy, no lo saques).
   - Si corre vía la tarea del Programador de Windows, dejá que la use esa
     configuración (ya tiene `--use-cli` desde el ajuste de hoy);
     si lo arrancás manual, agregá el flag vos.

5. Confirmá en `live_agent.log` (la línea nueva de arranque) que dice
   `Estado cargado de positions_state.json: posiciones abiertas en []`
   (vacío) — no `['SPY', 'AAPL', 'QQQ']`. Esperá a que corra al menos un
   ciclo completo para los 3 símbolos sin errores.

6. NO toques nada relacionado a Railway, al worker del bot diario, ni a la
   cuenta `PA35I3LOIY7P` en este prompt — eso quedó resuelto por separado.
   NO uses ningún comando de cierre "de todo" genérico en ningún paso de
   este prompt.

7. Repórtame: resultado exacto del paso 1 (account_number), resultado del
   paso 2 (lista de posiciones), confirmación de que `positions_state.json`
   quedó en `{}`, PID del proceso nuevo, y la línea del log que confirma
   estado vacío.
