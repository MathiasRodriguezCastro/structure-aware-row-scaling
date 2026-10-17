# Reparación, aceptación y decisión numérica: resultados del seguimiento

**Conclusión:** verificar y reparar recuperó tres entregas que fallaban en Base,
pero este seguimiento no demuestra una ventaja propia del escalamiento contractual.
Tolerancias estrictas e IntegralityFocus igualaron su aceptación. La reparación
fue barata en estos casos, con una pérdida importante de calidad del objetivo en
control30-3-2-3. Se conserva como investigación independiente, sin agregar otra
contribución al paper OMS v1.3.5.

## Diseño y alcance

Se fijaron 80 tratamientos antes de resolver: cinco modelos, semillas 11 y 23 y
ocho alternativas, con orden aleatorio registrado. Los horizontes Kondili H14 y
H16 son nuevos; los tres modelos MIPLIB son los seleccionados en el piloto, con
semillas nuevas. Eso añade confirmación limitada, no nuevas familias ni una muestra
representativa. La calibración anterior, semilla 17, queda fuera de los denominadores.

Gurobi 13.0.2, cuatro hilos, presolve y escalado interno automáticos, gap 1 %, MILP
hasta 15 s y referencia de 20 s para el ciclo. Se aplican exactamente las reglas
diádicas existentes. HiGHS 1.15.1 reoptimiza el LP con los enteros fijados; SoPlex
8.1.0/GMP 6.2.1 queda como reparación exacta condicional. No se reajustaron factores,
presupuestos o parámetros después de ver resultados.

Los presupuestos STN siguen siendo 1e-5 kg (10 mg) para material, 1e-5 para lógica
y 1e-3 en unidades monetarias de la fuente; son objetivos numéricos del estudio.
MIPLIB utiliza 1e-4 max(1, |RHS|), en unidades algebraicas experimentales. Una
entrega debe satisfacer todas las filas y cotas dentro de sus presupuestos y los
dominios enteros exactamente. La garantía contractual MIPLIB se refiere al punto
crudo; el redondeado se comprueba después, sin promesa uniforme de redondeo.

## Aceptación y costo completo

| Tratamiento | Fuente tras redondear | Entregas verificadas | LP de reparación | Abstenciones contractuales | Suma de tiempos, s |
|---|---:|---:|---:|---:|---:|
| Default-check | 7/10 | 7/10 | 0 | 0 | 40.381 |
| Tight-check | 10/10 | 10/10 | 0 | 0 | 48.326 |
| NumericFocus-check | 6/10 | 6/10 | 0 | 0 | 32.690 |
| IntegralityFocus-check | 10/10 | 10/10 | 0 | 0 | 68.679 |
| Base-check-repair | 7/10 | 10/10 | 3 | 0 | 39.193 |
| L2-check-repair | 7/10 | 10/10 | 3 | 0 | 52.895 |
| Budget-check-repair | 6/10 | 8/10 | 2 | 2 | 32.765 |
| Diagnostic-check-repair | 7/10 | 10/10 | 3 | 0 | 41.361 |

Todas las cuentas tienen denominador 10, incluidos los dos contratos incompatibles.
No son probabilidades poblacionales. Hay 78 llamadas MILP,
60 puntos fuente aceptables y 71
entregas verificadas. Los 11 LP condicionales recuperaron la entrega;
su costo incluyó preparar, resolver, comprobar y guardar sus certificados y estuvo
entre 0.0407 y 0.1760 s. No se necesitó el LP exacto en esta confirmación.
Dos puntos de HiGHS resultaron también factibles exactos al comprobarlos racionalmente.

Los tiempos de la tabla incluyen selección real de factores, exportación,
importación y cotejo nativo, MILP, verificación y reparación condicional. La
persistencia exterior se mide aparte; los archivos auxiliares de reparación están
dentro del tiempo de reparación. No hubo excesos de 20 s ni errores de ejecución.
**Desviación de registro:** la construcción inicial común de los modelos no se
cronometró por separado, pese a la frase correspondiente del protocolo. No se
presenta una suma que incluya esa etapa. Se documenta en audit-deviations.json.
El entorno y los tiempos por etapa quedan registrados. No se infiere superioridad
general en velocidad de dos semillas o de sumas con objetivos diferentes.

## Precisión recuperada y calidad del objetivo

