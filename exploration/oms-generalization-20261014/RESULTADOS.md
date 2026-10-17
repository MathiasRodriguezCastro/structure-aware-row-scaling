# Resultados preliminares y decisión de alcance

**Conclusión:** el procedimiento se pudo trasladar a fuentes independientes, pero
este piloto no demuestra una ventaja de aceptación primal de Budget-L2 frente a
su control o a las alternativas existentes. No se incorpora al artículo actual.
El aporte tangible por ahora es un prototipo de aceptación/abstención comprobado,
certificados de incompatibilidad y evidencia que limita el uso predictivo del diagnóstico.

Se conservaron 55 brazos, incluidos dos que se abstienen por incompatibilidad y
uno que falla al importar. Se resolvieron 52 brazos y se guardaron sus puntos.
Un checker separado, sin importar el runner ni ningún solver, verifica esos 52
puntos con aritmética racional: 41 cumplen los presupuestos después de redondear
enteros y 42 antes. Estas cuentas mezclan configuraciones deliberadamente distintas
y no son tasas poblacionales ni un ranking de métodos. Todo es piloto, semilla 17.

## Portabilidad a producción por lotes

El generador STN-Scheduler y los datos originales de Kondili son independientes
del despacho hidrotérmico. H=10 tiene 409 filas efectivas y 321 variables; H=12,
483 filas y 379 variables. Los contratos cambian exactamente 88 y 104 factores
de filas de capacidad. El objetivo de precisión es 1e-5 kg (10 mg), elegido para
el estudio; no es una exigencia de una planta. Todas las políticas y ambos solvers
cumplen el presupuesto en ambos modelos. Modificar factores no equivale a obtener
una mejora práctica cuando el control ya cumple la precisión.

## MIPLIB y controles

Los tres modelos se eligieron por criterios fijados antes de resolver: tag Numerics,
mezcla de variables continuas y enteras, dimensiones acotadas y primeros tres grupos
distintos al ordenar por no ceros y nombre. Los presupuestos son numéricos algebraicos,
no físicos. Se conserva la discrepancia entre la ficha y los no ceros del MPS de cinca.

V = asignación entera verificada dentro de los presupuestos de todas las filas y cotas;
F = existe punto, pero falla esa comprobación; A = abstención por incompatibilidad;
I = fallo de importación; -- = parámetro no disponible. V no significa factibilidad
exacta ni optimalidad. Los métodos escalados son variantes diádicas exactas: el control
L2 y Budget comparten kernel, cotas de coeficientes y, en STN, tolerancia entera.

| Modelo | Solver | Base | GM | L2 | Budget-L2 | L2-tight | NumericFocus 3 |
|---|---|---|---|---|---|---|---|
| Kondili-H10 | gurobi | V | V | V | V | V | V |
| Kondili-H10 | highs | V | V | V | V | V | -- |
| Kondili-H12 | gurobi | V | V | V | V | V | V |
| Kondili-H12 | highs | V | V | V | V | V | -- |
| control30-3-2-3 | gurobi | F | F | F | F | F | F |
| control30-3-2-3 | highs | V | V | V | V | V | -- |
| neos-3421095-cinca | gurobi | V | F | F | A | F | F |
| neos-3421095-cinca | highs | I | V | V | A | V | -- |
| ta1-UUM | gurobi | V | V | V | V | V | F |
| ta1-UUM | highs | V | V | V | V | V | -- |

En `control30-3-2-3`, Budget-L2 reduce el máximo residuo/presupuesto del punto
crudo Gurobi de 26.526 (L2) a 0,302; sin embargo, el punto redondeado sigue
fallando, con ratio 146.563. Base y GM también cumplían el presupuesto crudo.
No es una recuperación de una asignación entera verificada ni superioridad sobre
las alternativas. Las seis variantes Gurobi fallan el chequeo redondeado en este
piloto. HiGHS devuelve puntos que lo superan, pero alcanza el límite de 15 s en
todas las variantes: hay precisión primal, no una certificación de optimalidad.

En `neos-3421095-cinca`, 96 intervalos continuos del contrato son vacíos con las
especificaciones declaradas. Budget se abstiene en ambos solvers. La importación
Base de HiGHS falla con coeficientes de hasta 1e17; escalados convencionales permiten
importar y obtener puntos que cumplen tras redondear. Gurobi Base también entrega
un punto que cumple. La incompatibilidad limita la garantía uniforme solicitada,
no prueba que el problema sea inviable o que no exista una buena solución.

En `ta1-UUM`, el contrato cambia 55 filas y ambos métodos L2 superan los presupuestos;
todos alcanzan el límite. NumericFocus 3 falla este chequeo en Gurobi. Un remedio
numérico existente tampoco garantiza resultados en todas las configuraciones, pero
este caso no prueba una ventaja propia de Budget frente a su control directo.

## Costos del contrato en STN

