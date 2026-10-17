# Precisión y costo con controles emparejados

16 de octubre de 2026. Extensión cerrada de seis modelos conocidos SG-Ter-Mer,
no una validación externa. Se conservaron las 144 asignaciones del protocolo.
Hubo 145 intentos nativos: 144 resultados terminales y un intento interrumpido
por un reinicio del equipo, preservado y repetido según RESTART_AMENDMENT.md.

**Hallazgo central:** la recuperación primal frente a L2 sigue limitada a
instance046 sin presolve. NumericFocus=3 cumple los presupuestos y no presenta
ninguna de las contradicciones detectadas en sus 36 llamadas. Budget-L2 cumple
los 36 presupuestos, pero mantiene una cota contradicha con presolve automático
y tres sin presolve. Sus cocientes geométricos de Work frente a NumericFocus=3
son 0,361 y 0,227 respectivamente: menor trabajo para el presupuesto primal,
con diferencias pendientes de calidad de las afirmaciones del solver. No se
establece una política de optimización generalmente preferible.

## Resultado completo

Presupuesto exigente: 0,01 MW y 100 m³. «Cumple» verifica las 4.320 filas auditadas
por punto después de redondear las variables enteras. Se guardan también los
residuos sin redondear. No se usa el residuo más cercano a cero como criterio de
superioridad cuando ambos métodos cumplen el presupuesto.