En control30-3-2-3, reparar Base entrega costo 26,248128, desde puntos crudos
no entregables de −39,917360 (semilla 11) y −23,049913 (23). Budget reduce el
costo reparado a 24,661027 y L2 entrega 33,373658. Los controles Tight e
IntegralityFocus entregan costos cercanos a 1,27: son mucho mejores, aunque usan
aproximadamente 15 s. Un punto reparado rápido con peor objetivo no equivale a
una optimización rápida de igual calidad. No se conserva el gap del punto fuente.

| Semilla | Tratamiento | Objetivo entregado, minimización | Ciclo, s |
|---|---|---:|---:|
| 11 | Tight-check | 1.265274 | 15.154 |
| 11 | IntegralityFocus-check | 1.265272 | 15.114 |
| 11 | Base-check-repair | 26.248128 | 0.218 |
| 11 | Budget-check-repair | 24.661027 | 0.290 |
| 11 | L2-check-repair | 33.373658 | 0.295 |
| 23 | Tight-check | 1.265275 | 15.158 |
| 23 | IntegralityFocus-check | 1.315832 | 15.140 |
| 23 | Base-check-repair | 26.248128 | 0.242 |
| 23 | Budget-check-repair | 24.661027 | 0.230 |
| 23 | L2-check-repair | 33.373658 | 0.207 |

En Kondili todos los tratamientos cumplen, sin reparaciones. El diagnóstico
elige Budget y no mejora la aceptación del control. En cinca, Base, Tight e
IntegralityFocus cumplen; NumericFocus falla en ambas semillas. L2 requiere
una reparación en semilla 23. Budget se abstiene por 96 intervalos incompatibles.
En ta1-UUM se repara Base para semilla 23, con cambio de objetivo de 0,282 unidades.
La ventaja observada allí proviene del LP de reparación, no del contrato.

## Testigos exactos y contradicciones de cotas

Un LP flotante de ta1-UUM entrega un vector binary64 que satisface **exactamente**
todas las restricciones de la representación canónica. Su objetivo exacto,
comprobado con Fraction, se muestra como 7695229.19. Es una cota superior primal
del mismo modelo original. Las dos llamadas Tight declaran terminación óptima y
reportan cotas inferiores que la exceden:

| Semilla Tight | Cota inferior reportada | Testigo factible exacto | Diferencia |
|---|---:|---:|---:|
| 11 | 7813164.58 | 7695229.19 | 117935.39 |
| 23 | 7842648.07 | 7695229.19 | 147418.88 |

El testigo mejora también sus objetivos en más de 1 %. Importación y escalado se
cotejaron contra el mismo JSON original; la comparación no mezcla modelos. El
checker usa una guarda de max(1e-6, 8 ulp(cota)), muy inferior a estas diferencias.
Por lo tanto, esos informes de cota/gap quedan contradichos para el modelo
canónico. No se afirma haber certificado el óptimo global, ni que las demás cotas
sean válidas por ausencia de contradicción. No se atribuye una causa específica
al presolve, al escalado interno o al solver sin experimentos adicionales.
El checker también vuelve a leer los tres MPS originales, sin llamar al solver,
y coteja coeficientes, RHS, objetivo, sentidos, cotas y dominios con los modelos
canónicos; valida los SHA-256 originales de descarga. El adapter admite únicamente
las características presentes y rechaza otras. Se aplica la interpretación
binary64 de literales y los defaults documentados en el
[formato MPS de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/reference/fileformats/modelformats.html).

## Mecanismo, entrega y garantías

Los máximos coeficientes enteros de los tres MIPLIB son 1,058e7, 1e17 y 1,109e7,
mientras que los máximos continuos son 1, 1,4 y 1. Al fijar enteros desaparecen
de la matriz LP los coeficientes grandes, lo que orientó la reparación. Esto no
garantiza buena condición, factibilidad del entero elegido o éxito del LP.

El ciclo comprueba el punto fuente redondeado; si falla, fija los enteros más
próximos, prueba un LP flotante y, si sigue sin entrega verificada, un LP racional
con los datos originales completos. Cada candidato se comprueba en **todas** las
filas, cotas y dominios originales. Solo devuelve una entrega que pasa. Hay a lo
sumo una llamada MILP y dos LP; la terminación depende de que los backends terminen
o respeten sus mecanismos de interrupción. El presupuesto temporal es una
referencia operativa, no una garantía de tiempo real del sistema operativo.

