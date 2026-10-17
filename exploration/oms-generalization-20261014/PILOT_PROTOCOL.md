# Piloto fijado antes de resolver

La selección externa se archivó en `MIPLIB_SELECTION.json` antes de cualquier
resultado del solver. El diseño y código del piloto están congelados en
`pilot/design.json` y `pilot/source-snapshot.py`. El runner exige conservar ese
hash para continuar una ejecución interrumpida.

## Modelos y unidades

- STN-Scheduler, commit `3b1d5f3adfb1165c06ca496775047d683886ab52`:
  datos originales de `kondili.py`, horizonte publicado H=10 y variación H=12.
  La implementación original produce inventarios/lotes en kg (`STN.py`, método
  `trace`). No se aumentan coeficientes ni se introducen M artificiales.
  Se omiten variables declaradas que no aparecen en objetivo o restricciones y
  desigualdades sin ninguna cota finita, como lo hace una exportación efectiva;
  las restricciones terminales repetidas por el generador se conservan.
- MIPLIB: `control30-3-2-3`, `neos-3421095-cinca` y `ta1-UUM`, de tres grupos
  distintos. Todas las expresiones de columnas y RHS del MPS se cotejan con los
  datos binary64 importados, antes de generar las representaciones comparadas.
  El archivo actual de `neos-3421095-cinca` tiene 4.350 no ceros frente a 3.678
  anunciados en la ficha; se conserva el archivo descargado y no se reemplaza.

## Presupuestos declarados

STN: `1e-5 kg` (10 mg) por fila de cantidades; `1e-5` en filas lógicas sin
dimensión y `1e-3` en las unidades monetarias de la fuente. Son objetivos
numéricos exigentes, no precisiones requeridas por una planta ni estándares
operativos. Cotas de variables: `1e-5` en unidades de material o lógicas y
`1e-3` para Value/Cost.

MIPLIB: `δ_r = 1e-4 max(1, |b_r|)` por fila original, en unidades algebraicas
experimentales. Presupuesto absoluto de cotas `1e-4`. No existe interpretación
física validada. La selección de factores cubre el punto crudo; no reclama una
garantía uniforme sobre el redondeo entero. Ambos puntos se comprueban después.

## Factores y tolerancias

Se usa la variante diádica ya existente: el intervalo de representabilidad de
`scripts/research/budget_scaling.py`, seguido de centering GM o proyección del
candidato L2 al intervalo de exponentes admitidos. Coeficientes `[1e-9,1e9]`;
hipótesis de residuo exportado `ε=1e-6`. Se verifica proporcionalidad exacta de
cada coeficiente y RHS en binary64, así que el error de exportación es cero.
Esto evita inventar cotas finitas en fuentes que incluyen variables sin cota
superior. Dyadic-L2 es el control directo de Budget-dyadic-L2; no se confunde
con la política histórica Flat-L2 ni con una exportación L2 arbitraria.

En STN se asigna una tolerancia entera diádica guiada por los presupuestos,
`γ ≤ min_r δ_r/(2 Σ_j∈I |a_rj|)`, y se iguala entre L2 y Budget-L2. Base/GM
usan las tolerancias ordinarias de cada solver. En HiGHS el parámetro MIP
acopla comprobaciones primal y entera; no se presenta como una variación
aislada de IntFeasTol. En MIPLIB los dos métodos usan las tolerancias ordinarias
del solver, con allowance entero cero en la selección y redondeo observado
comprobado por separado.

## Asignaciones y conservación

Dos solvers, cinco modelos y seis políticas (Gurobi) o cinco (HiGHS): 55 brazos.
Los brazos incompatibles se conservan como abstenciones, sin resolución.
Semilla 17; llamadas secuenciales; cuatro hilos; límite 15 s; gap 1 %;
presolve normal (Gurobi automático, HiGHS activado) y escalamiento interno
predeterminado. Gurobi incluye NumericFocus 3. El orden se fija con 20261014.
La reducción global pone las tolerancias relevantes a `1e-9`.

Cada importación se coteja exactamente con la representación esperada:
coeficientes, RHS, sentido, objetivos, cotas y dominios enteros. Una importación
que elimine o cambie términos falla la comprobación y queda registrada. Se
guardan parámetros, versión, logs, puntos NPZ, tiempos y resultados por brazo.
El estado del solver y la aceptación primal son columnas independientes.

## Alcance de aceptación

Todas las restricciones se verifican con `Fraction`, primero en el punto
binary64 crudo y después en la asignación con enteros exactos. La aceptación
significa que el punto redondeado satisface los presupuestos numéricos de filas
y cotas. No significa factibilidad exacta, ni validez de cotas duales, ni
optimalidad global. No se confrontan cotas con testigos meramente filtrados.

`certifying_workflow.py` implementa un ciclo finito que puede llamar a un solver
mediante un callback o reproducir intentos almacenados. El replay del piloto
ilustra sus transiciones; no mide el costo de una política adaptativa ejecutada
prospectivamente. Se devuelve solamente la asignación efectivamente comprobada.

Este es un piloto exploratorio con una semilla. Una ventaja encontrada aquí
requiere confirmación con semillas/modelos no usados para diseñar el seguimiento
y comparación de precisión, costo y calidad antes de incorporar algo al paper.
