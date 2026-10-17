# IntegralityFocus y costo completo: resultado para OMS

15 de octubre de 2026. Un caso retrospectivo, no una validación externa.
Aclaración editorial de agregación: 16 de octubre de 2026.

**Resultado útil:** IF1 no elimina la violación de L2 en este contraste. En los
seis pares IF0/IF1 coinciden exactamente los puntos guardados, los objetivos,
las cotas y las unidades de trabajo. Todas las coordenadas enteras devueltas son
exactamente integrales, por lo que este resultado no muestra un error de redondeo
entero corregido por IF1. Es un control negativo pertinente, no una afirmación de
inutilidad general del parámetro.

## Precisión y afirmaciones del solver

| Política | Llamadas | Cumple presupuestos | Máximo volumen, m³ | Cotas contradichas | Finalizaciones contradichas | Mediana Work |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L2-window, IF0 | 3 | 0/3 | 4837.33807 | 3/3 | 3/3 | 0.596966 |
| L2-window, IF1 | 3 | 0/3 | 4837.33807 | 3/3 | 3/3 | 0.596966 |
| Budget-L2, IF0 | 3 | 3/3 | 1.47819519e-05 | 2/3 | 0/3 | 4.975495 |
| Budget-L2, IF1 | 3 | 3/3 | 1.47819519e-05 | 2/3 | 0/3 | 4.975495 |

El presupuesto exigente es 100 m³ y 0,01 MW. L2 viola la activación en
4.837,338 m³; Budget-L2 la limita a 1,4782e-5 m³. Budget mantiene dos cotas
contradichas de tres, aunque ninguna finalización al 1 % queda contradicha por
estos testigos. Ausencia de contradicción no certifica cotas ni optimalidad.
L2 presenta tres cotas y tres finalizaciones contradichas. No se comparan como
optimizaciones exitosas equivalentes por el solo hecho de terminar rápido.

**4,485 y 4,975 son compatibles.** Las unidades de trabajo Budget-L2 por semilla
11/23/47 son 3,6054776613; 4,9754950464; 5,0281587478, iguales a las de la campaña
anterior sin presolve. Su media geométrica es 4,4847271866 (4,485 en Tabla 11 histórica de v1.3.8 y
Tabla S12); su mediana es 4,9754950464 (4,975 en esta nota y Tabla S15).
La diferencia procede del resumen estadístico, sin cambiar configuraciones ni datos.

## Costo completo medido

Medianas, segundos; tres llamadas por celda, sin amortizar construcción.

| Política | Generar | Seleccionar/exportar | Importar/cotejar | Resolver | Verificar | Total del proceso |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L2-window, IF0 | 0.115 | 0.428 | 0.114 | 0.639 | 0.269 | 2.070 |
| L2-window, IF1 | 0.115 | 0.367 | 0.099 | 0.533 | 0.228 | 1.768 |
| Budget-L2, IF0 | 0.065 | 0.514 | 0.097 | 4.788 | 0.237 | 6.231 |
| Budget-L2, IF1 | 0.064 | 0.528 | 0.099 | 4.955 | 0.239 | 6.380 |

Generar incluye lanzamiento C++, lectura de entrada, construcción única y escritura
Base. Total mide un proceso Python nuevo e incluye también imports, lectura de
modelos, metadatos, comprobaciones de integridad, extracción y persistencia. Esas
etapas adicionales están desglosadas en verified-runs.csv: las columnas visibles
no cubren por sí solas todo el total, y las medianas no tienen por qué sumar.
El costo es del prototipo sobre una máquina compartida; no establece una ventaja
computacional general ni un costo de producción. Compilación y adquisición de
testigos son costos fuera de línea. Se conserva el tiempo de revalidación de dos
testigos en pre-incorporation-validation.json, separado del ciclo.

## Diseño, enmienda y comprobación

instance046, generador C++ original; 6.120 variables, 10.080 filas y 1.440 binarias.
Gurobi 13.0.2, cuatro hilos, 120 s, gap 1 %, presolve desactivado y escalado interno
automático; tolerancias primal 1e-6 y entera 2^-28; semillas 11,23,47. L2/Budget
reproducen exactamente los archivos históricos antes de cada llamada. No hay MIP
starts ni cambios de formulación, objetivo, cotas o dominios.

Doce tratamientos de la pasada principal. Una primera pasada completa se conserva
en first-pass/. Después se corrigió una copia repetida de vectores en el cotejo de
importación y se repitieron todos los tratamientos. Hubo 24 llamadas MILP nuevas,
sin nuevos LP de referencia. Los resultados nativos y puntos de ambas pasadas
coinciden exactamente. No se cuenta la repetición instrumental como otra muestra.

El checker separado no importa study.py ni Gurobi, y no optimiza. Revalida los dos
testigos completos con aritmética racional sobre 20.160 filas, 12.240 variables y
2.880 dominios enteros; comprueba 103.680 pares fila/punto físicos antes/después
de redondear. Los certificados corresponden al mismo hash de modelo importado.
Cuatro tests comprueban cancelación exacta, activaciones al redondear y refutaciones
de cotas/gap con objetivos negativos y márgenes de presentación.

## Decisión editorial

El control IF1 cierra una objeción concreta y justifica una frase en 7.9, con los
resultados y costos en el suplemento. No crea una tercera contribución. El abstract
y la introducción se conservan; el cierre editorial v1.3.8 también simplifica la carta.
No se amplía la campaña de mecanismos ni
se reclama generalidad a partir de un solo caso.
