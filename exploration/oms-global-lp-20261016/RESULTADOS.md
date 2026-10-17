# De intervalos condicionales a garantías globales comprobadas

**Se obtuvieron seis cotas inferiores globales exactas.** A diferencia de los
LP de reparación anteriores, estas relajaciones dejan libres las 1440 binarias
dentro de [0,1]. Los duales se comprueban racionalmente contra el modelo original:
signos, identidad de costos reducidos y objetivo. No se confía en una cota de
Gurobi ni se usa el dual de un LP de patrón como si fuera global.

Combinadas con seis testigos enteros Base exactamente factibles, dan:

| Caso | Anchura certificada relativa | Conclusión |
|---|---:|---|
| 001 | 22,085 % | Intervalo, sin garantía del 1 % |
| 005 | 0,715 % | Solución de referencia certificada al 1 % |
| 022 | 0,338 % | Solución de referencia certificada al 1 % |
| 027 | 1,099 % | Intervalo, sin garantía del 1 % |
| 031 | **0 exacto** | **Óptimo MILP exacto certificado** |
| 046 | 5,209 % | Intervalo, sin garantía del 1 % |

Los objetivos son negativos. La anchura es (U-L)/|U|, donde L es la cota LP
global y U el costo de un punto entero exactamente factible. No es la brecha
de integralidad medida contra un óptimo entero desconocido. En 031 la igualdad
U=L se verifica como racional; no se deduce de redondear cifras impresas.

Los seis ciclos de construcción, LP exacto y comprobación costaron 23,98 s en
total en la máquina compartida. Los seis testigos enteros se adquirieron aparte
y su costo queda registrado. Los certificados se pueden comprobar sin solver.

## Refinamiento de las 18 salidas del prototipo conjunto

Un seguimiento fijado antes de adquirir nuevos LP conservó TODOS los patrones
enteros de las 18 salidas del piloto. Son 13 patrones distintos, declarados por
hash antes de resolver. Los 13 LP de patrón producen puntos exactamente factibles
del Base original; se verifican todas las filas, cotas e integralidad.

Al combinar sus costos U con la cota LP GLOBAL ya verificada:

- **18/18** salidas tienen un punto refinado exactamente factible.
- **9/18** tienen garantía global del 1 %: los tres casos 005,022,031 en tres semillas.
- **3/18** son óptimos exactos: las tres salidas de 031.
- Las otras nueve conservan su intervalo y no reciben una afirmación de optimalidad.

La adquisición y comprobación de los 13 patrones cuesta 48,52 s en total,
adicional al costo global y a la resolución MIP. La salida certificada es el
vector racional refinado, no el vector binary64 devuelto originalmente.
`verified-repairs.csv` enumera cada salida y su certificado.

Este es un resultado real para la arquitectura resolver–verificar–refinar:
permite entregar algunas garantías globales y reconocer cuándo no alcanzan.
No se atribuye al escalamiento la dualidad LP ni la idea general de reparar
patrones enteros. Otros métodos también pueden usar estos certificados. La
garantía adicional no es gratuita ni resuelve los casos difíciles 001 y 046.

## Incorporación y alcance

La tabla breve de **referencias Base** se incorpora como S19 al suplemento OMS,
sin insinuar que certifica todos los puntos o exportaciones flotantes de las
comparaciones principales. El refinamiento del prototipo conjunto permanece
en el informe de investigación separado. No se inicia una exploración DW o de
cortes para intentar cerrar los intervalos restantes en este trabajo.

Reproducción de las referencias suministradas:

```bash
python3 exploration/oms-global-lp-20261016/independent_check.py
```

En el artefacto de investigación completo, el seguimiento adicional se comprueba
con `python3 exploration/oms-global-lp-20261016/check_repairs.py`.
Los dos verificadores solo leen datos y hacen aritmética racional; no optimizan.
