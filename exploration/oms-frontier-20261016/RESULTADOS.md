# Un régimen precisión–esfuerzo comprobado

**El criterio fijado antes de resolver se cumple.** Con presolve automático,
presupuestos de 30 y 100 m3 y potencia fija de 0.01 MW, los seis modelos cumplen
los presupuestos en las tres semillas. Budget-L2 usa menos trabajo que NF3 en
cada modelo, no tiene más contradicciones de cotas detectadas y sus costos no
empeoran más del 1 % frente a los incumbentes NF3 comprobados en los objetivos
numéricos del estudio. No se certifica con esto la optimalidad global.

Son 360 asignaciones fijadas de antemano: 330 llamadas MILP, 30 abstenciones y
31 adquisiciones LP de testigos exactamente factibles de las exportaciones
binary64 realmente resueltas. El verificador vuelve a comprobar todos los
testigos y 2.851.200 residuos originales crudos/redondeados, además de 1.425.600
residuos en las filas físicas exportadas. No se descartó ningún resultado.

| Presolve automático | 30 m3 | 100 m3 |
|---|---:|---:|
| Budget-L2 cumple los objetivos | 18/18 | 18/18 |
| Cotas/cierres contradichos de Budget-L2 | 0/0 | 0/0 |
| Cotas/cierres contradichos de NF3 | 0/0 | 0/0 |
| Cotas/cierres contradichos de L2 | 5/4 | 5/4 |
| Trabajo emparejado Budget/NF3 | 0.411 | 0.362 |
| Tiempo completo emparejado Budget/NF3 | 0.704 | 0.629 |

Las razones son medias geométricas de 18 pares, no razones de medianas. A
100 m3 las razones de trabajo por modelo están entre 0.072 y 0.585; a 30 m3,
entre 0.128 y 0.668. El menor trabajo se observa en los seis modelos. Los
tiempos se midieron en una máquina compartida con otras tareas de investigación:
no se presentan como mediciones aisladas de hardware. A 30 m3 el ciclo completo
es más lento en tres modelos baratos; a 100 m3 sus seis razones por modelo son
menores que uno, pero una es 0.994 y no se interpreta como una ventaja sustancial.

## Límites que importan

La tolerancia entera común es 1e-9, distinta de 2^-28 en el factorial anterior.
Se eligió antes de resolver para estudiar el rango de presupuestos, y es igual
en los controles. Por eso no se mezclan ambas campañas. Las semillas nuevas son
59,71,89; los seis modelos siguen siendo conocidos y de una sola familia.

La mejora primal frente a L2 continúa localizada en instance046 sin presolve.
Con presolve automático L2 ya satisface todos estos presupuestos. La evidencia
nueva es un régimen de esfuerzo y consistencia de los informes, no otra
recuperación de factibilidad ni una demostración de validez de todas las cotas.
Ausencia de contradicción detectada no equivale a certificado dual.

Fuera de ese régimen reaparecen resultados adversos. Con presolve automático
y 1000 m3, Budget tiene seis cotas y seis cierres contradichos. Sin presolve,
Budget conserva una cota contradicha a 30 m3 y tres a 100 m3. A 1000 y 3000 m3,
también falla los objetivos primales en tres llamadas. El resultado completo,+incluidos estos casos, se conserva en `verified-summary.csv`.

En cinco modelos, la reserva uniforme por redondeo entero agota 10 m3 aun con
la menor IntFeasTol admitida por Gurobi. Son 30 abstenciones, no modelos MILP
inviables. El sexto modelo admite ese presupuesto. A 3000 y 10000 m3 las
exportaciones son idénticas a L2: se conservaron las llamadas prescritas, pero
esos niveles no son representaciones independientes ni dos éxitos adicionales.

## Hipótesis exportada y observación

El contrato utiliza epsilon=1e-6. En las 36 llamadas Budget de la banda auto
30–100 m3, ninguna fila física exportada supera esa hipótesis; el máximo observado
es menor que 1.5e-10. Eso se mide aparte de la selección de factores y de los
residuos en unidades originales. Los objetivos físicos son metas numéricas del
estudio, no tolerancias operativas de UTE.

La comparación cumple el filtro descriptivo preestablecido: al menos cuatro
modelos en dos presupuestos contiguos; aquí son seis en ambos. No constituye
una prueba estadística ni generalización a otra aplicación o solver.

Reproducción sin optimizar:

```bash
python3 exploration/oms-frontier-20261016/independent_check.py
python3 scripts/research/oms_frontier_tables.py
```

En una extracción que no contiene las entregas históricas congeladas, añadir
`--allow-absent-historical` al checker. Los datos y programas de esta campaña
siguen siendo obligatorios y se comprueban por hash. Ese flag solo omite la
auditoría de paquetes históricos ausentes, no la verificación numérica nueva.
