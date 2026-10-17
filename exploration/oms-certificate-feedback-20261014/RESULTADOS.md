# Verificación exacta con realimentación: resultado de la prueba

Exploración independiente; OMS v1.3.5 permanece congelado. Fecha: 14/10/2026.

El experimento no encontró una mejora de C sobre B ni sobre el reinicio equivalente.
Se cierra este prototipo según el criterio fijado antes de resolver. El resultado
solo alcanza al caso, políticas, tres semillas y tres fases estudiados.

## Comparación completa

U es el costo de un testigo racional factible, con conversión binary64 comprobada.
Los costos múltiples siguen el orden de semillas 109,127,149. «--» significa que
la estrategia no obtuvo testigo; no es costo infinito ni certificado de inviabilidad
del MILP. Meta U <= 28129.51, basada en un costo factible previo 27851, no óptimo.

| Solver | Método | U | Meta exacta | Mediana de segundos completos |
|---|---|---|---|---|
| Gurobi | A-numeric | sin certificar | 0/3 | 0.242 |
| Gurobi | B-repair | 50001/53331/74091 | 0/3 | 1.359 |
| Gurobi | B-restart | 50001/53331/74091 | 0/3 | 2.923 |
| Gurobi | C-aggregate | 50001/53331/74091 | 0/3 | 4.208 |
| Gurobi | C-guard | 50001/53331/74091 | 0/3 | 4.145 |
| Gurobi | Base-B | 27851 | 3/3 | 1.732 |
| Gurobi | Base-tight-B | 27851 | 3/3 | 1.614 |
| HiGHS | A-numeric | sin certificar | 0/3 | 0.239 |
| HiGHS | B-repair | -- | 0/3 | 1.007 |
| HiGHS | B-restart | -- | 0/3 | 2.045 |
| HiGHS | C-aggregate | -- | 0/3 | 3.683 |
| HiGHS | C-guard | -- | 0/3 | 3.632 |
| HiGHS | Base-B | 27851 | 3/3 | 5.683 |
| HiGHS | Base-tight-B | 29651/29651/29311 | 0/3 | 31.319 |

A entrega cero nominal y alcanza la meta nominal en 6/6, pero su evaluación
posterior no respalda ese costo para ninguno de los seis patrones entregados.
La auditoría posterior de A no se carga como trabajo efectuado por A.
Base-B alcanza la meta exacta en 6/6. HiGHS Base-tight-B consume su límite y
no alcanza la meta: apretar tolerancias tampoco garantiza una mejora.

## Evidencia y límites

Son 42 resultados de estrategia, 60 llamadas MIP, 51 LP exactos y 9 accesos a
cache. Los LP producen 18 certificados de óptimo con testigo y 33 certificados
de inviabilidad. Se auditaron 44 patrones distintos, 30 inviables. Las 42
apariciones de patrones inviables en salidas nativas no son 42 patrones distintos.

Se probaron globalmente 24 cortes heredados antes de resolver y 24 nuevos
durante el ensayo; los heredados no se inyectaron en las estrategias. Los cortes
de costo parcial fijan 20 de las 3240 binarias. Los conflictos nuevos necesitan
entre 25 y 45 decisiones (los dos heredados, 26 y 28). Son regiones con una cota
inferior de continuación o una incompatibilidad; no dan el costo exacto de todos
los patrones de la región ni cubren todas las decisiones posibles.

En 36 observaciones de cortes activos, no hubo violaciones del corte exacto
tras redondear enteros, ni incumplimientos del residuo exportado o de gamma.
Ambas familias dejaron aparecer otros patrones inviables. La cota condicional
de la figura es suficiente y conservadora, no evidencia de un fallo observado.

Las 48 llamadas L2 con estado óptimo entregaron costo nominal cero. Seis
patrones tienen continuación exacta de costo positivo y las otras 42 apariciones
corresponden a patrones inviables. Esto no certifica la cota global ni refuta
independientemente 48 gaps: no aparecieron contradicciones de cota verificadas;
la optimalidad global sigue sin verificar.

## Cierre

No se modifica OMS ni se amplía esta campaña para buscar una ventaja.
NOTA_PREVENTIVA.md separa la existencia matemática de presupuestos uniformes
de su cálculo útil: exige familias completas de duales y rayos, ausentes aquí.
QUE_SIGUE.md deja una propuesta delimitada para estudiar un maestro Benders
real del despacho. Ninguna de esas notas demuestra novedad o superioridad.

Reproducción: README.md y VALIDATION.json. El paquete contiene protocolo,
código congelado, datos, logs, testigos y un replay sin llamadas a solvers.
