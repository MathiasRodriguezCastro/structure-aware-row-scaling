# Frontera contractual: protocolo previo a nuevas resoluciones

Fecha: 16-10-2026. Nueva autorización de Mathias para investigar las propuestas
del documento `9fd63a59-041b-4a43-85ad-63c776df6bf3`. No se cambia OMS v1.3.10.

## Pregunta y asignaciones

Seis modelos conocidos SG-Ter-Mer: 001,005,022,027,031,046; semillas nuevas para
esta comparación 59,71,89; presolve automático (-1) y desactivado (0). No son
modelos de validación externa. No se seleccionan casos después de ver resultados.

Presupuesto de potencia FIJO 0.01 MW. Volumen 10,30,100,300,1000,3000,10000 m3.
Tolerancia entera común 1e-9, la menor admitida por el backend; hipótesis de
residuo exportado epsilon=1e-6. E=gamma*sum_entero |a| se calcula exactamente.
La reserva de exportación finita de las activaciones conserva la del método
publicado. Una incompatibilidad se registra, no se relaja ni se resuelve.

Por modelo/presolve/semilla: siete Budget-L2, L2 con igual tolerancia entera,
L2-tight (ambas tolerancias 1e-9), L2-NF3. Son 360 asignaciones; el preflight
puede abstenerse en las de contrato incompatible. Orden aleatorio fijo 2026101601.
Threads=4, TimeLimit=120 s, MIPGap=.01, ScaleFlag=-1, IntegralityFocus=0.
No se incorporan starts, ajustes de M ni cambios al generador.

## Control y puntos de comparación

La selección se ejecuta dentro de cada proceso fresco; se miden selección,
exportación, lectura/cotejo, solver, extracción, comprobación y ciclo completo.
El modelo original se genera exactamente una vez por asignación ejecutada.
Se comparan todas las asignaciones, sin borrar fallos, abstenciones ni límites.
Un reinicio/fallo externo exige una enmienda explícita antes de reintentar.

Se verifican residuos de las 4320 filas físicas/activaciones originales, crudos
y tras redondear enteros, usando Fraction. El máximo cociente y las violaciones
se evalúan con el presupuesto solicitado. Los controles se evalúan en TODOS
los presupuestos, pero se resuelven una sola vez por caso/semilla/presolve.
La hipótesis epsilon del contrato y el residuo realmente observado en la
exportación se registran por separado. La condición suficiente no es una
promesa del parámetro FeasibilityTol.

Las cotas se contrastan solo con testigos exactamente factibles de la MISMA
exportación binary64. Se intenta un LP exacto de patrón fijado por exportación,
usando el mismo patrón guardado antes de esta campaña. Si falla, el indicador
de contradicción queda desconocido; no se busca otro patrón favorable.
El LP fijado no da una cota inferior global. Ningún resultado se anuncia como
certificado de optimalidad MILP. Costos exactos y de preparación se separan.

## Criterio de utilidad fijado antes de los resultados

La señal que justifica considerar una adición es un régimen contiguo de al menos
dos presupuestos compatibles, con cumplimiento en las tres semillas de al menos
cuatro modelos, menor trabajo emparejado que NF3, sin más contradicciones de
cota detectadas que NF3 y sin pérdida de más del 1 % de costo frente a sus
incumbentes verificados. Es un criterio descriptivo, no prueba de generalidad.
Menor Work con cotas refutadas no cuenta como equivalente calidad de resolución.
Si no aparece, se cierra esta campaña en la nota independiente.

## Protección y procedencia

El diseño, este protocolo, el runner y sus dependencias se fijan por SHA256
antes del primer MILP. Se preservan todos los ZIP y versiones anteriores.
Equipo local compartido: los segundos son mediciones de esta máquina y carga.
No se ejecuta cómputo ni compresión en el login de ClusterUY.
