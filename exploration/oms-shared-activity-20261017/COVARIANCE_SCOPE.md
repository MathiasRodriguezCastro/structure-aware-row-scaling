# Precisión del alcance de covariancia

La propiedad algebraica sin fronteras de representación es exacta: al cambiar
g_i,M_i,delta_i por 2^k_i, R se conserva, h_i cambia por 2^k_i y alpha_i por
2^-k_i. Las ventanas de los coeficientes exportados y la desigualdad de
precisión se conservan. Cada q_i del criterio centrado también se conserva.

Con restricciones binary64, la conclusión sobre el **selector** requiere que
ese cambio y su inverso establezcan una correspondencia entre las
representaciones admisibles relevantes para la minimización. No basta con que
solo siga representable el minimizador anterior: una escala antes excluida por
desbordamiento podría pasar a ser representable y cambiar el mínimo. La frase
abreviada «mientras siga representable» de la derivación debe entenderse con
esta condición en ambos sentidos, no como una invariancia global.

`test_boundary_certificates.py` construye un contraejemplo explícito: una fila
con g=M=delta=1e308 admite como mínimo r=0. Tras multiplicar coherentemente por
2^-1000 admite r=-16. El anterior r=0 sigue siendo admisible: no basta que ese
minimizador sobreviva. Antes, h=M/2^-16 desborda; después, resulta representable.
El ejemplo no se resuelve ni se utiliza como caso computacional favorable.

Los experimentos no dependen de extrapolar esa propiedad: se comprueban
directamente los 25 modelos Shared-budget exportados, idénticos por bytes en
las cinco conversiones ensayadas. Además hay pruebas de conversiones mixtas
por fila. Las fronteras se prueban por separado y no se anuncian como casos
de invariancia. Esta precisión no cambia diseños, factores ni resultados.
