# Qué aportó esta continuación y qué no justifica incorporar

## Resultado de la búsqueda

Se desarrolló un selector exacto de escalas para actividades SOS, con dos
objetivos: radio mínimo y mejor centrado admisible. Hay equivalencia proyectada,
una cota condicional para el punto redondeado que no necesita distancia de la
binaria a entero, una caracterización necesaria y suficiente por intervalos de
exponentes y certificados de incompatibilidad. El selector no llama a un solver.

Es un desarrollo real de implementación y matemática en este proyecto. No se
ha establecido prioridad de la construcción completa. SOS1, normalización de
holguras y holguras compartidas tienen antecedentes explícitos en SCIP. La
literatura consultada se conserva; no se presenta una búsqueda limitada como
prueba de novedad.

La evidencia computacional **no respalda incorporarlo a OMS como método nuevo
con ventaja práctica**. El resultado de 360 procesos nuevos es:

| Política | Precisión original / 45 | Precisión y calidad de referencia / 45 |
|---|---:|---:|
| Centered-shared, propuesta | 33 | 17 |
| Centered-individual | 35 | 17 |
| Minimum-shared | 30 | 18 |
| Normalización de coeficientes | 37 | 27 |
| Normalización con tolerancias estrictas | 41 | 18 |
| Indicadores con presupuesto | 37 | 28 |
| Filas con tolerancias estrictas | **44** | **33** |
| Centro compartido sin contrato | 33 | 18 |

Cada denominador contiene cinco modelos, tres presupuestos algebraicos y tres
semillas. No son 45 aplicaciones independientes. Algunas políticas coinciden
por bytes y parámetros; se identifican antes de interpretar sus resultados.
La calidad usa el margen del 1% sobre las referencias fijadas y no certifica
optimalidad. La primaria anterior añade 195 ejecuciones válidas: **555 en total**,
con los intentos de recuperación documentados por separado.

## Por qué no se rescata el candidato con un control débil

A 1e-6, la propuesta falla precisión en control30 y cinca; en neos-1112787 y
k16x240b satisface precisión pero no alcanza la referencia en ninguna semilla.
En beasleyC3 alcanza ambas metas en 3/3, pero Tight-raw también y requiere
menos trabajo y menor ciclo mediano. En las otras celdas tampoco aparece una
ventaja robusta frente a ese control. Un tiempo corto con punto no entregable
no se cuenta como aceleración.

El centro sin contrato ya está dentro del intervalo a 1e-4 en los cinco
modelos. A 1e-6 y 1e-8 el contrato sí modifica la elección: se comprobaron
6.629 bloques truncados al intervalo y 7.160 límites convencionales que exceden
el presupuesto. Esa actividad algebraica no se traduce aquí en una ventaja
efectiva. Tampoco mejora la propuesta al simplemente individualizar actividades.

Los dos modelos nuevos de redes con costos fijos amplían la evaluación, pero
sus controles ya cumplen los presupuestos. No aportan una recuperación primal
externa exclusiva de la propuesta. Los cinco modelos no son una muestra
representativa de familias ni el resultado negativo prueba imposibilidad general.

## Hallazgo concreto y verificable

En cinca, Centered-shared cumple los presupuestos en 3/3 a 1e-4 y 3/3 a 1e-8,
pero falla en 3/3 a 1e-6. Para la semilla 199, una activación tiene violación
redondeada **0,015642202283948508**, unas **15.642 veces** su presupuesto de 1e-6.
El factor seleccionado satisface el contrato, pero la salida incumple su
hipótesis de soporte SOS. A los otros dos presupuestos todas las activaciones
de esa semilla tienen residuo no positivo después de redondear.

`centered-followup/NONMONOTONICITY_CASE.json` conserva el ejemplo compacto y
`check_nonmonotonicity.py` lo comprueba usando solo racionales de Python.
La selección del ejemplo es retrospectiva y se etiqueta así. No es una
confirmación independiente ni una explicación causal completa de Gurobi.
La inspección de presolve observa cambios de coeficientes/cotas auxiliares,
sin afirmar una inversión completa del mapa de presolve.

La nueva derivación reconoce también un límite de representación: conservar
un minimizador representable no basta para asegurar covariancia global del
selector. Se construyó un contraejemplo de frontera y se precisó la condición
en ambos sentidos en COVARIANCE_SCOPE.md. Las 25 exportaciones comparadas en
las unidades ensayadas sí son idénticas por bytes.

## Decisión para el manuscrito

Mantener esta investigación separada. No añadir otra contribución principal,
otra tabla de grandes campañas ni una afirmación de superioridad basada en
centrado o factores admisibles. El envío v1.3.14 conserva sus resultados propios.

La búsqueda de un método con ventaja clara **sigue sin alcanzar ese objetivo**.
Este candidato queda descartado para incorporarlo al artículo con la evidencia
actual. Los protocolos, código, puntos, fallos y resultados quedan disponibles
para evitar repetirlo como si fuera una dirección no explorada. Eso no equivale
a declarar agotados todos los métodos posibles ni a garantizar una publicación.
