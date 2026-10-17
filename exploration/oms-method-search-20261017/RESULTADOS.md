# Búsqueda de un método nuevo para MILP con presupuestos de precisión

17 de octubre de 2026. Investigación separada de OMS v1.3.14.

**Conclusión:** se desarrollaron y contrastaron cuatro candidatos, sin restringir
la búsqueda al escalado conjunto. Hay dos propiedades matemáticas implementadas
y verificadas, pero ninguno acredita todavía un método nuevo con una ventaja
práctica propia frente a controles fuertes. No se incorporó nada al manuscrito.

## Qué se investigó y qué decidió el experimento

| Candidato | Resultado comprobado | Decisión |
|---|---|---|
| Cambio mínimo de columnas con contratos | En 27 casos, los 22 compatibles requieren cambio cero; los otros cinco conservan certificados de incompatibilidad | No abre una oportunidad real en este banco |
| Contracción certificada de big-M | 1.753 cotas derivadas y 96 reducciones de 1e17 a aproximadamente 2,27e6; los contratos redondeados siguen incompatibles | La operación clásica sola no basta |
| Escalas de actividades SOS1 elegidas por presupuesto | 54 llamadas; propuesta y SOS-unit cumplen en 12/12 cada una; SOS-unit obtiene mejores objetivos en control30 | No hay ventaja sobre el control convencional |
| Copias enteras redundantes para amplificar precisión | 78 llamadas; tres celdas admisibles y una abstención; presolve elimina todas las copias y produce el mismo modelo con copias continuas | No hay mecanismo propio que sobreviva a presolve automático |

Los 132 llamados nativos de optimización devolvieron puntos y se verificaron
independientemente. Hubo además seis llamadas diagnósticas a presolve, sin
optimizar, repetidas una vez para comprobar su reproducción (12 en total).
Las verificaciones incluyen 3.456 conjuntos de hipótesis SOS y 2.592
conjuntos de hipótesis de amplificación. No se mezclan las semillas entre campañas
para simular una réplica mayor. SUMMARY.csv contiene las 58 agregaciones de tres
semillas; repetir un control frente a dos presupuestos no cuenta como otra llamada.

## La propiedad candidata que se puso a prueba, sin afirmar prioridad

Para z binaria se añade q entera y la igualdad sigma*(Kz-q)=0, con K entero.
La proyección LP y MILP del modelo de partida permanece idéntica. Si las dos
distancias a entero son <=gamma y el residuo de la igualdad es <=epsilon,
la condición K*gamma+epsilon/sigma+gamma<1/2 implica

    |z-round(z)| <= gamma_eff = (gamma+epsilon/sigma)/K.

Este límite permite seleccionar conjuntamente K, sigma y factores de fila para
que epsilon/alpha+|a_z|*gamma_eff<=delta. El selector usa factores diádicos,
exportación exacta y certificados de admisibilidad/incompatibilidad. Se comprobó
por enumeración y mediante el replay racional de los puntos devueltos.

En cinca, el presupuesto 1e-4 admite K=2048 y el presupuesto 1e-8 admite
K=2097152. En control30, el presupuesto 1e-4 admite K entre 2 y 256, mientras
que 1e-8 no admite una representación completa en la ventana declarada.

Eso prueba una propiedad de representación, no utilidad científica adicional.
Las nueve parejas con presolve automático devuelven exactamente el mismo vector
completo y objetivo con q entera o continua. Las matrices, cotas, tipos de variable
y objetivos de los modelos reducidos también coinciden en los tres casos. Las
pequeñas diferencias de trabajo corresponden al procesamiento inicial; el mayor
cociente entero/continuo observado es aproximadamente 1,000001. Con presolve
desactivado tampoco aparece una ventaja consistente: en control30 la mediana
de objetivo con copia entera es 3,16534 frente a 2,66253 con copia continua,
con el mismo tope de trabajo y menor objetivo preferible.

## Por qué el resultado SOS tampoco alcanza

