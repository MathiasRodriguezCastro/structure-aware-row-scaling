# Selector C++ integrado: prueba de oportunidad

16-10-2026. Implementación aislada; no se toca el generador original ni su binario.
Se copia el código fuente y se añade un hook después de construir/diagnosticar el
modelo y antes de exportar. Todas las decisiones se obtienen antes de modificar
filas. RHS y coeficientes se escalan juntos; variables/objetivo/dominios no cambian.
La implementación usa racionales multiprecisión para reservas y extremos.

Se compara el mismo generador compilado -O2 con el hook desactivado + selector
Python, y con hook integrado. Seis modelos conocidos, L2 y Budget-L2, 0.01 MW y
100 m3, gamma=1e-9. Siete repeticiones por combinación, orden fijo aleatorio
2026101602. Arranque, generación, lectura, selección y exportación se incluyen
en el tiempo de preparación. Se separa el tiempo interno C++ del ciclo fresco.

Primero se comprueba igualdad binary64 de TODOS los coeficientes, RHS, objetivo,
cotas y dominios respecto a Python. Si difieren, no se reutiliza ningún resultado
MILP anterior para atribuir una aceleración del ciclo de resolución.
Solo se anuncia menor costo de preparación si se mide. El costo de comprobar
la igualdad de las implementaciones se mide separado, pues es validación del
experimento y no parte necesaria de una exportación de usuario.

Una ventaja de software no prueba una nueva ventaja primal, de cotas o de solver.
Los resultados quedan como nota; no se amplía el paper por la implementación sola.
