# Continuación: reparación, aceptación y decisión numérica

Investigación independiente de la entrega OMS v1.3.5. Continúa el piloto de
generalización, sin modificar sus datos ni su diseño. Se estudian los otros
aspectos: reparación efectiva, costo del ciclo completo, diagnósticos previos y
garantías de aceptación verificable.

## Hipótesis

1. Fijar una asignación entera y resolver su LP puede recuperar precisión en puntos
   que fallan después de redondear, siempre que la asignación admita continuación
   factible. Si no, la respuesta correcta es un nuevo intento o abstención.
2. Una verificación racional puede separar el punto exacto reparado de su entrega
   en binary64. Se exige comprobar ambos; no se presupone que convertir un testigo
   racional a float conserva automáticamente los presupuestos.
3. La amplificación de coeficientes enteros puede orientar el costo de reparación,
   pero una condición suficiente incumplida no es un predictor de fallo. Se evalúa
   en semillas/modelos no usados durante la calibración, sin aprendizaje automático.
4. El presupuesto no valida optimalidad. Se conservan objetivo original, validez
   primal y comprobaciones independientes de cotas como estados separados.

## Desarrollo separado de confirmación

La calibración empieza con el punto Gurobi/Base del piloto en
`control30-3-2-3`, sin nuevas llamadas MILP. Se compara el LP con enteros fijados
en aritmética ordinaria y racional. Los intentos fallidos se conservan.
Esta fase orienta la implementación y queda fuera de la evaluación prospectiva.

El protocolo del seguimiento se cerrará antes de resolver: semillas nuevas,
modelos nuevos de la fuente independiente, controles de tolerancias/NumericFocus/
IntegralityFocus, límites iguales y tiempos completos de preparación, importación,
optimización, reparación y verificación. Toda abstención se contabiliza.

## Componente matemático a desarrollar

La aceptación tiene dos niveles explícitos: exacta para el testigo racional y
numérica en unidades originales para el punto binary64 entregado. La verificación
de todas las filas, cotas y dominios es la condición de aceptación. La corrección
de un entero fijo no prueba optimalidad MILP ni garantiza encontrar una reparación.
La fase exacta utiliza expansiones decimales completas de los datos binary64 y un
checker `Fraction` sobre las filas originales, fuera del solver.

Los antecedentes de reparación exacta y certificación están en
[Eifler y Gleixner (2021)](https://arxiv.org/abs/2101.09141),
[Cheung, Gleixner y Steffy](https://arxiv.org/abs/1611.08832) y la
[documentación de SoPlex](https://soplex.zib.de/doc/html/EXACT.php).
No se reivindica la idea general de verificar/reparar como una novedad. El posible
aporte es la especificación de precisión, decisión, entrega y costo comprobables.
