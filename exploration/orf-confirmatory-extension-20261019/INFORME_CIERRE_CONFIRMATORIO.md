# Cierre e interpretación de la campaña confirmatoria ORF

22 de octubre de 2026. Las 3.840 ejecuciones y sus 480 reproducciones independientes terminaron sin fallas de ejecución. Se conservaron 3.816 ejecuciones con calidad evaluable y 24 diagnósticas del modelo infactible.

La campaña **no confirma una aceleración general de Budget-L2 frente a L2** en la métrica primaria registrada. Los intervalos de ambos solvers contienen uno; esto no demuestra equivalencia.

## Comparación primaria completa

| Solver | Pares | Objetivos alcanzados Budget/L2 | PAR2 Budget/L2 [IC 95%] | Tiempo completo [IC 95%] | Trabajo [IC 95%] |
| --- | ---: | ---: | --- | --- | --- |
| gurobi | 477 | 432/423 | 0.9954 [0.9227, 1.0623] | 1.0786 [1.0322, 1.1334] | 1.0384 [0.9842, 1.1035] |
| cplex | 477 | 99/102 | 0.9999 [0.9631, 1.0303] | 1.0048 [0.9896, 1.0197] | 0.9868 [0.9721, 0.9998] |

PAR2 mide la disponibilidad verificada después del solver: usa el tiempo medido en los éxitos y dos veces el límite más preparación si no se alcanza el objetivo. Los cocientes son medias geométricas emparejadas; los intervalos marginales proceden de 100.000 remuestreos de los 40 padres completos, conservando horizontes, semillas y máscara diagnóstica. El costo de referencia es factible y verificado, no un óptimo MILP certificado.

Con Gurobi, el tiempo completo de Budget-L2 es aproximadamente un 7,9 % mayor que el de L2. Los nueve éxitos adicionales no establecen una ventaja general: el intervalo de la diferencia de tasas incluye cero. En CPLEX hay tres éxitos menos y la diferencia también incluye cero. La pequeña reducción de trabajo de CPLEX es secundaria, conserva censura y no constituye una mejora del objetivo primario.

## Precisión física y dominio

Los 3.816 candidatos finales evaluables satisfacen los presupuestos físicos congelados de las filas mapeadas (0,01 MW y 100 m³), bajo las cuatro políticas de cada solver. En esta muestra no se observa recuperación adicional de esos presupuestos por usar el contrato. Son objetivos numéricos del estudio, no tolerancias operativas atribuidas al operador.

El diagnóstico descriptivo posterior distingue esos presupuestos de las cotas exactas del dominio y del objetivo de calidad. En CPLEX, todas las fallas del dominio final se explican por residuos positivos de cotas escritas. El rango global es [1.665e-16, 3.815e-06], en las unidades algebraicas respectivas de cada variable. No se modificó el criterio registrado de cotas exactas ni se recalculó el éxito con otra tolerancia. El diagnóstico usa el vector final; un éxito del objetivo puede corresponder a un incumbente anterior guardado. En CPLEX fallaron las cotas exactas en 379/477 finales Budget-L2 y 378/477 finales L2; este criterio domina la baja tasa de aceptación combinada de ese solver.

## Controles fuertes y cotas

Gurobi L2-NF3 alcanza 454 objetivos frente a 432 de Budget-L2; CPLEX L2-NumEmphasis alcanza 106 frente a 99. Las reducciones de trabajo frente a esos controles se interpretan junto con estas diferencias de éxito y los límites finitos. Las comparaciones secundarias con Base están en el JSON completo: no sustituyen la comparación primaria.

Las políticas escaladas tienen **cero comparaciones de cotas aplicables** en este detector, porque el testigo Base no se certificó factible para el export redondeado. Sus cero contradicciones detectadas no constituyen evidencia de cotas correctas. Base tiene 477 comparaciones aplicables por solver, con 13 contradicciones detectadas en CPLEX y dos en Gurobi.

## Alcance y uso editorial

Simple produce los mismos exports con L2 y Budget-L2. Los padres proceden de recombinaciones históricas con exposición previa documentada; el remuestreo no los convierte en nuevas observaciones operativas independientes. Las tres formulaciones siguen perteneciendo al despacho hidroeléctrico.

Esta campaña aporta una validación reproducible de alcance y límites. La afirmación defendible conserva el foco en especificación explícita de precisión, selección contractual y verificación. La evidencia nueva no justifica ampliar una afirmación de superioridad computacional general.

Si se incorpora al artículo, presentar un resumen breve de la comparación primaria con los éxitos y los intervalos, y desarrollar los estratos y diagnósticos en el suplemento. Incluir también los resultados nulos y desfavorables. El manuscrito y la versión de envío permanecen congelados durante este cierre separado.

## Evidencia de cierre

La verificación estadística independiente reprodujo 48 comparaciones y 80 intervalos. Las auditorías de ejecución abarcan 39,265 vectores, 13,387 auditorías completas y 477 verificaciones de referencia. El archivo sellado inventaría 37,298 archivos y 6,801,485,096 bytes.

Los hashes de las fuentes, datos tabulados, 480 informes y prueba estadística se comprobaron en la copia local. La comprobación local de todos los registros voluminosos se conserva separada del control estadístico realizado en el clúster.

Fuentes: `CONFIRMATION_ANALYSIS.json`, `CONFIRMATION_EXECUTION_REPORT.json`, `CONFIRMATION_ANALYSIS_REPLAY.json`, `CONFIRMATION_RAW_MANIFEST.json` y `CONFIRMATION_FINAL_DIAGNOSTICS.json`. No se ejecutaron nuevos optimizadores.
