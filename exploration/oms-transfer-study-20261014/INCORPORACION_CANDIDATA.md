# Candidato breve, fuera del paper

La aportación útil es una comprobación de alcance de la garantía primal y una
precaución para el software que compara costos. No justifica una tercera
contribución, un nuevo teorema o una afirmación de superioridad general.
El envío OMS v1.3.5 permanece sin cambios.

Si se revisa el manuscrito, este párrafo sería suficiente en la discusión de
limitaciones, con la tabla y los certificados en material suplementario:

> Meeting an original-unit primal residual budget does not by itself certify
> the objective attainable with the returned integer assignment. In a separate
> post-observation audit of all 16 assignments from a two-solver experiment on
> neos-3083784-nive, four budget-compliant zero-cost Gurobi outputs had exact
> fixed-integer LP optima of 59,631 or 37,251; four zero-cost HiGHS assignments
> had independently verified fixed-pattern infeasibility certificates. These
> findings use experimental RHS-relative budgets, including allowances of up to
> 10^6 for big-M rows, and do not contradict the primal contracts. They motivate
> application-based budgets and separate reporting of numerical objective values
> and exactly feasible costs. The certificates concern fixed integer assignments
> and make no global MILP optimality or infeasibility claim.

Los recuentos corresponden a salidas, no a patrones enteros únicos: L2 y Budget
duplican patrones en nive. No se interpretan como cuatro casos independientes.

No se atribuye este fenómeno a un cambio contractual: en nive, L2 y Budget
son exactamente el mismo archivo. Tampoco hay error en la evaluación de c^T x;
el problema es interpretar ese costo como realizable con los mismos enteros.

La cota ponderada Delta_z procede de dualidad débil conocida. Sirve como
diagnóstico computable de la posible subestimación con presupuestos dados,
pero aquí es demasiado grande para proteger el costo. No añadiría su fórmula
como otro resultado teórico del artículo. Los certificados positivos y de
inviabilidad, los resultados negativos y los tiempos están en el artefacto.

La extensión a otro grupo muestra beneficio sobre L2 en Gurobi, mientras
Base/IntegralityFocus y tolerancias estrictas siguen siendo competitivos.
HiGHS no muestra la misma ventaja de aceptación. Eso limita el alcance de
cualquier afirmación de efectividad y se mantiene explícito.
