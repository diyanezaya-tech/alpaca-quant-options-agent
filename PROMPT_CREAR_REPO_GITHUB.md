Contexto: el proyecto no tiene todavía repositorio git ni está en GitHub.
El hackathon probablemente pide un link de repo para el submission — hay
que crearlo ahora, con cuidado de no subir el `.env` (tiene las API keys
reales de Alpaca, aunque sea cuenta paper, no deben quedar públicas).

No requiere confirmación previa salvo donde se indica abajo explícitamente
(esto es solo git/GitHub, no toca `live_agent.py` ni la cuenta paper).

## Paso 1 — Gitignore antes que nada

Creá `.gitignore` en `C:\Users\drpal\Downloads\alpaca-hackathon\` con al
menos:
```
.env
__pycache__/
*.pyc
venv/
*.log
positions_state.json
```
(`positions_state.json` cambia constantemente con el loop en vivo —
no aporta valor versionado y generaría commits de ruido todo el concurso;
`live_agent.log`/`bootstrap_stdout.log` quedan afuera también por lo mismo,
ya cubiertos por `*.log`.)

## Paso 2 — Verificar autenticación de GitHub

Corré `gh auth status`. Si no está autenticado, **parate y avisame** — no
soy yo quien tiene que loguearse, y no quiero que uses ninguna credencial
mía ni intentes autenticar por tu cuenta. Si ya está autenticado, seguí.

## Paso 3 — Inicializar y primer commit

```
git init
git add .
git status
```
Antes de comitear: revisá el output de `git status` y confirmá que `.env`
y `positions_state.json` NO aparecen listados para commitear (el
`.gitignore` los debe excluir). Si aparecen, no sigas — avisame.

Si está limpio:
```
git commit -m "Initial commit: Agente Cuántico de Opciones - Alpaca AI Trading Agents Hackathon"
```

## Paso 4 — Crear el repo en GitHub y pushear

Repo público (el hackathon necesita poder verlo), nombre sugerido
`alpaca-quant-options-agent` (cambialo si preferís otro):
```
gh repo create alpaca-quant-options-agent --public --source=. --remote=origin --push
```

## Paso 5 — Verificación de seguridad post-push

Confirmá con `git ls-files` (o revisando el repo en GitHub) que `.env` NO
está en el repo. Si por error quedó en el historial de commits (aunque
después lo borres del working tree, el commit viejo lo conserva), avisame
inmediatamente — las API keys quedarían expuestas en el historial público
y habría que rotarlas en el dashboard de Alpaca antes de seguir.

## Reporte

URL del repo en GitHub, confirmación de que `.env` no quedó expuesto (ni
en el working tree ni en el historial de commits), y el nombre final que
usaste si cambiaste el sugerido.
