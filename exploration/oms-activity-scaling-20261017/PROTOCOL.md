# Escalado de actividades con presupuestos: piloto de descubrimiento

17-10-2026. Documento anterior a las nuevas llamadas al optimizador. Se conoce
el diagnóstico de las dos exploraciones de hoy: cambiar solo columnas continuas
no resuelve el obstáculo entero y contraer M mediante propagación tampoco
restaura el contrato redondeado. No se modifican el paper ni sus releases.

## Pregunta y antecedentes

¿Elegir la escala de una actividad SOS1 mediante el presupuesto original aporta
algo frente a escalas convencionales de la misma reformulación? Ni la sustitución
de big-M por indicadores/SOS1 ni el escalado de sus holguras son nuevos. SCIP
incluye `constraints/indicator/scaleslackvar` y utiliza la media de los valores
absolutos de los coeficientes. La posible contribución que se contrasta es la
selección verificable de escalas que controla simultáneamente la tolerancia de
fila, la tolerancia SOS y la de cotas, junto con su utilidad computacional.
Una búsqueda inicial de antecedentes no prueba prioridad.

## Transformación

Para g(x_cont)<=M*z, z binaria, usar una contracción certificada M'<=M cuando
exista. Introducir y>=0, w=1-z, g(x_cont)-h*y<=0, y<=M'/h y SOS1(w,y).
Compartir w entre filas de una misma binaria. h es una potencia de dos. Todas las
políticas SOS usan exactamente el mismo M' y la misma estructura. La equivalencia
es de la proyección de puntos enteros; no se afirma equivalencia LP.

Si |z-round(z)|<=gamma, |w+z-1|<=epsilon_c y a lo sumo un miembro de SOS1
supera gamma_s en valor absoluto, la condición 1-gamma-epsilon_c>gamma_s permite
deducir, para la fila original tras redondear z,

    violacion <= epsilon/alpha + h*max(gamma_s,tau).

tau limita el exceso de la cota superior de y. Todas son hipótesis que se
verifican sobre el punto devuelto, no promesas derivadas de parámetros nominales.
El selector busca el mayor h diádico admisible, con exportación exacta, cota
auxiliar <=1e19, coeficientes en [1e-9,1e9] y la desigualdad anterior <=delta.
Luego elige el factor de fila diádico más próximo a L2 en su intervalo admisible.

## Banco y diseño cerrado del piloto

Dos modelos externos ya identificados, control30-3-2-3 y neos-3421095-cinca;
son datos de descubrimiento, no una validación independiente de la selección.
Se transforman las 96 activaciones críticas previamente detectadas en cada uno.
Presupuestos de esas filas: 1e-4 y 1e-8 unidades algebraicas. Los demás presupuestos
y las cotas originales se mantienen. Los valores no son estándares operativos.

Seis políticas: Linear-L2; Linear-NF3; Contracted-L2; SOS-unit (h=1);
SOS-range (h=2^ceil(log2(M'))); Activity-budget (h contractual máximo).
Para aislar las activaciones, las filas no seleccionadas comparten factores
Budget-dyadic-L2 y se conservan idénticas en todos los brazos. Los tres controles
lineales no dependen del presupuesto de las activaciones y se resuelven una vez
por semilla; se verifican después frente a ambos presupuestos.

Gurobi nativo, semillas nuevas 151,157,163; cuatro hilos, TimeLimit=30 s,
WorkLimit=1, MIPGap=0.01, FeasibilityTol=1e-6, IntFeasTol=1e-9,
presolve automático, PreSOS1BigM=0 en todos los brazos para conservar SOS1.
NumericFocus=3 exclusivamente en Linear-NF3. Máximo 54 llamadas, secuenciales.
Se guarda orden intercalado de políticas, modelo exportado, parámetros, log,
punto completo, trabajo, tiempo de preparación, solver y verificación.
No se sustituyen ausencias de incumbente por puntos factibles.

## Verificación y decisión

Antes de resolver: comprobar exportación exacta, selector por enumeración pequeña,
equivalencia proyectada en ejemplos enumerables y la desigualdad racional.
Después: recalcular con fracciones las filas y cotas originales, antes/después de
redondear, las hipótesis SOS/complemento/enlace/cota y los objetivos originales.
No se certifica optimalidad ni se consideran válidas cotas solo por venir del solver.
Se retienen ausencias de solución, fallos de hipótesis y resultados desfavorables.

Si solo mejora frente a big-M pero no frente a SOS convencional, no basta para
reclamar un método científicamente superior. Si no consigue soluciones útiles,
se cierra esta variante. Una señal favorable exige otra validación antes de
incorporar nada a OMS. No habrá ajuste de h o parámetros a partir del resultado.

## Fuentes primarias consultadas

- SCIP, `cons_indicator.c`, construcción de holguras y parámetro scaleslackvar:
  https://raw.githubusercontent.com/scipopt/scip/master/src/scip/cons_indicator.c
- Gurobi, significado de SOS1 y tolerancia de cero:
  https://docs.gurobi.com/projects/optimizer/en/12.0/concepts/modeling/constraints.html
- Gurobi, PreSOS1BigM e IntFeasTol:
  https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html