| Modelo | Solver | L2: solver s | Budget: solver s | L2: trabajo | Budget: trabajo |
|---|---|---|---|---|---|
| Kondili-H10 | gurobi | 0.0100 | 0.0126 | 0.00478 | 0.00574 |
| Kondili-H10 | highs | 0.2563 | 0.2572 | -- | -- |
| Kondili-H12 | gurobi | 0.0158 | 0.0182 | 0.00691 | 0.00778 |
| Kondili-H12 | highs | 0.0860 | 0.0769 | -- | -- |

Son tiempos de optimización de una llamada por configuración, no estimaciones de
velocidad general. Trabajo se conserva solamente para Gurobi. Excluyen selección
de factores, importación y verificación; el tiempo completo de cada llamada queda
en sus registros. Los controles ya satisfacen los presupuestos. La fracción del
presupuesto utilizada no permite equiparar la calidad de objetivos o cotas MILP.

## Diagnóstico previo y algoritmo

El diagnóstico computa μ = (ε/α + γ Σ|a_j|)/δ usando los parámetros nominales,
por fila y solver. En 31 puntos verificados, μ supera uno: no disponer de esa
garantía suficiente no predice necesariamente un fallo. El checker comprueba también
los residuos exportados realmente observados y la hipótesis entera; cuando todas
las hipótesis y μ≤1 se cumplen, las filas pasan la verificación, como exige la cota.
No se entrenó un predictor ni se evaluó uno en datos de confirmación.

`certifying_workflow.py` implementa un ciclo finito de intento, verificación,
alternativa y abstención. Devuelve solamente la asignación redondeada que verifica;
mantiene el estado de optimalidad separado como no verificado. En el replay de diez
pares modelo/solver, devuelve nueve asignaciones comprobadas y se abstiene en
Gurobi/control30-3-2-3. Para HiGHS/cinca, rechaza la importación Base y usa el punto
L2 comprobado. El replay no es una evaluación prospectiva de una política adaptativa.
Siete tests cubren fallos tras redondear, dominios enteros exactos, etiquetas óptimas irrelevantes, datos no
finitos, importaciones no cotejadas y cotas de exportación contra todos los vértices.

La cota de exportación firmada utiliza el soporte de la caja real:
R⁺ = Σ max[(αa_j−â_j) l_j, (αa_j−â_j) u_j] − (αb−b̂).
La violación tras redondear queda acotada por max[0,(ε+R⁺)/α+E] si el punto crudo
pertenece a la caja y las hipótesis son válidas. Para igualdad se consideran ambos
signos. Los términos con error cero no necesitan cotas finitas. El prototipo y sus
tests verifican esta descomposición elemental; no se la presenta como teorema novedoso.
En este piloto las exportaciones diádicas tienen error exactamente cero.

## Originalidad y decisión

La verificación independiente, los certificados y la reparación de puntos ya tienen
antecedentes fuertes. Eifler y Gleixner (2021) incluyen reparación exacta en un solver
MILP racional; Cheung, Gleixner y Steffy (2016/2017) estudian certificados verificables.
Gleixner y Steffy desarrollan LP con oráculos de precisión limitada. No hay base aquí
para anunciar como nueva la idea general de resolver, verificar y reparar.

La diferencia potencial sigue siendo una especificación trazable de presupuestos de
aplicación, factores, representación y aceptación. Para elevarla a contribución
algorítmica falta una evaluación prospectiva de las decisiones y costos totales y
una comparación con reparaciones/tolerancias/controles existentes. Este piloto
comprueba portabilidad y límites, sin demostrar esa ventaja.

**Decisión para el paper:** conservar v1.3.5 sin cambios. No agregar otra contribución,
otra tabla principal ni una campaña oportunista. La siguiente fase que podría aportar
valor sería ejecutar un ciclo de verificación y reparación bajo un protocolo fijo,
con requisitos defendibles y modelos/semillas no usados en el piloto. Debe informar
abstenciones y costo total y superar un control directo; si no lo hace, queda fuera.

## Reproducción

Desde la raíz del repositorio o del artefacto extraído:

```bash
python3 exploration/oms-generalization-20261014/generalization_study.py verify
python3 exploration/oms-generalization-20261014/independent_check.py
python3 exploration/oms-generalization-20261014/certifying_workflow.py
python3 -m pytest -q exploration/oms-generalization-20261014/test_certifying_workflow.py
```

El replay necesita Python/NumPy y pytest para los tests; no requiere Gurobi, HiGHS,
Pyomo o licencias. Regenerar modelos y ejecutar llamadas nuevas sí requiere las
dependencias descritas en `PILOT_PROTOCOL.md`. Los datos originales, logs, decisiones,
objetivos, puntos y resultados adversos se mantienen identificados por hashes.

Fuentes primarias:

- [STN-Scheduler y licencia MIT](https://github.com/jckantor/STN-Scheduler).
- [MIPLIB Numerics](https://miplib.zib.de/tag_numerics.html).
- [Guía numérica de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html).
- [Eifler y Gleixner, reparación/certificación exacta](https://arxiv.org/abs/2101.09141).
- [Cheung, Gleixner y Steffy, certificados](https://arxiv.org/abs/1611.08832).
- [Gleixner y Steffy, oráculos de precisión limitada](https://optimization-online.org/wp-content/uploads/2019/12/7507.pdf).
