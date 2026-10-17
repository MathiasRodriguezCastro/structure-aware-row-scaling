# Exploración completada y decisión de incorporación

La continuación solicitada después de estas notas obtuvo resultados nuevos.
[RESULTADOS.md](RESULTADOS.md) contiene las conclusiones, límites y reproducción.
Las notas siguientes se conservan como diagnóstico inicial, anterior a las nuevas llamadas.

# Exploración separada del cierre para OMS

14 de octubre de 2026. Decisión del autor: cerrar la versión actual para OMS y
explorar por separado solamente mejoras que aporten valor sin ampliar el alcance
indefinidamente. Se conserva `v1.3.2-oms-submission`; esta nota y sus datos no se
incorporaron al manuscrito, los suplementos ni el paquete congelado. La preparación
local está terminada; no se realizó una presentación editorial ni un depósito nuevo.

## Resultado de esta primera exploración

Hay una pista concreta para estudiar la verificación de soluciones después del
redondeo entero: una restricción de activación de un tramo de Salto Grande. No se
encontró una necesidad de modificar los factores dentro del alcance físico auditado
en el artículo. Tampoco se demostró una ventaja práctica de los contratos frente al
escalado convencional o al ajuste de tolerancias.

Se leyeron los 1.710.720 registros existentes de contratos y se examinaron los seis
modelos ya elegidos para la comprobación de etapas: Simple `caso01a`, `caso24f`,
`caso46e`; SG-Ter-Mer `instance001`, `instance046`, `instance092`. Se usaron sus
36 soluciones guardadas, con las cuatro políticas principales y las dos parciales.
No se generaron instancias, no se cambiaron presupuestos y no se llamó a optimizar.

## Por qué los contratos actuales son holgados

Para cada fila, con conversión `u` de unidades físicas a algebraicas, se calculó
el margen condicional `alpha*u*delta/epsilon`, usando el escenario exigente ya
declarado (0,01 MW y 100 m³) y `epsilon = 1e-6`. Es una medida del límite de
residuo supuesto, no del residuo efectivamente observado. No incluye por sí sola
el defecto de exportación ni el transporte por redondeo entero.

| Política | Menor margen en potencia | Menor margen en agua | Mayor límite condicional en agua |
|---|---:|---:|---:|
| Base | 10.000 | 100.000.000 | 0,000001 m³ |
| Flat-GM | 10.000 | 27.777,8 | 0,0036 m³ |
| Ruiz-R4 | 10.000 | 46.341,1 | 0,002158 m³ |
| Role-Hybrid | 10.000 | 27.777,8 | 0,0036 m³ |

El límite condicional máximo en potencia es 0,000001 MW en las cuatro políticas.
Las políticas parciales reproducen estos márgenes en su subconjunto. La tabla
explica por qué profundizar en los mismos balances con estos presupuestos no
parece una vía prometedora para demostrar utilidad de la selección de factores.
`conditional-headroom.csv` conserva las filas e instancias limitantes.

## Lo que cambia al redondear una binaria

Las 25.920 filas físicas de los seis modelos examinados no contienen variables
enteras. Por su soporte, sus actividades permanecen exactamente iguales cuando
se modifican únicamente las coordenadas enteras. Este resultado se limita al
alcance publicado: identidades y límites de potencia, definiciones de generación,
envolventes de producción y balances de agua.

Las filas auxiliares de activación de tramos sí contienen binarias y están fuera
de ese alcance. Se verificaron las 1.440 filas de activación de cada uno de los
tres modelos SG-Ter-Mer sobre sus seis soluciones. En `instance046`, la fila
`a1_activacion_1(18)` tiene la forma

```text
12494793414.450399 * varphi - v <= 10427944344.323
```

El generador declara `v` en m³ y `varphi` binaria. En el punto Base guardado,
`varphi = 0.9999996126403118` y `v = 2066844230.148119`. El punto crudo satisface
esa fila. Después de redondear `varphi` a 1 manteniendo las otras coordenadas,
la violación es exactamente `2537543057/524288` m³ para los coeficientes, RHS y
punto interpretados como datos binary64. Esto equivale a 4.839,979280471802 m³.
No es un certificado sobre datos físicos anteriores a su representación.

| Política en instance046 | Máxima violación de activación cruda | Máxima después del redondeo |
|---|---:|---:|
| Base | 0 m³ | 4.839,9793 m³ |
| Flat-GM | 0 m³ | 0 m³ |
| Ruiz-R4 | 0 m³ | 4.839,5246 m³ |
| Role-Hybrid | 0 m³ | 0 m³ |
| Local-only | 0 m³ | 0 m³ |
| Coupling-only | 0 m³ | 4.839,9793 m³ |

