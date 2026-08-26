Contexto para que te pongas al día — hoy hubo un incidente en paralelo con
otra sesión de Claude Code (la del proyecto "App Trading"/Caveman) que vos
no viste: confundió la cuenta del hackathon con la de otro bot mío
(`PA35I3LOIY7P`, un proyecto en pausa, no relacionado) y liquidó posiciones
ahí por error. Ya está resuelto y no te concierne — pero como consecuencia,
esa otra sesión también reinició `live_agent.py` más de una vez y limpió
`positions_state.json`. Necesito que verifiques el estado REAL actual antes
de seguir, no asumas nada de lo que vos mismo dejaste antes.

## Parte 1 — Sincronizar estado real

1. Confirmá qué proceso `live_agent.py` está corriendo ahora mismo (PID,
   hora de arranque) y con qué flags (`--use-cli`, sin `--dry-run`).
2. Leé `positions_state.json` tal cual está ahora y compará contra
   `GET /v2/account` + `GET /v2/positions` reales de `PA3EGUEP0QCV` —
   confirmá que coinciden (no debería haber ninguna posición fantasma).
3. Reportame qué encontraste, con números concretos (equity actual,
   posiciones abiertas y su vencimiento).

## Parte 2 — Estado de las dos tareas pendientes

Decime en qué quedaron estas dos, si las corriste y qué encontraste (si
no llegaste a correrlas, corrélas ahora):

1. `PROMPT_VALIDAR_DTE_CORTO.md` — validación del backtest de 3 años con
   DTE 7-14/buffer 2, el análisis de ventana de 7 días repetido con la
   calibración nueva, el sanity check de los strikes del Iron Condor para
   DTE corto, y la corrección del premio ($5,000 -> $6,000) en
   `MISSION_BRIEF.md`.
2. `PROMPT_INTEGRAR_MCP_SERVER.md` — instalación del MCP server oficial de
   Alpaca en modo solo-lectura, las 3 consultas de prueba, y la
   documentación en `README.md`/`writeup.md`.

Si alguna quedó a mitad de camino, terminala. Si hay algo bloqueado,
explicame qué y por qué en vez de saltarlo en silencio.

Repórtame todo junto al final — Parte 1 primero (para que sepa que
estamos mirando la misma realidad), después Parte 2.
