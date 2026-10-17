# ¿Puede cerrarse una garantía global con el LP exacto?

Seis modelos Base conocidos 001,005,022,027,031,046, 16-10-2026. Se RELAJAN
todas las 1440 binarias conservando sus cotas [0,1]; no se fija ningún patrón.
Todos los coeficientes, RHS, costos y cotas son los racionales exactos de los
binary64 originales. Se exportan en decimales exactos sin notación exponencial.

Una llamada SoPlex exacta por modelo, límite 30 s y guarda externa 35 s. Todos
los resultados, incluidos desconocidos, se conservan. No se cambia el modelo
para conseguir un certificado. Se comprueban racionalmente los signos duales,
la identidad A^T*pi=c, el objetivo dual y la factibilidad primal LP. Solo un
dual verificado da una cota inferior global MILP; el primal LP fraccionario
no da una cota superior MILP. Los seis testigos enteros Base ya adquiridos dan U.

Se informa [LB_LP,U], y (U-LB_LP)/|U| si U>0, nunca un óptimo MILP supuesto.
Se evalúa si el intervalo basta para una garantía de 1 %. Una brecha grande
cierra esta vía sin estudiar cortes, DW ni formulaciones nuevas en este trabajo.

Es una prueba para la línea de verificación propuesta por Mathias, posterior
al piloto conjunto. No se reivindica la técnica clásica de dualidad LP como
novedad ni se usa un LP fijado para emitir una cota inferior global.