El criterio de escala elimina M del límite condicional de error redondeado:
epsilon/alpha+h*max(gamma_SOS,tau). Sin embargo, elegir h de esa manera no
mejora los objetivos frente a h=1 en el piloto. En control30, a presupuesto 1e-4,
las medianas son 2,36943 y 1,83523; a 1e-8, 5,45573 y 1,83523. En cinca no
aparece una diferencia relevante. Además, 20 conjuntos de hipótesis nominales
fallan en la propuesta de control30 aunque sus puntos redondeados cumplen por
verificación directa. No se confunden ambas formas de evidencia.

SOS1, indicadores y escalado de sus holguras ya existen. SCIP incorpora
`constraints/indicator/scaleslackvar` y utiliza el tamaño de los coeficientes
para escoger la escala. Una búsqueda inicial de literatura no certifica que los
criterios de este estudio sean originales. Una fórmula verificable sin ventaja
sobre aquellos controles no resuelve por sí sola la objeción de novedad para OMS.

## Alcance y reproducibilidad

Los pilotos nuevos utilizan control30-3-2-3 y neos-3421095-cinca, seleccionados por
el diagnóstico previo. Son datos de descubrimiento. Los presupuestos 1e-4 y 1e-8
se aplican exclusivamente a las activaciones y son unidades algebraicas elegidas
para el experimento. Las demás filas y cotas conservan sus presupuestos.
Gurobi 13.0.2, cuatro hilos, WorkLimit=1, TimeLimit=30 s, MIPGap=0.01,
FeasibilityTol=1e-6 e IntFeasTol=1e-9. La campaña SOS usa semillas 151/157/163;
la de copias usa 167/173/179. Muchas corridas útiles terminan por límite de
trabajo. Los objetivos son incumbentes verificados numéricamente, no óptimos
certificados. No se deduce validez de cotas inferiores de los estados del solver.

Se preservan protocolos anteriores a cada campaña, programas, entradas
exportadas, certificados, parámetros, atributos finales y todos los puntos.
OutputFlag=0 dejó solo las cabeceras de los logs nativos; no hay trazas completas
del árbol. Los tiempos de importación/solver/verificación no comprenden toda la
selección y exportación; no se usa ese dato para afirmar mejoras de tiempo total.

Ejecutar `python3 verify_all.py` desde esta carpeta para repetir los controles
sin nuevas optimizaciones. Requiere el repositorio completo, Python y las
dependencias de lectura existentes; no es un suplemento independiente de OMS.
`python3 analyze.py` reconstruye las tablas desde resultados preservados.
`../oms-integer-embedding-20261017/presolve_diagnostic.py` repite el diagnóstico
nativo adicional de presolve. No sobrescribir los pilotos para repetir solves.

Las pruebas completas de los candidatos están en sus archivos THEORY.md,
PROTOCOL.md, RESULTADOS.md y VALIDATION.json. Los documentos y releases de OMS
no fueron modificados. El DOI de Zenodo sigue reservado para el cierre editorial.

## Fuentes primarias consultadas

- [SCIP, implementación de indicadores y escalado de holguras](https://raw.githubusercontent.com/scipopt/scip/master/src/scip/cons_indicator.c).
- [Gurobi, semántica y tolerancias de SOS](https://docs.gurobi.com/projects/optimizer/en/12.0/concepts/modeling/constraints.html).
- [Gurobi, parámetros IntFeasTol y PreSOS1BigM](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html).
- [HiGHS, presolve y agregación de variables enteras](https://github.com/ERGO-Code/HiGHS/blob/master/highs/presolve/HPresolve.cpp).
- [Andersen y Pochet, fortalecimiento de coeficientes](https://research.dial.uclouvain.be/entities/publication/03ea6bfe-7105-4d5c-a48a-47578c173bd1).

Estas fuentes delimitan los ingredientes conocidos; no constituyen una revisión
bibliográfica exhaustiva ni una declaración de prioridad.
