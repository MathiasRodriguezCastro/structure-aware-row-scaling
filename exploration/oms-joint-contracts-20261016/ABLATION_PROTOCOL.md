# Ablación posterior al piloto: atribución, no validación independiente

El piloto conjunto de 18 llamadas terminó antes de fijar este seguimiento y
no mostró contradicciones de cotas/cierre detectadas. Para distinguir el efecto
del cambio de unidades del efecto de los contratos, se fija un cruce 2x2:
filas solamente / filas+columnas continuas, contratos activos / sin contratos.
Se mantiene la exactitud binary64, mismo objetivo entero de centrado, ventanas,
regla determinista de selección, seis casos, semillas 59,71,89, presolve auto y
todos los parámetros del piloto. Los contratos se evalúan siempre con .01 MW y
100 m3. Se reutilizan explícitamente las 18 llamadas Joint-contract ya realizadas.

Se congelan los 72 brazos antes del primer MILP adicional. Si dos políticas
producen exactamente la misma exportación por construcción, se declara el alias
antes de resolver y se ejecuta una vez esa representación por caso/semilla.
No se deduplica después de observar puntos. Todo costo de selección y las
llamadas prestadas se registran. No se escoge otro potencial ni otra ventana.

Los seis testigos exactos Base y su transformación verificable se reutilizan;
no se adquieren nuevos patrones ni se confunden LP fijados con cotas inferiores.
Este seguimiento puede atribuir un efecto a la representación contractual dentro
de los modelos conocidos; no demuestra validez externa ni novedad histórica.
