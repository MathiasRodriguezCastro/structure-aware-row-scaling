# Presupuestos selectivos, extensión posterior explícita

Se observa que la protección uniforme al 1 % usa los mismos factores diádicos
que la cota dual fija. Se evalúa ahora una asignación selectiva que no reduce
presupuestos sin contribución a ese certificado. Es una extensión posterior,
no una hipótesis prospectiva del estudio inicial ni nueva evidencia de familias.

Se incluyen los diez patrones factibles de nive de safe-design.json, sin
seleccionar los favorables. Para cada uno se mantiene el factor diádico ya
certificado. Se reducen por ese factor solo los presupuestos de filas originales
que aparecen con un multiplicador no nulo en el dual de v(0), y las cotas
continuas finitas con multiplicador no nulo. La igualdad usa un presupuesto
común para sus dos lados. Las otras precisiones permanecen como fueron definidas.

Se conservan todos los coeficientes, costos, RHS, cotas y dominios originales;
solo cambia la definición de la región de aceptación numérica. No se vuelve
a resolver ningún MILP. Para cada nuevo LP ampliado se verifica un primal/dual
exacto con el mismo límite 2 s/watchdog 4 s. Los presupuestos son diádicos y
se exportan sin redondeo adicional.

La misma dualidad proporciona v(0)-c(y)<=factor*Delta<=epsilon para los puntos
con esos enteros que cumplen estos presupuestos. Es una garantía condicional
al patrón y su certificado. No asegura factibilidad de otros patrones ni
confiabilidad de cotas globales. Se cuantifican presupuestos cambiados y factores
contractuales admisibles con la ventana y epsilon exportado originales.

No se promete ventaja computacional frente a reparar exactamente. El resultado
es una asignación de precisiones comprobable; eficiencia y generalización a
enteros no auditados requieren un experimento diferente.
