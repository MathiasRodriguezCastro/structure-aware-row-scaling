# Factores exactos más allá de potencias de dos

Exploración separada de OMS, fijada antes de calcular resultados nuevos.

## Pregunta y criterios

¿La selección considerando redondeo de productos ofrece una oportunidad real
frente a la grilla de potencias de dos ya implementada? Se distinguen: ampliar
el conjunto de factores de exportación exactamente proporcional, mejorar el
objetivo de centrado y obtener una mejora computacional. Solo las dos primeras
se miden aquí. No hay nuevas resoluciones ni afirmaciones de mejora MILP.

Se usan las tres entradas canónicas conocidas instance001, instance022 e
instance046 del paquete precision-work, fijado por SHA256. Son tres modelos de
la misma familia; no constituyen validación externa. Integralidad, cotas,
objetivo y filas se conservan. No se ejecuta ni modifica el generador.

## Matemática y políticas

Cada dato no nulo se escribe z = signo N_z 2^p_z, N_z impar. Para un factor
binary64 positivo alpha = m 2^k, m impar, todos los productos son exactos si y
solo si m N_z tiene a lo sumo 53 bits, p_z+k >= -1074 y el producto es finito,
además de que alpha sea representable. Se implementa selección GM completa en
ese conjunto discreto y se compara con GM restringido a potencias de dos.

Un tercer selector usa un conjunto finito declarado de candidatos binary64
redondeados y los dos selectores exactos. Verifica en racionales los límites de
coeficientes exportados y la transferencia del residuo, incluyendo el defecto
de exportación sobre las cotas de variables originales. No se afirma óptimo
global de este tercer selector. Las cotas infinitas no se sustituyen por números
arbitrarios. Se toma el mismo modelo binary64 importado del estudio padre.

Ventana [1e-9,1e9], hipótesis exportada epsilon=1e-6 y reserva entera
E=1e-9 sum_{j entero}|a_j|, con los mismos números binary64 del padre.
Escenarios físicos exigente (.01 MW,100 m3), referencia (.1,1000) y permisivo
(1,10000), incluyendo la extensión de activaciones ya documentada. Son
objetivos numéricos del estudio, no estándares de un operador.

## Medidas fijadas

Sobre todas las filas: igualdad/diferencia de factores, productos exactos,
objetivo max(alpha M,1/(alpha m)), pérdida respecto del óptimo real y costo
de selección separado. Sobre filas físicas: admisibilidad de contrato completo,
defecto de exportación/presupuesto y modificación por escenario. No se usará
una mejora del centrado como evidencia de mejor condición o rendimiento.

Sensibilidad adicional construida a partir de filas reales: reemplazar delta
por E+epsilon/(theta H), H=1e9/M y theta en {1/2,3/4,7/8,15/16,1}.
Estos presupuestos artificiales fuerzan intervalos estrechos cerca del techo;
no son necesidades detectadas en las aplicaciones. Se informa cuántas
abstenciones de potencias de dos se evitan con otros factores exactos. Esta
sensibilidad no se presenta como incompatibilidad del modelo ni validación
física. No se seleccionan ejemplos según rendimiento del solver.

Verificación: enumeración exhaustiva en formatos binarios pequeños; casos
binary64 con subnormales y límites de exponente; segundo programa independiente
que reconstruye productos y elecciones a partir de resultados y datos; replay
sin importaciones de optimizadores. Se preservan por hashes los diez paquetes
anteriores y la entrega OMS v1.3.5.

## Decisión

Sin ventaja en contratos reales, no se inicia otra campaña MILP. Un efecto
limitado a centrado o presupuestos artificiales queda como nota de software.
La revisión de antecedentes de límites conjuntos se documenta separadamente
en esta carpeta; no se reivindica novedad por no encontrar una coincidencia.
