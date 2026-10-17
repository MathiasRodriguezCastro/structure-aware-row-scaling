# Contrato mediante copias enteras redundantes

## Equivalencia proyectada

Para z binaria y K entero positivo, añadir q entera en [0,K] y Kz-q=0.
Cada punto original se extiende unívocamente por q=Kz; cada punto extendido
se proyecta a un punto original. Costos de q nulos. La misma afirmación para
la relajación LP vale con q continua en [0,K]. La copia entera adicional es
matemáticamente redundante; su función propuesta es numérica.

## Amplificación condicional de integralidad

Sean z0=round(z), q0=round(q). Supóngase

    |z-z0|<=gamma, |q-q0|<=gamma, |sigma*(Kz-q)|<=epsilon.

El entero q0-Kz0 tiene valor absoluto a lo sumo
K*gamma+epsilon/sigma+gamma. Si esa cantidad es menor que 1/2, necesariamente
q0=Kz0. (La condición <1 bastaría para esta última inferencia; el selector
utiliza deliberadamente el margen conservador <1/2 declarado en el protocolo.)
Se obtiene entonces

    |z-z0| <= (gamma+epsilon/sigma)/K = gamma_eff.

Para una fila a_C x_C+a_z z<=b, un residuo exportado <=epsilon después de
escalar por alpha implica violación original redondeada <=
epsilon/alpha+|a_z|*gamma_eff. Se intersecta este contrato con exportación exacta
y ventana de coeficientes. No se escalan los valores permitidos de z.

La condición que evita confundir dos enteros no debe omitirse. Si K=2^30,
gamma=1e-9, z=1/K y q=1, ambas distancias enteras satisfacen gamma y Kz-q=0,
pero round(q)!=K*round(z). El selector excluye esos tamaños de K.

## Selección y certificado

Para t fijo, la mayor sigma admisible reduce gamma_eff y no empeora el resto
del contrato de fila. Por eso basta examinarla para cada k=0,...,28. Se busca
t creciente, y después k creciente por grupo de filas. El verificador vuelve
a enumerar exponentes relevantes, demuestra factibilidad en t y ausencia de
solución en t-1, además del menor k dentro de t. Este es un óptimo del criterio
de representación declarado; no del rendimiento del solver.

## Límite encontrado

Presolve puede eliminar la integralidad redundante y la ecuación de copia.
Comprobar solo las propiedades de la matriz entregada no demuestra que el
solver aproveche el mecanismo. En los tres casos admisibles de este piloto,
los brazos con q entera y continua producen exactamente la misma matriz y
dominios después de presolve automático. Todas las q se eliminan. Los controles
computacionales impiden atribuirles una ventaja práctica.

La propiedad anterior es verificable, pero no basta para anunciar un método
nuevo útil para OMS. La prioridad bibliográfica del criterio está sin resolver;
la redundancia entera y la agregación de variables son antecedentes conocidos.
