# Qué garantiza el controlador de calidad y qué evidencia exige

Este documento formaliza propiedades de la implementación, no teoremas nuevos.
Presupuestos primales, calidad de objetivo e informes de optimalidad son estados
distintos. Los componentes tienen antecedentes en warm starts, verificación y
reparación exacta; la hipótesis empírica es su utilidad conjunta en el ciclo.

## Aceptación y retención

Sea V_delta(y) la verificación de todas las filas y cotas originales dentro de
sus presupuestos, con dominios enteros exactos. El conjunto S_k contiene los
candidatos disponibles que pasan V_delta tras k etapas. Cada etapa puede añadir
un candidato o no añadir ninguno; no elimina candidatos ya verificados.

Si S_k es no vacío, el controlador devuelve el elemento de menor costo original
c(y), calculado con aritmética racional sobre los valores binary64. Por inclusión
S_k en S_(k+1), min_(y en S_(k+1)) c(y) <= min_(y en S_k) c(y). Por construcción,
V_delta(y) se cumple para cualquier salida. Una fase robusta que falla, se queda
sin tiempo o devuelve un punto peor no hace perder el candidato anterior.

Esta propiedad no convierte un punto dentro de tolerancias numéricas en un
testigo factible exacto. Tampoco prueba progreso estricto, alcanzar un objetivo
deseado, superioridad sobre otro tratamiento o encontrar el óptimo global.
Todas esas son preguntas separadas.

## Veto de una cota mediante un testigo exacto

Para minimizar c^T x sobre el modelo original, si q satisface exactamente todas
las filas, cotas y dominios, entonces z* <= U=c^T q. Si B es una cota inferior
válida, necesariamente B <= z* <= U. Por lo tanto B>U contradice su validez.
La implementación usa una guarda max(1e-6,8 ulp(B)) para evitar controversias
del último dígito mostrado. El checker vuelve a verificar el vector q completo.

El modelo del testigo debe coincidir exactamente con el modelo certificado.
Factores positivos diádicos que escalan fila y RHS proporcionalmente conservan
ese modelo; una reformulación no cotejada o un cambio en dominio/objetivo no
permite reutilizar el certificado. Un hash semántico y el modelo canónico dejan
esta condición explícita.

No hallar B>U no prueba B válido. El testigo puede ser muy subóptimo o no existir.
El estado de optimalidad permanece no verificado en todos los casos. La comparación
solo puede descartar afirmaciones inconsistentes; no sustituye un certificado dual
de LP, branch-and-bound exacto o un certificado global de optimalidad MILP.

Un testigo racional puede justificar U aunque su conversión a binary64 no cumpla
los presupuestos de entrega. Para iniciar el solver o devolver un punto, esa
conversión debe verificar V_delta de nuevo. Los seis tests comprueban, entre
otras cosas, el ejemplo 3x=1 con presupuesto inferior a 2^-54 y el rechazo de
testigos de otro modelo o solamente factibles dentro de tolerancias.

## Disponibilidad y comparación justa

Una contradicción detectada con un testigo disponible antes de una fase es un
veto online. Usar el mejor testigo obtenido más tarde en otras ejecuciones es una
auditoría posterior. La implementación y los resultados mantienen ambas cuentas
separadas. Las cotas de una fase no se transfieren a un punto reparado como gap
certificado y la retención del mejor candidato no modifica los dominios MILP.

El control Witness-warm-tight usa información previa. Su objetivo sirve para
examinar aceptación del Start y efectos en cotas; su tiempo excluye obtener el
testigo y no se presenta como algoritmo nuevo más rápido. Los warm starts se
comparan contra controles en frío con igual suma máxima de límites MILP, y se
informan tiempos de exportación, importación, reparación, verificación y auditoría.
Para valorar una mejora del artículo hacen falta resultados de precisión y
calidad frente a esos controles, no solo una salida que pase el filtro.

Referencias primarias:

- [Gurobi, atributo Start](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html#attrstart).
- [Gurobi, IntegralityFocus](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameterintegralityfocus).
- [Eifler y Gleixner, reparación exacta y certificados MILP](https://arxiv.org/abs/2101.09141).
- [SoPlex, LP exacto y referencias](https://soplex.zib.de/doc/html/EXACT.php).
