# Protocolo de continuación — 14 de octubre de 2026

Se sigue la instrucción del autor de investigar las notas y añadir únicamente
resultados que fortalezcan el objetivo del paper sin una ampliación pesada.
Las versiones congeladas existentes se conservan. No se promete hallar una ventaja.

La primera hipótesis es que una fila de activación de volumen puede incumplir una
precisión declarada al convertir la binaria a un estado exacto, aunque los balances
de agua pasen su verificación. La segunda es que seleccionar factores admisibles
puede cambiar una decisión numérica útil frente a normalizar una norma de filas y
ajustar globalmente las tolerancias. Se conserva evidencia negativa y se distingue
siempre precisión primal de validez de cotas de optimalidad.

## Diseño ejecutado

1. Auditoría exacta de las 132 soluciones y los 30 modelos ya archivados, incluyendo
   las 66 observaciones con filas de activación. Se separan residuos positivos
   diminutos de aumentos materiales por redondeo. No hay resolución nueva en esta etapa.
2. Piloto separado en `instance046`, semilla 17, ocho políticas y límite 60 s. El
   piloto orienta los controles y queda excluido de los resultados de confirmación.
3. Confirmación en los seis escenarios SG-Ter-Mer del banco sin inversión de demanda:
   `instance001`, `instance005`, `instance022`, `instance027`, `instance031`,
   `instance046`. Semillas 1, 7 y 42; 120 s, cuatro hilos, brecha relativa 1 %;
   parámetros de escalado interno y presolve automáticos. Las cuatro políticas son
   GM, L2 con ventana de coeficientes y tolerancia entera igualada, Budget-L2 y L2
   con ambas tolerancias globales a `1e-9` (72 asignaciones).
4. Controles de mecanismo en `instance046` con las mismas tres semillas: desactivar
   presolve, NumericFocus 3, exportación diádica de ambos métodos, IntegralityFocus,
   M ajustados, indicadores, Base y el Ruiz de filas ya definido (27 asignaciones).
5. Construcción de un testigo MILP factible exacto cuando las cotas reportadas parezcan
   incompatibles con puntos de costo menor. Se fijan las binarias de una solución
   guardada, se resuelve el LP restante con SoPlex y se verifican independientemente
   todas las filas, cotas y dominios con `Fraction`. El testigo debe corresponder a
   los datos binary64 del archivo realmente importado por el solver. No certifica
   optimalidad global del MILP.

La semilla del orden aleatorio de llamadas es 20261014. Las llamadas medidas a
solvers son secuenciales. Logs, parámetros, factores, exportaciones, soluciones y
protocolos se conservan por observación. Los programas guardados en cada diseño
documentan su versión; las modificaciones posteriores no cambian el piloto.

## Precisión y controles

Los objetivos numéricos de 0,01 MW y 100 m³ son el escenario exigente elegido
antes de esta exploración. Se extiende explícitamente el objetivo de volumen a
la consistencia numérica del umbral de activación; no se lo presenta como una
tolerancia del operador ni se confunde esa fila con un balance hidráulico. Las
comparaciones con 1.000 y 10.000 m³ permanecen análisis de sensibilidad, no estándares.

L2 usa únicamente coeficientes, escala también el RHS y proyecta su factor sobre
la ventana `[1e-9,1e9]`. No usa una banda de identidad. Budget-L2 usa el mismo
kernel y cambia el factor solamente cuando el presupuesto lo requiere. Una prueba
estructural comprueba esas diferencias por nombre, así como objetivo, cotas y
dominios. Se reserva el transporte entero y, en las activaciones, un límite del
error de exportación sobre la caja finita de las variables. Los archivos usan
serialización de ida y vuelta. Los controles diádicos permiten descartar el
redondeo de los productos como explicación de un resultado.

La tolerancia entera guiada es una potencia de dos no mayor que la mitad del
presupuesto de volumen dividida por el mayor M de activación. L2-matched-int y
Budget-L2 comparten esa tolerancia para atribuir diferencias a los factores. El
control global usa `FeasibilityTol = IntFeasTol = 1e-9`. Las hipótesis contractuales
se contrastan con los residuos efectivamente observados; un parámetro nominal
no constituye por sí solo una garantía.

M ajustados e indicadores se aplican solamente a las activaciones de volumen.
Con `v >= L`, la fila `M*b-v <= M-V` es redundante para `b=0` cuando `M>=V-L`,
y exige `v>=V` para `b=1`. La sustitución por `M'=max(0,V-L)` o por un indicador
mantiene la región factible entera, aunque cambie la relajación. Se conservan las
condiciones de esa equivalencia para cada fila. La licencia CPLEX local no admite
estos modelos; los controles comerciales de esta ampliación usan Gurobi 13.0.2.

## Criterio de incorporación

La elección depende de los resultados completos y de su verificación. Sería útil
un caso donde el contrato cambie factores o detecte información insuficiente y
ello cambie una decisión de precisión, verificación o fiabilidad frente a controles
plausibles. Una mejora de condición sin consecuencia práctica no basta. Tampoco
basta que una política sea rápida si la calidad reportada resulta contradicha por
un testigo válido. No se añaden teoremas para presentar estos controles conocidos
como nuevos ni se atribuye una ventaja universal.

Si la evidencia merece incorporación, el cuerpo recibirá una explicación breve;
protocolos, controles completos y testigos irán al suplemento y al artefacto. Si
la ventaja no se sostiene, se conserva la versión cerrada y se documenta el límite.