| Presolve | Política | Cumple /18 | Máximo activación (m³) | Cotas contradichas | Finalizaciones contradichas | Límites de tiempo | Media geom. Work | Mediana ciclo completo (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Auto | L2 | 18/18 | 4.768e-07 | 5 | 3 | 0 | 1.59 | 1.944 |
| Auto | Budget-L2 | 18/18 | 0.0001123 | 1 | 0 | 0 | 1.106 | 2.17 |
| Auto | L2-tight | 18/18 | 0 | 5 | 3 | 0 | 1.516 | 1.894 |
| Auto | L2-NF3 | 18/18 | 0 | 0 | 0 | 0 | 3.063 | 2.295 |
| Off | L2 | 15/18 | 4837 | 8 | 8 | 0 | 0.2904 | 1.343 |
| Off | Budget-L2 | 18/18 | 1.478e-05 | 3 | 0 | 0 | 0.6023 | 1.795 |
| Off | L2-tight | 18/18 | 2.384e-07 | 8 | 8 | 0 | 0.2888 | 1.369 |
| Off | L2-NF3 | 18/18 | 0 | 0 | 0 | 0 | 2.648 | 2.22 |

Las cotas se comparan con doce testigos exactamente factibles del archivo nativo
correspondiente, con margen de presentación max(1e-6, 8 ulps). Una finalización
al 1 % se contradice cuando U < C - 0,01|C|. No detectar una contradicción no
certifica ni las cotas ni la optimalidad. Todas las llamadas, incluidas las
finalizaciones contradichas y los límites de tiempo, entran en los resúmenes.

## ¿En cuántos modelos se recupera precisión?

Cada celda indica cumplimiento entre tres semillas, con presolve desactivado.

| Instancia | L2 | Budget-L2 | L2-tight | L2-NF3 |
| --- | ---: | ---: | ---: | ---: |
| instance001 | 3/3 | 3/3 | 3/3 | 3/3 |
| instance005 | 3/3 | 3/3 | 3/3 | 3/3 |
| instance022 | 3/3 | 3/3 | 3/3 | 3/3 |
| instance027 | 3/3 | 3/3 | 3/3 | 3/3 |
| instance031 | 3/3 | 3/3 | 3/3 | 3/3 |
| instance046 | 0/3 | 3/3 | 3/3 | 3/3 |

Modelos con mayor cumplimiento Budget-L2 frente a L2 sin presolve: instance046.

## Comparación de costo al presupuesto común

Los cocientes se calculan por instancia y semilla; nunca se mezclan configuraciones
de presolve. Un cociente menor que uno favorece a Budget-L2 en trabajo. El resumen
condicionado a que ambos cumplan se identifica como tal, con su denominador. No
representa por sí solo eficiencia hasta una calidad objetiva común ni tiempo hasta
el primer incumbente verificable. Los objetivos y todos los pares se suministran.

| Presolve | Control | Cumplen ambos /18 | Recuperaciones Budget | Pérdidas Budget | Cociente Work, todos | Cociente Work, cumplen ambos | Ambos cumplen y sin flags /18 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Auto | L2 | 18/18 | 0 | 0 | 0.6957 | 0.6957 | 13/18 |
| Auto | L2-tight | 18/18 | 0 | 0 | 0.7297 | 0.7297 | 13/18 |
| Auto | L2-NF3 | 18/18 | 0 | 0 | 0.3612 | 0.3612 | 17/18 |
| Off | L2 | 15/18 | 3 | 0 | 2.074 | 1.604 | 10/18 |
| Off | L2-tight | 18/18 | 0 | 0 | 2.085 | 2.085 | 10/18 |
| Off | L2-NF3 | 18/18 | 0 | 0 | 0.2275 | 0.2275 | 15/18 |

## Diseño, costo completo y límites

Instancias 001,005,022,027,031,046; semillas 11,23,47; presolve automático y
desactivado; cuatro políticas. Cada llamada reconstruye el generador C++ original
una vez, sin modificar su código. Los archivos L2 y Budget reproducen por SHA-256
los usados en la investigación anterior; los controles utilizan el mismo archivo L2.
El contrato cambia 1.440 factores por modelo, sobre 10.080 filas y 6.120 variables
(1.440 binarias). Las entradas no contienen la inversión de demanda documentada.

Gurobi 13.0.2, cuatro hilos, 120 s, gap 1 %, ScaleFlag=-1 e IntegralityFocus=0.
L2 y Budget comparten FeasibilityTol=1e-6 e IntFeasTol=2^-28. L2-tight usa 1e-9
en ambas tolerancias; L2-NF3 conserva las tolerancias emparejadas y añade NumericFocus=3.
No hay MIP starts. El orden aleatorio se fijó antes de optimizar. No se ajustaron
parámetros después de observar los resultados ni se ejecutaron nuevos LP de referencia.

Total abarca un proceso Python nuevo: imports, lanzamiento C++, construcción y
exportación Base, metadatos, selección, escritura escalada, lectura e igualdad de
la importación nativa, resolución, extracción, comprobación y persistencia. Las
etapas disjuntas están en verified-runs.csv. Son tiempos de un prototipo en una
máquina compartida, no un benchmark de producción; Work es el indicador principal
del esfuerzo nativo. Compilación y adquisición previa de testigos son costos fuera
de línea; witness-revalidation-timing.json registra la revalidación actual separada.
Los tiempos además abarcan un reinicio: se conservaron las 37 llamadas completas
anteriores y se repitió únicamente el intento que perdió su proceso. Ese intento
sin resultado final se identifica como fallo externo de entrega, no como réplica
completa ni como fallo atribuible al solver. No se deduce un resultado de sus logs.

Este experimento evalúa la solución terminal del criterio nativo de parada. No
construye una frontera completa sobre diferentes presupuestos ni mide tiempo hasta
el primer incumbente que cumpla. Los menores tiempos de llamadas con cotas o gaps
contradichos no cuentan como optimizaciones exitosas equivalentes.

## Reproducción y decisión

`python3 exploration/oms-matched-accuracy-20261016/independent_check.py` revalida
los doce testigos completos y los residuos físicos con fracciones exactas de los
datos binary64. No importa Gurobi ni llama a un optimizador. `write_report.py`
regenera esta nota y las tablas. `study.py prepare/run` corresponde a la campaña
nativa, requiere licencia y rechaza sobrescribir el diseño existente.

La mejora se evalúa dentro de una sola familia de seis modelos ya conocidos; las
semillas también habían sido utilizadas. No son una muestra externa. Cumplir los
presupuestos auditados no constituye una certificación integral de factibilidad
u optimalidad. Un resultado favorable con presolve desactivado no demuestra una
ventaja con los ajustes predeterminados. Se cierra esta cohorte sin abrir más
barridos en función del resultado.
