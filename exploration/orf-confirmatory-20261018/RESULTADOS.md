# Validación prospectiva de Budget-L2 para ORF

Diseño fijado antes de resolver; inicio 18 y cierre 19 de octubre de 2026.
24 escenarios nuevos, ocho por horizonte de 24, 72 y 168 horas; tres semillas
por escenario y cinco políticas: 360 MIP, todos conservados. No se modificaron
el generador ni la política Budget-L2. Los escenarios perturban ventanas de
seis entradas conocidas: son nuevos parámetros y tamaños, no datos de una
aplicación independiente ni un test fuera de la familia del despacho.

## Precisión y contradicciones detectadas

| Política | Presupuestos | B/G | Hipótesis exportada |
|---|---:|---:|---:|
| Base | 72/72 | 0/0 | 70/72 |
| Base-tight | 72/72 | 0/0 | 72/72 |
| L2 | 72/72 | 7/6 | 72/72 |
| L2-NF3 | 72/72 | 0/0 | 72/72 |
| Budget-L2 | 72/72 | 1/0 | 72/72 |

Todos los puntos cumplen los presupuestos, antes y después de redondear enteros.
B/G son contradicciones de cota/cierre frente a testigos racionales de la
representación efectivamente resuelta; G usa el criterio histórico del 1%.
No son certificados de todas las cotas restantes. Base tiene dos puntos que
exceden ligeramente la hipótesis de residuo exportado 1e-6, aunque cumplen
los presupuestos originales; la tolerancia nominal no es esa hipótesis.

En new-h072-08, semilla 101, Budget-L2 devuelve una cota −531914,2655652602.
El testigo exactamente factible de su exportación cuesta −534369,9691107974:
la cota queda refutada por 2455,7035455372 unidades. Su cumplimiento primal
no permite certificar esa cota. No se vuelve a resolver para eliminar el caso.

## Comparación emparejada

| Control | Trabajo B/C | Tiempo completo B/C | Pares sin contradicciones B/C | Trabajo filtrado | Tiempo filtrado | Mayor deterioro candidato |
|---|---:|---:|---:|---:|---:|---:|
| Base | 0.422 | 0.797 | 71/72 | 0.419 | 0.796 | 1.020% |
| Base-tight | 0.170 | 0.643 | 71/72 | 0.168 | 0.641 | 1.020% |
| L2 | 0.931 | 0.996 | 64/72 | 0.971 | 1.023 | 0.778% |
| L2-NF3 | 0.476 | 1.031 | 71/72 | 0.472 | 1.028 | 1.020% |

Son medias geométricas emparejadas; los 72 pares incluyen tres semillas de
24 escenarios, no 72 modelos independientes. El filtrado es un resumen
descriptivo adicional: retiene pares completados, con presupuestos satisfechos
y sin contradicción detectada en ninguna rama. No demuestra optimalidad ni
elimina los casos adversos del informe completo. Los tiempos incluyen
generación, selección, exportación, importación, verificación y persistencia,
en procesos nuevos intercalados y una máquina compartida.

**Resultado:** el menor trabajo frente a Base reaparece en escenarios nuevos.
El aporte incremental frente a L2 es más limitado: bajan las contradicciones
detectadas de siete a una, pero el trabajo solo baja 6,9% y el tiempo completo
casi no cambia. Al filtrar contradicciones, la razón de trabajo es 0,971 y
la temporal 1,023. NF3 no presenta contradicciones y tarda algo menos que
Budget-L2 en el ciclo completo. El peor costo candidato de Budget-L2 empeora
1,020% frente a Base/Base-tight; no se puede repetir para esta muestra la
afirmación de deterioro inferior a 0,1% del experimento dirigido anterior.

## Intervención y referencias racionales

El contrato cambia 8,448 factores en las 24 instancias, siempre en activación.
Es el 14,286% de las filas por modelo. La mayor razón Budget/L2 por modelo
está entre 8,242 y 10,694. No se detectan incompatibilidades. Los factores
identifican la intervención, sin demostrar el mecanismo interno del solver.

Se verifican 17/24 cotas LP globales y 72/72 testigos enteros de las tres
representaciones por modelo. 12 referencias Base quedan certificadas al 1%;
ninguna igualdad U=L certifica un óptimo MILP exacto en esta nueva muestra.
Los otros siete LP globales terminan con estado desconocido de SoPlex y
sin un certificado utilizable; no agotaron necesariamente los 30 segundos.
Las 24 cotas superiores Base están disponibles. Son referencias reparadas,
no certificados de todos los candidatos flotantes de las comparaciones.
Los 96 intentos racionales cuestan 50.90 s adicionales,
sin incluirlos dentro de los tiempos MIP comparados.

Como indicador descriptivo adicional, PAR10 asigna 1200 s a una salida sin
candidato, incompleta, fuera de presupuesto, con contradicción o sin testigo
para el contraste. No se presenta como métrica prefijada en el protocolo.
Las medias en segundos son: Base: 1.860, Base-tight: 2.431, L2: 117.623, L2-NF3: 1.095, Budget-L2: 17.696.


## Confirmación con trazas nativas completas

La auditoría detectó que OutputFlag=0 había silenciado las trazas nativas
de la primera campaña. Se conservaron todos sus puntos, resultados API y
logs de cabecera, y se registró LOGGING_AMENDMENT.json antes de repetir
las 360 asignaciones completas con OutputFlag=1. No se cambiaron modelos,
política ni parámetros de optimización. Son 720 MIP totales, no 48 modelos.
La confirmación conserva exactamente 360/360 puntos,
360/360 valores de trabajo y 360/360 conjuntos de endpoints.
Se verifican racionalmente todas las soluciones nuevas y se reutilizan
los testigos de las mismas exportaciones, sin nuevas llamadas LP.
Las contradicciones originales no se eliminan. Tiempos completos de la
confirmación, por separado:

| Control | Trabajo B/C | Tiempo completo B/C |
|---|---:|---:|
| Base | 0.422 | 0.787 |
| Base-tight | 0.170 | 0.637 |
| L2 | 0.931 | 0.986 |
| L2-NF3 | 0.476 | 1.008 |

`logging-confirmation/verified-replication.csv` muestra cada cotejo y
`logging-confirmation/verified-runs.csv` retiene las nuevas verificaciones.
`verified-model-comparisons.csv` cruza por modelo la intervención, esfuerzo,
residuos, contradicciones y preparación adicional de la campaña principal.

## Incorporación al artículo

Se añade una subsección breve y los controles por horizonte al suplemento.
El resumen conserva el resultado previo de seis modelos y añade el límite
prospectivo. No se presenta superioridad general frente a L2 o NF3.
La cota elemental de errores de exportación se documenta aparte y se prueba
en 20000 verificaciones racionales, sin cambiar la política experimental.

## Reproducción sin licencia comercial

Extraer el archivo científico heredado y superponer el ZIP prospectivo.
Desde esa raíz:

```sh
python3 exploration/orf-confirmatory-20261018/check.py
python3 exploration/orf-confirmatory-20261018/check.py --logging-confirmation
python3 exploration/orf-confirmatory-20261018/check_export_bound.py
```

`verified-runs.csv` conserva cada salida; `verified-pairs.csv`, cada comparación;
`verified-factors.csv`, la intervención; `verified-certificates.csv` y
`verified-intervals.csv`, las garantías y los desconocidos. No se requiere
Gurobi ni SoPlex para comprobar los datos suministrados.
