# Métricas fijadas antes de la primera optimización

Los 195 llamados y 225 asignaciones (con aliases fijados por bytes y parámetros)
se prepararon sin optimizar. Se comprobaron las 65 importaciones únicas. La
implementación por intervalos reemplazó la enumerativa antes de resolver y
produjo exactamente las mismas exportaciones numéricas en las 25 variantes
Shared-budget; la enmienda y los códigos previos quedan preservados.

La métrica primaria es la entrega de un punto con enteros redondeados dentro de
todos los presupuestos/cotas originales. La covariancia se evalúa por bytes de
exportación e hipótesis, no mediante llamadas idénticas repetidas.
La calidad se compara por el objetivo original recalculado tras redondear, al
tope declarado de WorkLimit=5/TimeLimit=30 s. No se considera mejor una corrida
que termina pronto con un punto que no cumple los presupuestos.

Se fijan además objetivos de referencia antes de ver las salidas nuevas:
control30: 1,265275 (entrega numérica histórica de Tight, no óptimo certificado);
cinca: 44.269.807,675929 (entrega histórica verificada);
neos-1112787: 565.031.773.677 (solución exacta publicada en MIPLIB);
beasleyC3: 754 (solución exacta publicada en MIPLIB);
k16x240b: 11.393 (valor publicado redondeado a entero, sin certificar aquí).
La prueba auxiliar de calidad es U<=U_ref+0,01*abs(U_ref), solo en puntos que
cumplen los presupuestos. Estos valores no son certificados de optimalidad.
Los estados óptimos y cotas nativos se registran sin validación global.

El prototipo prepara exportaciones y fija aliases antes de resolver. Registra
por separado selección/exportación, reconstrucción de Shared-budget, importación
y cotejo, solver y verificación. La suma de esas etapas no es una medición de
proceso nuevo desde el generador y no incluye descarga/lectura común inicial.
No se anunciará una mejora de tiempo completo de esta campaña; si hay ventaja
práctica, esa afirmación necesita una medición posterior del ciclo completo.

Las normalizaciones SOS (incluida la propuesta) se comparan a epsilon=1e-6 y
gamma=1e-5. Tight-raw constituye el control de tolerancias estrictas y utiliza
1e-9 en ambas. Todas las variantes usan presolve automático y PreSOS1BigM=0.
No se ajustan factores ni referencias después de observar resultados.
