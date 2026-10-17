# Corrección del agregado de significandos

Después de la primera corrida y de la comprobación independiente se corrigió
un contador: si el límite del significando impar es 2, el único impar positivo
permitido también es 1. Por eso la condición correcta es hmax < 3 y no hmax == 1.
Esto no modifica selectores, factores, contratos ni productos; únicamente el
agregado de filas donde solo existen potencias de dos como multiplicadores
exactos. El verificador independiente detectó y reconstruyó 17.773 filas.

Se conservan initial-study.py, initial-sources-before-results.json y los hashes
de ambos archivos de decisiones anteriores a la corrección. Una nueva ejecución
determinista debe producir exactamente esos mismos archivos de decisiones.
La implementación de selección pasó sus cinco tests antes de calcular los
primeros resultados. No hubo llamadas a optimizadores ni ajuste de políticas
según resultados. La corrección no cambia el protocolo matemático.
