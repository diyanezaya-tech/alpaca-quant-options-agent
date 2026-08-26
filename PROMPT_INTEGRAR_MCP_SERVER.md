El requisito del hackathon dice textualmente: "Build AI trading agents on
Alpaca — autonomous agents and trading apps using Alpaca's **Trading API,
MCP server and CLI**" (confirmado ahora en la página oficial de lablab.ai,
captura de Diego). Hoy tenemos Trading API (SDK `alpaca-py`, el motor
principal) y CLI (`cli_executor.py`, activado con `--use-cli`) — pero el
**MCP server de Alpaca nunca se integró**. `writeup.md` cita esa misma
frase del requisito como si estuviera cumplida y no lo está — hay que
corregir eso también.

Investigué: existe el MCP server oficial de Alpaca
(https://github.com/alpacahq/alpaca-mcp-server), soporta opciones
completo (cadenas, griegos, IV, spreads multi-leg), y tiene soporte nativo
para Claude Code vía:

```
claude mcp add alpaca --scope user --transport stdio uvx alpaca-mcp-server \
  --env ALPACA_API_KEY=<key de .env> \
  --env ALPACA_SECRET_KEY=<secret de .env> \
  --env ALPACA_PAPER_TRADE=true
```

(usa `uvx`, no requiere instalación manual del paquete)

## Objetivo

Integrarlo de forma que agregue valor real para la demo/writeup del
hackathon (no solo "está instalado pero nadie lo usa" — eso no demuestra
nada a los jueces), y SIN crear un segundo camino de ejecución de órdenes
que pueda pisar al loop autónomo (`live_agent.py`) que ya opera la cuenta.

Instrucciones:

1. Instala y configura el servidor con el comando de arriba, usando las
   credenciales de `.env` (misma cuenta paper `PA3EGUEP0QCV`). Verifica la
   conexión con `/mcp` en Claude Code.

2. **Importante — evitar doble ejecución**: revisa qué `ALPACA_TOOLSETS`
   expone el servidor por defecto y filtra explícitamente a herramientas
   de SOLO LECTURA para esta integración (cuenta, posiciones, datos de
   mercado, opciones/griegos, noticias) — sin las de colocar/cancelar
   órdenes. El único camino de ejecución de órdenes reales debe seguir
   siendo `live_agent.py` (vía SDK o CLI); el MCP server es una capa de
   consulta/monitoreo conversacional, no un segundo trader operando la
   misma cuenta sin coordinación. Si no se puede filtrar de forma
   confiable a solo-lectura, dejalo con todo pero documenta bien claro en
   el README que las herramientas de trading del MCP no deben usarse
   mientras el loop esté corriendo, y avisame antes de decidir cuál
   camino tomar.

3. Pruébalo con un par de consultas reales de solo lectura contra la
   cuenta paper (equity actual, las 3 posiciones abiertas y su P&L,
   cadena de opciones de SPY a 7-14 DTE) y pega la interacción real
   (pregunta + respuesta del MCP) como evidencia de que funciona.

4. Documenta en `README.md` y `writeup.md` esta pieza: qué es, cómo se
   configura, y qué rol cumple (capa conversacional de monitoreo/consulta
   sobre Trading API + CLI, que ya cubren la ejecución) — reemplazando la
   cita del requisito que hoy está sin respaldo real por una descripción
   honesta de las 3 piezas (API, CLI, MCP) y para qué se usa cada una.

5. No toques `config.py`, no abras/cierres posiciones a través del MCP
   server, no reinicies `live_agent.py` en este prompt (eso lo cubren los
   otros prompts que ya te pasé).

6. Repórtame: si la instalación/conexión funcionó, la interacción de
   prueba con resultados reales, y qué decisión tomaste sobre el filtro
   de solo-lectura.