Base y Coupling-only son representaciones idénticas en esta comprobación; tampoco
Local-only y Role-Hybrid constituyen observaciones independientes. En los otros
dos modelos no se observaron violaciones positivas de activación, ni crudas ni
redondeadas. Ruiz-R4 es el control de filas del artículo, con columnas fijas y
cuatro iteraciones; no es una comparación con el procedimiento completo de Ruiz.

La comprobación de demanda detecta inversión solamente en `instance092` entre
estos tres modelos. `instance046` no presenta ese defecto. Esto no certifica la
corrección operativa completa de sus datos ni el impacto de la activación sobre
la potencia o el costo del despacho.

## Qué aporta esta pista y qué falta

La fila permite investigar una decisión concreta: aceptar, rechazar o corregir
una solución al convertir las binarias a estados exactos. El redondeo altera la
activación aun cuando los balances de agua mantengan sus residuos. La medida
normalizada del modelo completo alcanza aproximadamente `3.32e-7` después del
redondeo; una medida normalizada pequeña no basta para interpretar este umbral
de volumen. Esa medida se calculó en punto flotante y se conserva como diagnóstico.

El transporte por redondeo está gobernado por `M*gamma`. Con la tolerancia de
integralidad declarada `gamma = 1e-5`, su reserva conservadora en esta fila es
124.947,934 m³. Multiplicar la fila por un factor no cambia esa cantidad en m³.
Por tanto, un contrato que reserve ese error puede detectar agotamiento de un
presupuesto; el escalado de filas por sí solo no resuelve el redondeo entero.

Usando únicamente el límite inferior exportado `v >= 0`, el menor M válido para
esta implicación en aritmética exacta sería `max(0,V-L)`, aproximadamente
2.066.849.070 m³. Su reserva a `1e-5` seguiría siendo unos 20.668,5 m³. No se
exportó ni resolvió esa reformulación. Con el M actual y `gamma = 1e-9`, la
reserva sería unos 12,495 m³; esto es una cota analítica del canal de redondeo,
no el resultado de una ejecución con tolerancias más estrictas.

Los presupuestos de 100, 1.000 y 10.000 m³ del artículo se refieren a balances.
No se asignaron automáticamente a la activación de tramos ni se presentaron
como tolerancias operativas. Antes de una prueba adicional se necesita justificar
cuál es el error admisible en ese umbral y qué consecuencia tiene para la decisión.
Después corresponde comparar contratos con tolerancias más estrictas,
`IntegralityFocus`, M más ajustados e implicaciones mediante indicadores, midiendo
residuos crudos y redondeados, trabajo, tiempo y objetivo. Estas alternativas ya
están documentadas por el fabricante; el hallazgo no demuestra novedad ni superioridad
de un mecanismo nuevo. [Guía de tolerancias y Big-M de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html),
[IntegralityFocus](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameterintegralityfocus).

La relación entre escalado de filas y precisión interpretable ya forma parte de
las recomendaciones del solver. El posible aporte adicional debe estar en la
selección admisible, detección de incompatibilidades y verificación que cambia
una decisión útil, con evidencia comparativa.
[Recomendaciones de escalado de Gurobi](https://support.gurobi.com/hc/en-us/articles/26284047605521-How-do-I-scale-my-model-to-improve-its-numerical-properties).

Se detiene aquí esta exploración acotada. El cierre para OMS no depende de hallar
esa ventaja. La activación de volumen queda como primer candidato para una
investigación posterior; todavía no justifica una campaña amplia ni reabrir el paper.

## Reproducción

Desde la raíz del repositorio, con las dependencias de investigación instaladas:

```bash
python3 exploration/oms-followup-20261014/screen_existing.py
```

El programa usa HiGHS para leer los LP y NumPy/SciPy para diagnósticos; no optimiza
ni requiere una licencia comercial. Escribe únicamente en esta carpeta. Sus
aserciones comprueban el número de contratos, ausencia de cambios, selección de
seis modelos, 36 puntos, tolerancia entera y soporte físico sin enteras. Los
testigos de activación usan `Fraction` sobre los datos binary64 originales.
`MANIFEST.json` registra hashes de los programas y entradas utilizados y de todas
las salidas numéricas. Las fuentes oficiales enlazadas se consultaron el 14 de
octubre de 2026.
