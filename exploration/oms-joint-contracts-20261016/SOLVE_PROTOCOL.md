# Seguimiento de utilidad: fijado antes de resolver la regla conjunta

16-10-2026. El diagnóstico ya mostró t=8 frente a t=17 en los cinco primeros
modelos con 100 m3. Esto habilita únicamente un piloto de utilidad, no una
afirmación de ventaja. Se fija ahora la extensión ANTES del primer MILP conjunto:

- Los seis casos completos, sin selección posterior.
- Presolve automático y semillas 59,71,89: 18 asignaciones conjuntas.
- Factores del potencial determinista devuelto por el algoritmo en su menor t;
  no se escoge otro potencial para mejorar resultados.
- 0.01 MW/100 m3, gamma=1e-9, epsilon=1e-6; exactitud de matriz, RHS, costos y
  cotas. Mismo solver/Threads/TimeLimit/MIPGap/ScaleFlag/IF que frontier.
- Los controles son las asignaciones auto emparejadas ya fijadas en frontier:
  L2, Budget-L2/100, L2-tight, L2-NF3. No se usan controles escogidos a posteriori.
- x=2^v y se calcula exactamente como racional para auditar, y por ldexp para
  la salida binary64; se verifican ambas y se distingue su redondeo adicional.
- Un testigo exacto del Base se obtiene con el patrón ya elegido antes de estas
  campañas; se transforma y se comprueba contra la exportación exacta conjunta.
  Si falla esa adquisición, las contradicciones quedan desconocidas.
- Se conservan límites, fallos y puntos sin filtrar. El LP fijado es una cota
  primal condicional al patrón, nunca una cota inferior global.

El piloto solo justifica ampliación si aparece una mejora primal o de calidad
frente a controles fuertes en varios modelos. Mejor centrar coeficientes no basta.
Menor tiempo con cierre/cotas refutadas tampoco es una mejora de resolución.
No se incorporan resultados al manuscrito antes de la comprobación independiente.
