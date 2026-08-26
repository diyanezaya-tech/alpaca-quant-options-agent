Hoy arranca oficialmente el hackathon (28 de agosto). Necesito que el
track record de P&L que se juzgue empiece limpio, exactamente desde hoy —
sin mezclar los días de prueba/observación previos.

Instrucciones:
1. Antes de que abra el mercado (09:30 ET), revisa qué posiciones están
   abiertas ahora mismo en la cuenta paper (PA3EGUEP0QCV).
2. Cierra TODAS las posiciones abiertas (avísame el P&L acumulado de estos
   días de prueba antes de cerrarlas, para que quede documentado aparte —
   no lo necesitamos para el concurso, pero es bueno tenerlo).
3. Verifica si Alpaca permite resetear/reiniciar el historial de la cuenta
   paper a un estado limpio (equity de vuelta a $100,000 exactos, sin
   historial de órdenes previo). Si no es posible vía API/CLI, dime cómo se
   haría desde el dashboard web y qué implica (por ejemplo, si hay que
   crear una nueva cuenta paper — en ese caso avísame antes de hacer nada,
   porque implicaría generar nuevas API keys y actualizar el .env).
4. Si no se puede resetear el historial pero sí el balance, al menos deja
   documentado en README.md/writeup.md la fecha y hora exacta en que
   arrancó el track record oficial (28 ago), y el equity de referencia en
   ese momento, para que quede clara la ventana que corresponde juzgar.
5. Una vez limpio (o documentado), reinicia el loop en vivo (la tarea
   programada `AlpacaHackathonLiveAgent`) para que arranque de nuevo desde
   cero sobre la ventana oficial del concurso.
6. Confírmame cuando esté listo y cuál fue el enfoque que terminaste
   usando (reset real vs. solo documentar el corte).
