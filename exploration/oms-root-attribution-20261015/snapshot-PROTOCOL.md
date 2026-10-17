# Atribución del efecto de escalamiento al acceso a un incumbente

## Encaje en OMS

La pregunta pendiente de la contribución A es qué parte del beneficio operativo
del escalamiento externo sobrevive al proporcionar el mismo incumbente inicial.
Se examina una interacción del software de escalamiento y búsqueda MIP, sin
proponer cortes, DW, un predictor o un nuevo precondicionador.
La contribución B mantiene sus controles de precisión y sus límites actuales.
Este ensayo no atribuye una ventaja nueva a los metadatos del generador.

Se eligen tres casos conocidos del estudio de mecanismos: instance001 y
instance003, donde GM ayudó, e instance042, donde aumentó el trabajo. La elección
es retrospectiva, para diagnóstico, no validación fuera de muestra. El indicio
observacional de 001 es una cota LP raíz igual al nivel impreso y una diferencia
grande de incumbentes antes de ramificar. Eso no prueba causalidad interna.

## Protocolo fijado antes de nuevas llamadas

Por modelo se toma exclusivamente el patrón entero del GM archivado con semilla
307 y mecanismos internos normales. Se redondean sus enteros y se intenta una
continuación LP exacta con SoPlex, límite 15 s. Si no se obtiene un testigo
racional factible, ese caso no entra en la comparación con incumbente común;
se conserva el resultado sin buscar otro patrón sustituto.

Un testigo exacto no certifica el óptimo MILP. Se convierte a binary64 para
Start, reteniendo el testigo racional y las verificaciones originales/exportadas.
El costo de adquisición se declara aparte: no se lo ofrece como algoritmo
gratuito. La API Start no garantiza aceptación. Se comprueba el log de carga,
el objetivo y el patrón del candidato guardado; comparaciones con rechazo se
informan separadamente y no prueban neutralización del incumbente.

Tres semillas nuevas: 503, 509, 521. Base/GM x Cold/CommonStart: 12 brazos por
caso, máximo 36 MILP. Orden secuencial aleatorizado con semilla 20261015.
Gurobi 13.0.2, Threads=4, TimeLimit=12, WorkLimit=12, MIPGap=.001,
FeasibilityTol=1e-6, IntFeasTol=1e-5, IntegralityFocus=0, Presolve=-1,
ScaleFlag=-1. Se mantienen las políticas exactas congeladas del estudio padre.
No se cambian variables, dominios, objetivo, coeficientes o presupuestos.

Se guardan todos los candidatos MIPSOL, progresión de cotas/incumbentes y logs.
Se informa por caso y semilla: trabajo y estado nativo, calidad del incumbente,
aceptación del Start, relajación raíz impresa, cortes reportados y progreso.
El trabajo de callbacks no es tiempo del algoritmo de reparación. No se
confunden cortes impresos con acceso a sus coeficientes ni el presolve de la API
con la matriz interna usada por optimize.

Después se fija una cola de todos los patrones finales únicos y se intenta
una continuación exacta con límite 5 s, sin sustituciones. Se verifica si el
costo nominal está respaldado por el mínimo del mismo patrón. Esa cota no es
una cota MILP global. El testigo común sí puede refutar cotas globales mayores
que su costo. La ausencia de contradicción no certifica optimalidad.

## Lectura y abandono

Si el contraste Base/GM disminuye al aceptar ambos el mismo Start, es evidencia
de dependencia respecto del acceso al incumbente, no de que toda la diferencia
se deba a una heurística identificada. Si persiste, la explicación requiere
otros mecanismos. Si el efecto no es consistente, se cierra el diagnóstico sin
otra campaña ni tablas para el paper. Un resultado positivo solo se considerará
para OMS si explica una afirmación existente y puede comunicarse brevemente.

El manuscrito, la entrega v1.3.5 y los once paquetes cerrados se preservan por
hashes. Datos conocidos, una familia y límites breves: no se extrapola a
superioridad general ni se entrena un selector con estos resultados.
