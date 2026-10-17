# Escalamiento interno y valor de la información del generador

Protocolo fijado antes de nuevas optimizaciones. Estudio separado del manuscrito
OMS v1.3.5 y de los siete paquetes de investigación anteriores. No se modifica
el generador C++. El diagnóstico LP–DW queda pendiente por prioridad del usuario.

## Preguntas y selección

1. ¿Una ventaja del escalamiento externo sobrevive con escalamiento interno y
presolve normales? ¿Depende de desactivar alguno de esos mecanismos?
2. Manteniendo el selector de factores, ¿los presupuestos físicos cambian
decisiones y aportan una ventaja verificable?

Descubrimiento: SG-Ter-Mer instance001 (ayuda histórica), instance014 (perjuicio)
e instance042 (resultado parecido). Se declaran seleccionadas retrospectivamente;
sus resultados anteriores solo motivan la selección. Reserva: instance002,
instance003 e instance004, ausentes del banco OMS seleccionado de 30 casos.
No se afirma que jamás hayan sido estudiadas en la tesis. No se observarán sus
resultados de optimización hasta fijar las conclusiones/predicciones del
descubrimiento. Todos conservan horizonte 360 e integralidad original.

## Transformaciones, sin redondeo de productos

Matriz canónica: importación Gurobi del MPS nativo exportado por el ejecutable
existente del generador, con --noConstante y sin preprocesar ni resolver. Se
archivan entrada, comandos, log, MPS y datos binary64. No es una réplica exacta
de los LP antiguos del exportador DummyLp (que redondeaba algunas constantes).

Un solo selector por fila propone un factor y lo proyecta al conjunto de
potencias de dos que deja todos los coeficientes no nulos en [1e-9,1e9]. Banda
identidad cerrada [0.5,2] antes de proyectar. GM minimiza exactamente, en los dos
exponentes vecinos, max(alpha*M,1/(alpha*m)); L2 propone 1/||a||2. Sin escalado
de columnas. Todos los productos de coeficientes y RHS deben ser racionalmente
idénticos a alpha por el dato binary64 original; fallo de esa comprobación
detiene la preparación. Objetivo, dominios y cotas permanecen idénticos.

- Base: identidad.
- Algebraic: GM en todas las filas, sin roles ni presupuestos.
- Structural: mismo selector, L2 cuando la fila acopla agentes entre sí o con
  variables globales; GM en las demás. Roles por pertenencia de variables,
  auditados contra nombres. Esta diferencia es una regla que usa estructura,
  no una prueba de que esa información sea inaccesible desde la matriz.
- Generator: exactamente Structural proyectado además en alpha >= epsilon/delta
  para filas físicas reconocidas. epsilon=1e-6 es hipótesis de residuo exportado,
  no promesa del solver. Tres escenarios autorizados: (MW,m3) exigente
  (0.01,100), referencia (0.1,1000), permisivo (1,10000). La decisión principal
  usa referencia. Convertir cada presupuesto a las unidades algebraicas de la
  fila. Si los factores coinciden, deduplicar las resoluciones y declarar que
  no hay efecto operacional atribuible a los presupuestos en ese banco.
- Ruiz: cuatro medias iteraciones de norma infinito, columnas fijas en uno,
  mismo selector dyádico/banda/ventana aplicado al factor acumulado.

No se reducen artificialmente los presupuestos para activar contratos. No se
atribuyen diferencias entre Algebraic y Structural a presupuestos físicos.

## Experimento y recursos

Gurobi 13.0.2, Threads=4, TimeLimit=12 s, WorkLimit=12, MIPGap=0.001,
FeasibilityTol=1e-6, IntFeasTol=1e-5, IntegralityFocus=0, semillas 307,331,353.
Los demás parámetros permanecen por defecto. Sin starts ni soluciones previas.
Factorial completo Base/Structural x ScaleFlag {-1,0} x Presolve {-1,0},
3 casos x 3 semillas = 72 MILP. Controles Algebraic/Ruiz con ambos parámetros
normales: 18 MILP adicionales. Orden permutado con semilla 20261014; resolución
secuencial. Reserva: cuatro políticas con parámetros normales, 36 MILP.
Si coinciden matrices de dos políticas, reutilizar el mismo resultado e informar
el número real de llamadas. No añadir casos, semillas o ajustes por resultados.

Cada configuración también tiene un diagnóstico presolve y una relajación LP
separados (no repetidos por semilla). Costos de esos diagnósticos NO forman parte
del tiempo MILP; no se presenta un selector operativo que omita esos costos.
Relajaciones LP: Method=1, hasta 12 s/12 unidades, sin interpretar una parada
desconocida como óptimo. Es un diagnóstico numérico, no certificado racional.

## Evidencia y límites de interpretación

Guardar estados, cotas, incumbente, gap, nodos, iteraciones, trabajo y tiempo;
progreso de cota/incumbente; punto final; log completo. Verificar después, con
sumas precisas, objetivo, filas, cotas, integralidad y presupuestos físicos en
datos originales. Distinguir epsilon/alpha (límite condicional) del residuo
observado. Medir por separado preparación/carga/optimización/verificación.
No comparar tiempo como mejora si se pierde calidad o se alcanza un límite.
Reportar completamientos a gap declarado, censura y razones emparejadas de
trabajo solo cuando ambos terminan y tienen calidad primal comparable.

Diagnóstico m.presolve(): dimensiones, rangos y huellas de filas normalizadas
por factor positivo, con RHS/sentido y nombres de variables; dominios/objetivo
incluidos en la huella completa. Huella igual demuestra igualdad de esa
representación normalizada; huella distinta no demuestra una diferencia
matemáticamente sustancial (puede haber agregación o renombrado).
La API advierte que este modelo puede diferir del usado por optimize. No expone
la matriz realmente escalada internamente. Por tanto no se afirma observar qué
factores internos sobrevivieron ni que una simulación reproduzca el solver.

Después del descubrimiento se fija un archivo de conclusiones y, solo si hay
una regla defendible, predicciones antes de abrir resultados de reserva. No se
ajusta un predictor a tres puntos ni se afirma causalidad entre un indicador y
rendimiento. La reserva comprueba generalización de afirmaciones cualitativas,
incluida la ausencia de efecto físico si se identifican factores iguales.

Criterio de incorporación al paper: mecanismo nuevo comprobable con predicción
útil fuera del descubrimiento, o ventaja competitiva clara en calidad/trabajo
atribuible a información adicional. Reducción de rangos, huellas diferentes o
una sola mejora no bastan. Si no se cumple, cerrar esta exploración con informe
breve y mantener OMS sin cambios. No se concluye que toda otra línea esté agotada.

## Documentación primaria

Gurobi [ScaleFlag](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:ScaleFlag),
[Model.presolve](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.presolve)
y [parámetros numéricos](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/numeric_parameters.html).
Consultadas 2026-10-14. Los valores internos y la ruta de presolve no se infieren
a partir de una equilibración simulada.
