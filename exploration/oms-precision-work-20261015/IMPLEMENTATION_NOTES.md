# Registro de implementación

Los seis tests de aritmética, contratos, GCD y LP racional pasaron antes del
primer MILP. No se cambió el código congelado del constructor/runner durante
las corridas. Todos los productos de exportación se comprobaron antes.

El checker independiente detectó que Base.lp declara 1e20 como cota superior
de `costoFalla`, mientras la API lo devuelve infinito. Se incorporó al parser
la semántica oficial: UB>=1e20 y LB<=-1e20 son infinitos. Se comprueban además
las cotas literales finitas sobre todos los puntos y testigos, de modo que esa
normalización no oculta una violación. No cambian datos canónicos ni resultados.
Referencia: https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html

El trabajo de primera llegada se obtiene de callbacks ya archivados. No se
modificó la búsqueda ni se terminaron corridas con el checker. Los tiempos de
selección y construcción son realmente medidos por brazo; runtime y costo de
captura proceden del optimizador. La suma de selección+construcción+runtime de
primera llegada es un prefijo observado, no un ciclo online completo: excluye
lectura previa, verificación, persistencia y certificados posteriores. Los CSV
lo etiquetan `measured_prefix_seconds`; no se reclama como tiempo end-to-end.

La compilación del acumulador exacto por modelo y la preparación documental no
se incluyen en el tiempo de verificación por candidato. La adquisición de cada
patrón racional sí registra construcción, resolución, comprobación y persistencia.
Son costos posteriores separados del eje de trabajo nativo de las figuras.
