# Escalamiento conjunto exacto con contratos

Exploración separada, 16-10-2026. Primero se implementa y comprueba una
caracterización para datos binary64, exponentes enteros y columnas enteras
inmóviles. El objetivo es decidir factibilidad y minimizar el entero t que
acota todos los coeficientes no nulos entre 2^-t y 2^t; no es condición espectral.
Se transforma simultáneamente matriz, RHS, objetivo y cotas, preservando sus
valores racionales. Los puntos devueltos se deben desescalar y verificar aparte.

Se estudian los seis modelos conocidos y los siete presupuestos de la campaña
frontier, con potencia fija .01 MW y gamma=1e-9. Se comparan columnas fijas y
columnas continuas libres. También se verifica la grilla de ventanas simétricas
t=0..40. La prueba de oportunidad precede a cualquier MILP nuevo.

Las cotas finitas y RHS exportados se limitan además a 1e19 para no cruzar los
sentinelas de infinito del backend; coeficientes [1e-9,1e9] y exactitud de todos
los datos no nulos. Los infinitos siguen siendo infinitos. Factores alpha y s
deben ser potencias de dos binary64 positivas finitas. Un contrato incorpora
E=gamma sum_entero |a| en unidades originales; no hay defecto de exportación
cuando todos los datos se exportan exactamente. E>=delta es incompatibilidad
de ESTA garantía uniforme, no prueba de inexistencia de puntos factibles.

El algoritmo debe devolver un potencial entero verificable o un ciclo de peso
negativo verificable. Un certificado en t*-1 junto a un potencial en t* prueba
optimalidad del entero t, sin confiar en el estado de un solver. Casos pequeños
se contrastan por enumeración independiente y LP de factibilidad.

Antecedentes: la formulación logarítmica y el uso de grafos para escalamiento
son clásicos (Rothblum–Schneider 1980; Orlin–Rothblum 1985; implementación
LPScale de OR-Tools).
No se reivindica la idea como nueva. La combinación concreta con contratos y
representación exacta requiere revisión de antecedentes más amplia antes de
atribuir novedad. Una mejora solo de centrado no justifica ampliar OMS.
