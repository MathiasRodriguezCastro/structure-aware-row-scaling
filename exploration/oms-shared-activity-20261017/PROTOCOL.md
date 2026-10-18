# Actividades compartidas con precisión y covariancia de unidades

17-10-2026. Continuación de investigación solicitada por Mathias tras señalar
que cerrar los cuatro pilotos negativos no satisfacía la búsqueda de un método.
El paper OMS v1.3.14 y los resultados anteriores se mantienen intactos.

## Hipótesis anterior a las nuevas optimizaciones

Las variables de actividad de SOS1 están sujetas a una tolerancia absoluta de
cero. Una escala fija h=1 puede cambiar su precisión física al cambiar unidades.
Se investigan conjuntamente: (1) una escala con contrato que sea covariante a
cambios diádicos coherentes de unidades; (2) una actividad normalizada compartida
por todas las activaciones seleccionadas de una misma binaria.

Para un bloque g_i(x_cont)<=M_i*z, z binaria, M_i>0, sustituir sus filas por
g_i-(M_i/R)*y<=0, 0<=y<=R, w+z=1 y una sola SOS1(w,y).
R=2^r se elige como el menor radio que admite factores diádicos alpha_i con
exportación exacta, coeficientes en [1e-9,1e9], R<=1e19 y

    epsilon/alpha_i + (M_i/R)*max(gamma_SOS,tau) <= delta_i.

Se elige L2 dentro de cada intervalo de fila. La propiedad del bloque redondeado
requiere las hipótesis observadas de enlace/complemento/SOS/cota y que round(z)
sea 0 o 1. No necesita asumir la distancia nominal de z a entero: si round(z)=0,
z<=1/2 y w>=1/2-epsilon_c>gamma_SOS. El resto del modelo se verifica completo.

Si cada fila y su presupuesto se multiplican coherentemente por 2^k_i, R no
cambia, M_i/R se multiplica por 2^k_i y alpha_i por 2^-k_i: la exportación debe
ser idéntica, mientras se conserve representabilidad. No se declara novedosa
la reformulación SOS ni compartir holguras (SCIP ya tiene usesameslackvar).
Se contrasta el criterio contractual y su utilidad, sin declarar prioridad.

## Casos fijados antes de adquirir resultados

Control30 y cinca son descubrimiento conocido. Se reutiliza en ambos la misma
contracción certificada de M, para todos los controles. Neos-1112787 proviene del
piloto histórico pero no de las campañas SOS/copia: es transferencia a otra
estructura, no un dato jamás observado. BeasleyC3 y k16x240b son dos modelos nuevos
de costo fijo y flujo de MIPLIB, elegidos ahora por su estructura publicada antes
de descargar/inspeccionar soluciones. No se sustituyen si son desfavorables.

Presupuestos originales 1e-4 max(1,abs(RHS)), cotas 1e-4, unidades algebraicas
experimentales; sin atribuirles requisitos operativos. Se detectan filas con RHS
cero, una sola binaria con coeficiente negativo al normalizar <=, y solo variables
continuas restantes. Se seleccionan los grupos que contienen alguna fila cuyo
contrato redondeado no admite factor a gamma=1e-5. Se transforman todas las filas
de ese grupo. Otros patrones no soportados se registran, no se generalizan.

Unidades diádicas k=-20,-10,0,10,20 en las filas de activación y sus presupuestos;
no se cambian variables, costos ni los otros presupuestos. Son cinco
representaciones de un problema, no cinco instancias independientes.

## Controles y llamadas

Budget-row (contrato redondeado, abstención si imposible); Raw-budget (sin reserva
entera); Tight-raw (FeasibilityTol=IntFeasTol=1e-9); NF3-raw; SOS-unit (h=1,L2);
SOS-normalized (h=potencia de dos inferior a delta, contrato completo);
SOS-range (h=M, una actividad por fila, L2);
Individual-budget (h diádico máximo por fila, mismo contrato);
Shared-budget (radio mínimo por grupo, propuesta);
Indicator-budget (implicación nativa escalada por precisión más g<=M).
Las filas no seleccionadas comparten Raw-budget para aislar la intervención;
su precisión tras redondear se comprueba y no se promete por esa selección.

Gurobi 13.0.2, cuatro hilos, presolve/escalado interno automáticos, gamma=1e-5,
epsilon=tau=1e-6, salvo Tight-raw. NumericFocus=3 solo en NF3-raw.
PreSOS1BigM=0 común para evitar reintroducir big-M en los brazos SOS; se declara
esta configuración en toda conclusión. Semillas nuevas 181,191,193.
TimeLimit=30 s, WorkLimit=5, MIPGap=.01. Orden aleatorio fijo.
Modelos byte a byte idénticos con iguales parámetros se resuelven una vez por
semilla; aliases se fijan por hashes antes de la primera optimización. Se mide
selección/exportación/importación, solver, verificación y proceso completo.
Logs completos: OutputFlag=1, LogToConsole=0. No se reemplazan ausencias de punto.

Primero se comprueban equivalencia proyectada, garantía, radio mínimo y
covariancia con pruebas racionales y enumeración. Después se verifican todas
las filas/cotas originales y cada hipótesis sobre puntos preservados. Cualquier
fallo se conserva. No se certifican cotas ni óptimos globales por estados nativos.
Mejorar solo frente a SOS-unit en unidades adversas no basta: se exige comparar
con SOS-normalized, Individual-budget, Indicator-budget y controles por filas.
La invariancia se reporta por exportaciones, no como replicación de optimizaciones.

Fuentes primarias: documentación de SOS de Gurobi; cons_indicator.c de SCIP
(scaleslackvar y usesameslackvar); páginas MIPLIB de los cinco modelos. El
resultado previo negativo con h fijo motiva este protocolo, no se oculta.
