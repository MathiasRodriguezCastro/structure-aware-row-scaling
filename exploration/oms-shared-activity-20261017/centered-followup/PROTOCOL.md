# Proyección del radio equilibrado: controles fuertes y sensibilidad

17-10-2026. Seguimiento definido antes de sus llamadas. No modifica la campaña
primaria de 195 llamadas. La normalización de holguras por coeficientes y su
compartición son conocidas (SCIP). Ser invariante frente a h=1 en unidades
adversas no demostraría novedad frente a esos controles.

## Método candidato y controles

La caracterización exacta de radios admisibles del estudio primario también
permite proyectar un radio de equilibrado en ese intervalo. Sea
q_i=M_i^2/||g_i||_2^2. Elegir el entero r que minimiza
max(q_max/2^(2r),2^(2r)/q_min) dentro de [r_-,r_+]. Se comparan los dos enteros
que rodean log2(q_min*q_max)/4, truncados al intervalo. Comparación racional;
empate a menor radio. Es el óptimo del centrado relativo de las actividades en
esa familia, no del trabajo solver. La información de presupuesto solo cambia
esa proyección; los demás ingredientes se conservan para la ablación.

Ocho políticas: Coefficient-SOS (escala individual por media absoluta de
coeficientes, diádica), Tight-coefficient-SOS (misma regla, epsilon=gamma=1e-9),
Unconstrained-shared (radio equilibrado compartido sin contrato),
Centered-individual (intervalo y centrado por fila), Centered-shared (propuesta),
Minimum-shared (menor radio de la campaña primaria), Indicator-budget,
Tight-raw (control directo por filas con epsilon=gamma=1e-9).

Cinco modelos sin sustitución: control30, cinca, neos-1112787, beasleyC3 y
k16x240b. Tres presupuestos en todas las activaciones: 1e-4,1e-6,1e-8 en las
unidades algebraicas originales; resto de presupuestos/cotas sin cambio.
Son sensibilidad numérica declarada, no estándares operativos.
Grupos seleccionados por incompatibilidad de fila a epsilon=1e-6,gamma=1e-5;
misma selección para todos los controles, antes de resolver. Las activaciones
que no precisan conversión reciben el contrato redondeado por filas. Las demás
filas usan presupuesto del punto crudo y se verifican después de redondear.

Semillas nuevas 197,199,211; cuatro hilos, presolve/escalado interno automáticos,
PreSOS1BigM=0, MIPGap=.01, WorkLimit=5, TimeLimit=30 s. Los otros brazos mantienen
epsilon=1e-6 y gamma_SOS=1e-5. Orden aleatorio fijado. Máximo 360 llamadas;
abstenciones explícitas si no existe representación. No se ajustan escalas tras
observar objetivos. Las tres unidades de presupuesto no son tres aplicaciones.

## Evaluación y costo

Primario: punto redondeado dentro de todas las filas, cotas y dominios originales.
Segundo: objetivo original del punto verificado y cumplimiento de las referencias
numéricas del EVALUATION_ADDENDUM primario (margen 1%). Un objetivo pequeño que
no satisface presupuestos no cuenta como éxito. No se certifican cotas globales.

Cada llamada se ejecuta como un proceso nuevo. El tiempo exterior comprende
inicio de Python, lectura de modelos preservados, construcción/selección,
exportación, importación y cotejo nativo, solve, verificación y persistencia.
No incluye la adquisición original de MPS, contracción certificada común ni el
generador C++: se denomina ciclo desde modelo preservado, no desde ese generador.
Los tiempos se miden de forma secuencial y se conserva la carga del equipo.
Los estados de solver, puntos, logs y fallos de hipótesis se guardan completos.
Todos los métodos usan el mismo verificador de entrega. El padre conserva
procesos fallidos/interrumpidos y no sustituye una salida adversa por otra.

La campaña primaria y esta confirmación tienen semillas y objetivos declarados
por separado. Se guardan resultados negativos y controles que ya cumplen el
presupuesto. No se añadirá al paper una ventaja solo sobre controles débiles.
