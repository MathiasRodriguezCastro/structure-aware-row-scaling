# Seguimiento prospectivo de aceptación y reparación

Fijado antes de nuevas llamadas MILP. La calibración usa solamente el punto
Gurobi/Base del piloto, semilla 17; queda excluida de los resultados de este
seguimiento. Los modelos y código del piloto no se modifican.

## Preguntas y unidades

Se pregunta si comprobar y reparar produce asignaciones entregables cuando falla
un punto del solver, cuál es su costo completo y cómo afecta su objetivo.
Precisión primal, calidad del objetivo y optimalidad se informan por separado.

Se conservan los presupuestos del piloto: STN 1e-5 kg por fila de material,
1e-5 en filas lógicas y 1e-3 en unidades monetarias de la fuente; MIPLIB
1e-4 max(1, |RHS|), en unidades algebraicas experimentales. Cotas como en el
piloto y dominios enteros exactos. No se reajustan después de observar resultados.

## Casos y controles

Modelos: Kondili-H14 y Kondili-H16, horizontes no usados en la calibración, y los
tres MIPLIB previamente seleccionados: control30-3-2-3, neos-3421095-cinca,
ta1-UUM. Semillas nuevas 11 y 23. No son nuevas familias independientes ni una
muestra representativa. Todas las combinaciones se retienen.

Ocho tratamientos en Gurobi 13.0.2, cuatro hilos, gap 1 %, presolve automático
y escalado interno predeterminado:

1. Default-check: Base, tolerancias ordinarias, verificación sin reparar.
2. Tight-check: Base, ambas tolerancias a 1e-9, sin reparar.
3. NumericFocus-check: Base, NumericFocus 3, sin reparar.
4. IntegralityFocus-check: Base, IntegralityFocus 1, sin reparar.
5. Base-check-repair: Base y reparación condicional.
6. L2-check-repair: L2 diádico y reparación condicional.
7. Budget-check-repair: su proyección contractual diádica y reparación
   condicional; un intervalo vacío genera abstención y no resolución.
8. Diagnostic-check-repair: regla fijada antes de resolver. Si el L2 satisface
   la cota nominal completa de redondeo, usa L2. Si no, cuando la máxima
   magnitud entera supera en al menos 1e6 la máxima magnitud continua usa Base
   y reserva la reparación; en otro caso usa Budget solamente si satisface
   la cota completa, o Base como referencia con verificación a posteriori.
   No se presenta esta regla exploratoria como predictor de fallos validado.

Los tratamientos L2/Budget comparten la tolerancia entera guiada del piloto en
STN. MIPLIB conserva tolerancias ordinarias: su selección contractual cubre el
punto crudo, y el entero se comprueba después. Elegir Base como referencia no
convierte sus factores en admisibles ni elimina incompatibilidades declaradas.

Total: 5 modelos × 2 semillas × 8 tratamientos = 80 asignaciones. Orden aleatorio
fijo con semilla 20261015, llamadas secuenciales. Se archivarán el código y hashes
antes de comenzar; una modificación requiere otro diseño, no reanudar este.

## Ciclo y límite

Se prepara efectivamente la representación de cada llamada, se coteja la
importación y se resuelve una vez (límite MILP 15 s). Se verifica la asignación
entera redondeada en todas las filas, cotas y dominios originales.

Si pasa, se devuelve ese punto. Si falla y el tratamiento admite reparación,
se fijan sus enteros más próximos y se reoptimiza el LP continuo original con
HiGHS (hasta 2 s, presolve activado y tolerancias LP 1e-9). Se comprueba de nuevo
contra las restricciones originales. Una contradicción entera constante puede
evitar el LP; no se llama certificado global de inviabilidad MILP.

Si no hay entrega verificada, se usa SoPlex/GMP exacto con el tiempo restante,
hasta 3 s. Los datos originales binary64 se escriben como decimales completos,
sin nuevos redondeos del RHS tras sustituir enteros. Se comprueba el testigo
racional y, por separado, su conversión a binary64. Se entrega únicamente si
esa conversión satisface las precisiones y dominios. Si no, se abstiene.

Presupuesto global de referencia 20 s por tratamiento, incluyendo preparación,
importación, optimización, reparación y comprobación. Los límites se ajustan al
tiempo restante; se reserva comprobación y se registran posibles excesos por
overhead. No se promete un límite de tiempo real del sistema operativo.
Guardar artefactos se mide aparte. Se conserva el costo original de preparación
de entradas compartidas, excluido del ciclo porque es común a tratamientos.

## Endpoints y comparaciones

- Entrega verificada, fallos, abstenciones e incompatibilidades sobre todas las
  asignaciones, sin excluir límites o resultados adversos.
- Tiempos completos y por etapa, número de LP de reparación y uso del exacto.
- Objetivo del punto crudo y del entregado; reparación puede empeorarlo. No se
  considera equivalente una optimización rápida con peor objetivo o precisión.
- Testigos racionales y errores al convertirlos: un testigo exacto no implica
  automáticamente precisión de su entrega flotante.
- Diagnósticos previos por fila y modelo y cumplimiento observado de sus
  hipótesis. Mu>1 significa ausencia de garantía suficiente, no fallo predicho.

Una cota dual solamente se contradice con un objetivo factible exacto del mismo
modelo; no se usan puntos numericamente filtrados. Testigos y optimalidad son
estados distintos. El seguimiento no genera certificados de optimalidad global.

## Propiedades a comprobar

El ciclo es finito y nunca acepta una entrega que falle sus comprobaciones.
Además se implementa un certificado necesario de representabilidad para filas
unarias de igualdad tras fijar enteros: los dos vecinos binary64 de b/a minimizan
la violación de esa fila. Si ambos exceden el presupuesto, ningún valor binary64
con esos enteros puede satisfacerlo, aunque exista un testigo racional exacto.
Es una propiedad elemental de cuantización, no una novedad matemática reclamada.
