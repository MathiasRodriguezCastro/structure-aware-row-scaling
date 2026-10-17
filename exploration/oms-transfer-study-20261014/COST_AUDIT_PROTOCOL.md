# Auditoría posterior del costo de una asignación entera

Motivación observada durante el seguimiento: en nive, algunas entregas satisfacen
los presupuestos y reportan costo cero, mientras un LP exacto con los mismos
enteros encuentra un costo positivo. Una solución exacta positiva sola no prueba
que cero sea imposible: falta una cota inferior válida para ese patrón entero.

Antes de llamadas adicionales se fija una auditoría de **las 16 asignaciones de
nive**, todos los tratamientos y ambas semillas. No se seleccionan solo ceros.
Se usan las entregas ya almacenadas; no se vuelve a resolver ningún MILP, cambiar
un factor o elegir otro patrón. No es un endpoint prospectivo del estudio de 80.

Para cada entrega, un LP SoPlex exacto con sus enteros fijados, límite 2 s,
exportación decimal completa y salida racional primal y dual (-X/-Y). Se guardan
los intentos sin testigo o sin certificado. Costos/timing de esta auditoría se
informan aparte y no se atribuyen al algoritmo evaluado anteriormente.

Un checker independiente verifica primal exacto y multiplicadores duales: signo
según cada sentido, costos reducidos y soporte de las cotas originales. Obtiene
L_z, cota inferior del LP con ese patrón z. Si un primal exacto q alcanza L_z,
se certifica su óptimo **con z fijado**, no el óptimo ni una cota inferior global
MILP. Contradicciones constantes prueban ausencia de continuación exacta de ese
patrón, no inviabilidad global del problema.

Para una entrega y dentro de los presupuestos de fila delta_r y cotas beta_j,
la misma dualidad da c(y) >= L_z - sum_r |pi_r| delta_r
- sum_continuas |rc_j| beta_j. Se comprueba exactamente esa desigualdad.
Cuantifica cuánto puede subestimar el costo un punto aproximadamente factible;
no acota el exceso de costo ni certifica el gap global. Es dualidad débil
elemental, no un teorema nuevo reclamado. El posible resultado es diagnóstico
de software y trazabilidad entre precisión primal y valor económico informado.
