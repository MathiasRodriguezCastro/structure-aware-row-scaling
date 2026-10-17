# Integración C++: una reducción real del costo de preparación

**Resultado comprobado:** en los seis modelos conocidos, el selector integrado
produce exactamente los mismos factores y modelos binary64 que Python. Para
Budget-L2 la preparación completa independiente es entre **3,70 y 6,37 veces
más rápida** en las medianas por modelo. No se ha medido esa aceleración para
la resolución completa del MILP.

La mediana de las seis medianas por modelo pasa de **1,243 s a 0,315 s** para
Budget-L2; para L2 pasa de 1,067 s a 0,265 s. Son 168 preparaciones cronometradas
en la pasada corregida: seis modelos x dos políticas x dos implementaciones x
siete repeticiones. El orden se fijó antes de medir. La máquina es compartida y
hubo otras campañas locales concurrentes; estos segundos no son una constante
del algoritmo ni un benchmark de hardware aislado.

El intervalo 3,70–6,37 compara medianas, no es un intervalo estadístico. Los
datos por modelo están en [verified-summary.csv](verified-summary.csv).

## Qué se implementó

Un hook sobre una copia aislada del generador aplica los contratos sobre los
objetos `Problema/Restriccion`, después de construir el modelo una sola vez y
antes de exportar. Selecciona todos los factores antes de modificar una fila.
Las reservas y extremos se calculan con racionales Boost multiprecisión;
los extremos se redondean hacia dentro y la reserva hacia fuera. Se preservan
RHS, costos, cotas y dominios. No se modifican el generador original, su binario,
los modelos de las otras campañas ni la entrega OMS v1.3.10.

Se comprobó igualdad de 120.960 filas entre implementaciones y cumplimiento
exacto de 25.920 contratos físicos. Cada una de las 168 exportaciones vuelve a
coincidir con su referencia; los factores también coinciden. Esta evidencia
permite separar una mejora de implementación de un cambio de representación.

## Qué tiempo se mide y qué falta

La medición incluye arranque del proceso Python de orquestación, imports,
generación, reconstrucción de metadata cuando corresponde, selección,
exportación y persistencia de factores/resultado. El chequeo experimental que
compara ambas implementaciones se mide fuera de ese ciclo. El brazo C++ usa el
mismo generador -O2 que Python, activando el hook: no se compara un generador
optimizado contra uno compilado sin optimización.

El flujo Python de resolución necesita además importar bibliotecas del solver y
del verificador. Parte del ahorro de arranque de este benchmark podría solaparse
con imports que ambos flujos necesitan de todos modos. Por eso **no se suma ni
se resta este ahorro a los tiempos históricos del solver para inventar un nuevo
tiempo total**. La mejora de selección y exportación sí queda medida; una ventaja
completa frente a NF3 requiere un seguimiento del flujo completo.

## Corrección de auditoría conservada

La primera pasada completa de 168 preparaciones se conserva en `first-pass/`.
El verificador detectó que el CSV C++ no citaba los nombres de filas que contienen
comas. Los modelos y factores eran correctos; el CSV no era interpretable por
un lector CSV estándar. Se corrigió exclusivamente la emisión de ese registro,
se recompiló y se repitió TODO el diseño, sin escoger la pasada más rápida.
El checker confirma que las exportaciones de ambas pasadas son idénticas.
Son **336 preparaciones cronometradas y 48 de preflight** en total. La primera
pasada también favorecía a C++; sus medianas se incluyen en `VALIDATION.json`.

## Decisión editorial

Es un resultado útil de software para OMS, con un alcance concreto: el costo
del selector Python no es inherente al método. Todavía no amplía la recuperación
de precisión primal a otros casos ni certifica cotas. Se conserva como módulo
experimental y candidato a incorporación breve, sin añadir una contribución
matemática por el mero hecho de programarlo en C++.

Reproducción de los resultados guardados, sin resolver ni compilar:

```bash
python3 exploration/oms-native-selector-20261016/independent_check.py
```

Para recompilar: GCC 11.4, C++17 y Boost 1.74 (`libboost-dev`). Las rutas de
includes locales usadas están en `build-with-local-boost.log`. Todos los backends
comerciales se excluyeron de este ejecutable. No se llamó a ningún optimizador
en este benchmark.
