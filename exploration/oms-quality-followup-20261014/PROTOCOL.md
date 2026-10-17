# Calidad tras reparar e informes de cotas: diseño prospectivo

Exploración independiente del envío OMS v1.3.5 y de los dos estudios anteriores.
No modifica ninguno de sus códigos, datos o paquetes. Se conserva evidencia
adversa. El protocolo y fuentes se congelan antes de nuevas llamadas MILP.

## Hipótesis

1. Una reparación rápida puede inicializar una segunda resolución y mejorar la
   calidad del objetivo respecto de entregar solamente el LP reparado.
2. Ese ciclo debe compararse con inicios en frío igualmente robustos y con la
   misma asignación total de tiempo MILP. No basta mejorar la precisión.
3. Testigos factibles exactos permiten vetar informes de cotas incompatibles,
   pero no certificar cotas no contradichas ni optimalidad global.

## Selección y controles

Se retienen los tres MIPLIB ya seleccionados: control30-3-2-3,
neos-3421095-cinca y ta1-UUM. La elección sigue todos los casos numéricos del
piloto, no solamente los favorables. Se excluye STN de esta pregunta porque en
los cuatro horizontes anteriores todas las alternativas verificaron precisión.
No son nuevas familias. Semillas nuevas 31 y 47; Gurobi 13.0.2, cuatro hilos,
gap 1 %, escalado interno y presolve automáticos salvo el control indicado.

Ocho tratamientos, cada uno en los seis pares modelo/semilla:

1. Cold-tight: Base, FeasibilityTol e IntFeasTol 1e-9, un MILP.
2. Cold-IF1: Base, tolerancias ordinarias e IntegralityFocus 1, un MILP.
3. Base-warm-tight: Base ordinario hasta 1 s, comprobar/reparar, luego Base tight.
4. Base-warm-IF1: mismo inicio, luego Base con IntegralityFocus 1.
5. L2-warm-IF1: L2 diádico ordinario hasta 1 s, luego la misma representación IF1.
6. Budget-warm-IF1: proyección contractual diádica hasta 1 s, luego IF1.
   Un intervalo incompatible produce abstención sin resolver ninguna fase.
7. Cold-tight-presolve-off: idéntico a Cold-tight con Presolve=0; es un control
   de mecanismo para cotas, no una búsqueda de parámetros después de resultados.
8. Witness-warm-tight: Base tight recibe un testigo exacto disponible antes de
   esta confirmación, también convertido y verificado para entrega. Es un
   control diagnóstico con información previa, no un método de velocidad nuevo.
   Preparar ese testigo se declara por separado y no se atribuye gratis a un
   algoritmo general. Control y ta reutilizan certificados anteriores; cinca
   usa un LP exacto de un punto previo, excluido de los resultados prospectivos.

Total: 48 asignaciones, orden aleatorio fijado con semilla 20261016. Todas las
llamadas son secuenciales. No se reajustan políticas tras observar semillas nuevas.
Se reutilizan factores y presupuestos del estudio anterior: MIPLIB
delta_r=1e-4 max(1,|RHS|), cotas 1e-4, dominios enteros exactos. Son unidades
algebraicas experimentales, no presupuestos físicos validados. Contratos cubren
el punto crudo; toda entrega entera se verifica por separado.

## Tiempo, reparación y retención

La suma de límites solicitados a MILP es como máximo 15 s por tratamiento:
en dos fases, la primera recibe hasta 1 s y la segunda hasta 14 s, con reserva
para el ciclo global. El tiempo no utilizado por la primera no se reasigna.
Referencia global
20 s incluyendo selección/exportación, importación/cotejo, fases MILP,
verificación, reparación y auditoría. Es una referencia operativa, no tiempo real.
Se registran límites solicitados y tiempos observados; overhead puede excederlos.
La construcción compartida inicial se cronometrará y se informará aparte.

Cada punto retornado se redondea en variables enteras y comprueba en todas las
filas, cotas y dominios del modelo original. Si falla, LP con enteros fijados,
HiGHS hasta 0,5 s y, si no recupera entrega, SoPlex exacto hasta 1 s restante.
Todos los LP escriben datos/certificados originales; ninguno fija enteros de la
fase principal. Solo el LP de reparación fija su asignación.

Se conservan todos los candidatos que pasan. La fase robusta recibe el mejor
candidato verificado como Start completo, si existe. Si no existe, se ejecuta
en frío y se declara ese resultado. La salida es el candidato de menor objetivo
original, calculado con Fraction, entre los verificados disponibles. Una fase
posterior no puede hacer perder el punto ya comprobado ni se hereda su gap.

Al terminar, si queda tiempo, un único LP exacto de hasta 1 s intenta convertir
la mejor asignación en testigo factible exacto; no se reclama optimalidad de ese
LP sin certificado dual. Una conversión también verificada puede competir como
candidato. La misma auditoría se aplica a todos los tratamientos. Si no termina
o falla, se conserva el punto numérico y se informa ausencia de testigo exacto.
Los archivos auxiliares se incluyen en su etapa; persistencia final se mide aparte.

## Cotas y endpoints

Los testigos exactos previos, disponibles antes de resolver, se usan para una
comprobación online separada de cotas después de cada fase. Se verifica su modelo
y factibilidad exacta, y se veta una cota inferior B cuando B>U+max(1e-6,8 ulp(B)).
La ausencia de contradicción deja el estado no verificado. El testigo racional
puede ser válido para esta comparación aunque su entrega binary64 no lo sea.
Los nuevos testigos se pueden usar para un screening conjunto posterior, con
esa disponibilidad posterior explícita. No se llama chequeo online al conjunto.

Resultados primarios: entrega verificada, objetivo entregado y costo completo,
comparando cada warm-IF1 con Cold-IF1 y warm-tight con Cold-tight por modelo/semilla.
Se registran mejora/empeoramiento, utilización real de Start, abstenciones,
fallos, testigos, contradicciones online y posteriores, y límites alcanzados.
Los seis pares no bastan para significación poblacional o superioridad general.

Una ventaja propia del contrato requiere superar a su L2/control directo en
precisión y calidad sin costo desproporcionado, no solamente usar un punto previo.
Si no hay evidencia convincente, todo queda en un documento independiente.