Una contradicción constante tras fijar enteros prueba que ese patrón no tiene
continuación exacta, no que el MILP completo sea inviable. La factibilidad racional
del LP tampoco prueba optimalidad MILP ni que convertir su testigo a float conserve
las precisiones. El desarrollo separado sí obtuvo un testigo exacto de
control30-3-2-3, costo 26,248128; la conversión también pasa. Su tiempo medido fue
0.1091 s. Ese ensayo de desarrollo no entra en la tabla principal.

### Obstrucción de representación comprobable

Para una igualdad unaria a x = b después de fijar los enteros, sea q=b/a y sean
f− y f+ sus vecinos binary64 adyacentes. Si ambos son finitos, el menor residuo
alcanzable entre valores binary64 es min(|a f−−b|, |a f+−b|): a cada lado de q,
la distancia crece al alejarse. Si ese mínimo excede δ, ningún valor binary64
con ese patrón entero puede satisfacer el presupuesto de esa fila.

Ejemplo de comprobación, **no modelo experimental favorable**: 3x=1, 0≤x≤1.
El testigo racional x=1/3 es exacto, pero el menor residuo binary64 es 2^−54.
Con δ=2^−55 no hay entrega aceptable; con δ=2^−54 sí. Los tests comprueban ambos
casos. No se hallaron obstrucciones unarias en los casos reales del seguimiento.
Esta propiedad elemental separa factibilidad exacta y precisión de representación;
no se presenta como un teorema nuevo ni como una mejora práctica ya demostrada.

### Diagnóstico previo y error de exportación

La regla fijada eligió Budget para STN y Base con reparación reservada para los
tres MIPLIB. Logró 10/10, como Base-repair, con mayor costo de selección. En
48 puntos fuente que pasan, la cota nominal μ supera 1: la falta de garantía
suficiente sigue sin ser un predictor de fallo. Solo 12 puntos tienen μ≤1;
el checker verifica sus hipótesis de residuos exportados e integralidad y no
encuentra contradicciones de la cota cuando esas hipótesis se cumplen.

El soporte firmado de exportación ya desarrollado en el piloto es
R⁺ = Σ max[(αa_j−â_j) l_j, (αa_j−â_j) u_j] − (αb−b̂).
Bajo pertenencia del punto a la caja y residuo exportado ≤ε, la violación tras
redondear es ≤max(0,(ε+R⁺)/α+γΣ_enteros|a_j|). Para igualdad se aplican ambos
signos. Los coeficientes con error cero no necesitan cotas finitas. Aquí las
exportaciones diádicas son exactamente proporcionales, de modo que R⁺=0.
No se atribuye a ese diagnóstico una predicción o utilidad que los datos no prueban.

## Antecedentes y decisión para OMS

La reparación exacta y la certificación ya tienen antecedentes explícitos en
[Eifler y Gleixner](https://arxiv.org/abs/2101.09141) y
[Cheung, Gleixner y Steffy](https://arxiv.org/abs/1611.08832).
[SoPlex](https://soplex.zib.de/doc/html/EXACT.php) implementa LP racional;
[IntegralityFocus](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameterintegralityfocus)
es un control existente pertinente. No se reclama como novedoso verificar o
reparar. El posible desarrollo es integrar requisitos, representación, aceptación,
abstención y calidad con trazabilidad; esta muestra no demuestra una ventaja
propia de contratos que justifique una nueva contribución en el artículo.

**Decisión:** mantener el envío OMS v1.3.5. La investigación deja un ciclo ejecutado,
reparaciones y certificados reproducibles, una separación comprobada entre precisión
y optimalidad y un resultado negativo útil sobre el diagnóstico. Los resultados
no justifican ampliar el paper ni iniciar una búsqueda de casos favorables.

## Reproducción

```bash
python3 exploration/oms-decision-study-20261014/independent_check.py
python3 -m pytest -q exploration/oms-decision-study-20261014/test_repair.py
python3 exploration/oms-decision-study-20261014/write_report.py
```

Python/NumPy bastan para el checker; pytest para cinco tests. El replay no llama
solvers. El artefacto contiene protocolo, congelamiento y enmienda preejecución,
fuentes, modelos, 80 registros, puntos, logs, certificados, tiempos y hashes.
Los certificados son del **modelo canónico binary64**, no de una interpretación
racional ideal de los decimales del MPS ni de precisión física operativa.
