# Optimización del evaluador, sin nuevos MIP

La campaña utiliza el evaluador exhaustivo congelado. Después de ella se mide,
en procesos nuevos, una implementación que ordena los mismos candidatos con la
misma puntuación y se detiene en el primer certificado. No se cambian la lista,
los presupuestos, las reservas, los límites de coeficientes ni el desempate.

Se evalúan las seis instancias y los cuatro contratos del experimento II. Cada
exporte completo debe coincidir por SHA-256 con los modelos realmente resueltos.
Si cambia cualquier factor, no se atribuyen a esa variante las soluciones
anteriores. Se reportan únicamente tiempos de selección, pruebas de identidad
y costos medidos del algoritmo original. No se reconstruye una aceleración
del proceso completo sumando tiempos de campañas distintas.
