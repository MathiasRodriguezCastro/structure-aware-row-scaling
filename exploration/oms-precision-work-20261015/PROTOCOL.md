# Frontera empírica precisión–trabajo, con calidad común

Estudio independiente del paper OMS v1.3.5 y de los ocho paquetes de investigación
ya cerrados. Protocolo fijado antes de sus nuevas resoluciones. No se cambia el
generador ni se reutilizan soluciones como starts.

## Pregunta nueva

¿Los contratos añaden puntos útiles a una frontera precisión/trabajo frente a
controles competitivos, cuando se exige también calidad comparable? Los ensayos
anteriores estudiaron una precisión a tiempo fijo, o calidad final. Este ensayo
conserva la secuencia completa de candidatos y mide el trabajo hasta cumplir
simultáneamente precisión y un objetivo común. Una parada numérica incorrecta no
se considera éxito por ser rápida.

Tres modelos de la confirmación física sin inversión de demanda, posiciones
1,3,6 de su lista: instance001, instance022, instance046. Son casos conocidos,
no validación en familias nuevas. Se conservan las exportaciones Base.lp ya
archivadas, 360 períodos e integralidad original. Interpretación: sus literales
como binary64. No se vuelve a generar con un ejecutable que pudo cambiar.

## Referencias y criterios

Antes del MILP, obtener una referencia racional factible por modelo, fijando el
patrón de un testigo GM ya archivado y resolviendo el LP original Base. Se comprueba
todo con aritmética racional; si no se obtiene, detener preparación y conservar
el fallo. No es referencia óptima. Umbral común Ccap=Uref+0.01 max(1,|Uref|), con
datos racionales; referencia y adquisición son información offline, no un método
que descubre ese objetivo gratuitamente. Sus puntos nunca entran en los MILP.

Tres precisiones autorizadas, sin afinarlas: exigente (0.01 MW,100 m3), referencia
(0.1 MW,1000 m3), permisiva (1 MW,10000 m3). Incluyen identidades de potencia,
envolventes, balances de agua y activaciones por volumen. Las unidades se
convierten por coeficientes originales. Son objetivos numéricos, no estándares.

Punto candidato redondeado a enteros exactos: comprobar todas las filas físicas,
cotas (presupuesto absoluto 1e-6), y otras filas (1e-8 max(1,|RHS|), presupuesto
algebraico auxiliar explícito). La condición de calidad usa el costo original
evaluado exactamente y C<=Ccap. No se deduce factibilidad exacta, respaldo del
costo ni optimalidad de satisfacer esos presupuestos.

Guardar TODOS los eventos MIPSOL, incluso los que no mejoran el incumbente, y
el punto final. Suprimir candidatos solo por costo perdería puntos de mejor
precisión. Primera llegada por trabajo/runtime registrados, sin parar o cambiar
el solver al observarla. El callback solo captura datos; la verificación es
posterior. El costo de captura se registra y entra en el tiempo del optimizador.

## Factores y controles

Potencias de dos, productos coeficiente/RHS exactamente proporcionales,
ventana [1e-9,1e9], sin banda identidad, sin escalado de columnas. Igual selector
del factor más próximo en logaritmos dentro del conjunto admisible.

1. Base: identidad; tolerancias primal 1e-6 y entera 1e-9.
2. Tight: Base, también primal 1e-9.
3. GM: centrado geométrico de extremos, diádico.
4. Ruiz: cuatro medias iteraciones de norma infinito, columnas fijas en uno.
5. L2: norma euclídea, diádico.
6. NumericFocus: L2 con NumericFocus=3.
7–9. Budget-Demanding/Reference/Permissive: mismo candidato L2, proyectado además
en alpha >= epsilon/(delta-E), epsilon=1e-6, E=1e-9 sum_enteros |aij|. Reservas
y extremos se computan racionalmente. Si delta<=E o falta factor exacto,
abstenerse y declarar incompatibilidad. Exportación diádica elimina la reserva
de redondeo de productos, no el error interno del solver.
10. GCD: división por GCD y piso del RHS solo en desigualdades de coeficientes
enteros, variables todas enteras; igualdades solo si la división conserva el RHS.
Si todas esas filas ya tienen GCD=1/RHS entero, es Base y se deduplica. No se
aplica piso del RHS a una fila que contiene variables continuas.

Todos los controles salvo Tight/NumericFocus comparten parámetros. IntFeasTol
1e-9 en todos aísla factores y da un control entero fuerte. Gurobi 13.0.2,
Threads=4, Presolve=ScaleFlag=-1, IntegralityFocus=1, MIPGap=.001,
TimeLimit=15 s, WorkLimit=16, semillas nuevas 401,409,419. Orden fijo permutado
con semilla 20261015. 90 brazos; matrices/parámetros idénticos se resuelven una
vez por semilla y sus alias se explicitan. No se repiten semillas/casos ni se
amplían límites después de observar. Resoluciones secuenciales.

Se cronometran selección de factores, construcción, optimización/captura,
persistencia y verificación. La selección se repite realmente por corrida.
Trabajo al objetivo y costo de verificación se reportan separados: no se
equiparan unidades de trabajo con tiempo total ni se llama frontera óptima
universal al conjunto de políticas ensayadas. Primera llegada medida retrospectiva,
no un controlador online ya evaluado. No se suman costos de modelos distintos.

## Respaldo exacto posterior

Tomar la primera llegada numérica de cada brazo/escenario. Deduplicar por patrón
entero y modelo; intentar UN LP racional de mínimo costo por patrón (SoPlex,
5 s, watchdog 8 s), con todas las filas y cotas Base originales. Mantener desconocidos,
inviables y errores. Costo fuera de la frontera nativa. No buscar otra semilla
o segundo patrón favorable si la primera llegada no queda respaldada.

Un testigo primal con costo U<=Ccap respalda que los mismos enteros admiten la
calidad pedida; para respaldo del costo nominal C exigir además
U<=C+0.01 max(1,|U|). Si un dual exacto prueba mínimo>Ccap se rechaza la calidad.
Si no hay prueba, queda desconocida. Ninguno certifica optimalidad MILP global.
Se publican frontera numérica y respaldo por separado, para no confundirlos ni
atribuir reparación/certificación gratuita al escalamiento.

## Decisión

Una mejora solo en L2, igualada por Base/Tight/GM/Ruiz/NumericFocus/GCD, no basta.
La precisión requiere medir residuos observados, no solo cotas contractuales.
Una ventaja en este banco retrospectivo sigue necesitando transferencia antes
de incorporarse como contribución al paper. Si los controles dominan o no hay
ventaja clara, cerrar esta pregunta y documentar por qué; conservar OMS.

Documentación primaria consultada 2026-10-15:
[MIPSOL](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/callbacks.html),
[numerics](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/numeric_parameters.html),
[tolerancias](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html)
y [SoPlex exacto](https://soplex.zib.de/doc/html/EXACT.php).
