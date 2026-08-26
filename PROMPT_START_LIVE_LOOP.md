Autorizado: arranca `live_agent.py` en loop real (SIN `--dry-run`) contra la
cuenta paper del concurso (PA3EGUEP0QCV), en modo de observación temprana
antes de que el hackathon empiece oficialmente el 28 de agosto. El objetivo
es detectar cualquier problema de estabilidad/lógica con un par de días de
margen, no que estas operaciones cuenten para el resultado oficial (que
solo se mide durante la semana 28 ago–4 sept).

Instrucciones:
1. Revisa una vez más `config.py` (universo de símbolos, intervalos, risk
   gates) y confirma que todo está en los valores que ya validamos
   (take-profit 5%, stop loss 3% sobre subyacente, buffer de salida por
   DTE, máx. 2% de riesgo por operación, máx. 3 posiciones concurrentes).
2. Arranca el loop con un intervalo razonable (el que ya está configurado,
   ~15 min, está bien — no lo aceleres).
3. Corre en background de forma que sobreviva si cierro la terminal
   (usa lo que ya dejaste documentado en el README sobre Programador de
   Tareas de Windows, o si es más simple ahora mismo, un proceso en
   background con `Start-Process` — lo que prefieras, pero que quede
   corriendo sin que yo tenga que mantener la ventana abierta).
4. Confírmame que arrancó correctamente (primer ciclo evaluado, log
   inicial) y avísame cómo revisar el archivo de log para hacer seguimiento
   sin tener que preguntarte a cada rato.
5. El 28 de agosto reviso contigo si seguimos con el mismo estado/posiciones
   que traiga acumuladas desde ahora, o si conviene resetear a limpio para
   que el resultado que se juzga sea el de la semana oficial únicamente
   (avísame si tiene sentido tomar nota de esto en algún lado para no
   olvidarlo).
