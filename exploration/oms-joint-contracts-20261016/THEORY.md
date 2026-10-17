# Caracterización exacta y algoritmo: alcance de la derivación

Para un MILP con datos binary64 finitos, se considera x_j=2^v_j y_j y se
multiplica la fila i por 2^u_i. Se exige v_j=0 en TODAS las columnas enteras,
u_i,v_j enteros, y factores positivos binary64 finitos. Se exportan directamente
ldexp(a_ij,u_i+v_j), ldexp(b_i,u_i), ldexp(c_j,v_j) y ldexp(l_j,-v_j),
ldexp(h_j,-v_j). No se aplican dos multiplicaciones sucesivas que podrían
desbordar/infrafluir aun si el producto combinado fuera representable.

## Intervalos de exponentes sin logaritmos aproximados

Sea z distinto de cero, z=signo*N*2^p, N impar con a lo sumo 53 bits, y
h=floor(log2|z|). Entonces z*2^k es exactamente representable, finito y no nulo
en binary64 si y solo si -1074-p <= k <= 1023-h. Es consecuencia directa de la
representación binaria, incluyendo subnormales; no se presenta como una idea nueva.
La precisión del significando no cambia al multiplicar por potencias de dos.

Una ventana [ell,U] impone ceil(log2(ell/|a_ij|)) <= u_i+v_j <=
floor(log2(U/|a_ij|)). Los cocientes y pisos/techos se calculan con racionales
exactos, no usando log() cerca de un entero. El objetivo entero t exige además
-t-floor(log2|a_ij|) <= u_i+v_j <= t-ceil(log2|a_ij|).

Con E_i=gamma*sum_{j entero}|a_ij| y delta_i>E_i, el contrato agrega
u_i >= ceil(log2(epsilon/(delta_i-E_i))). Si delta_i<=E_i la garantía uniforme
solicitada es imposible dentro de esta clase. No es prueba de inviabilidad MILP:
el punto devuelto podría ser exactamente entero o tener errores que se cancelan.

Los intervalos exactos del RHS acotan u_i; los del objetivo acotan v_j;
los de cotas finitas acotan -v_j. Los infinitos permanecen infinitos. Un límite
adicional de magnitud para RHS/cotas se convierte en otra cota de exponente;
evita cruzar los sentinelas de infinito del backend. No limita columnas libres
mediante cajas inventadas.

## Teorema para esta clase

Poner w_j=-v_j y agregar un nodo ancla de potencial cero. Cada intervalo anterior
se escribe p_b-p_a<=d, con d entero: arista a->b de peso d. Incluye las dos
aristas de una igualdad v_j=0. El sistema de escalamiento es factible si y solo
si este grafo NO tiene ciclo de peso negativo.

Necesidad: sumar las diferencias a lo largo de cualquier ciclo da cero; pesos
con suma negativa contradicen sus desigualdades. Suficiencia: agregar un origen
con aristas cero a todos los nodos y tomar distancias mínimas produce potenciales
enteros que satisfacen todas las aristas; restar la distancia del ancla la fija
en cero. Se recuperan u_i=p_fila, v_j=-p_columna. Las equivalencias de intervalos
prueban exactitud de todos los datos, cumplimiento de ventanas y contratos.

Por sustitución invertible positiva se preservan EXACTAMENTE factibilidad y
objetivo del modelo racional binary64, incluidas las cotas y dominios enteros.
El costo original coincide con c'ᵀy+c0. Esto es equivalencia algebraica, no una
garantía sobre los errores del algoritmo del solver o de un vector desescalado
almacenado otra vez en binary64. La tolerancia de cotas de y tampoco se convierte
automáticamente en una tolerancia uniforme sobre las cotas de x.

La monotonía de la ventana en t permite búsqueda binaria. Un potencial válido
en t* y un ciclo negativo en t*-1 prueban que t* es el menor ENTERO admisible.
Esto optimiza una envolvente de magnitud, no el valor real del centrado ni el
número de condición. No requiere un MIP general. Bellman–Ford daría complejidad
O(VE log H); el prototipo usa relajaciones en cola y devuelve certificados
comprobables. No se atribuye una mejora de complejidad a esa implementación.

## Límite que no puede evitar el escalamiento de columnas continuas

Como v_j=0 para enteras, el término de redondeo E_i permanece invariante ante
cualquier escalamiento permitido de columnas. Por tanto delta_i<=E_i no puede
rescatarse por esta extensión. Si además la fila contiene un coeficiente entero
a_ij, la ventana superior obliga 2^u_i|a_ij|<=U; junto al contrato exige
epsilon*|a_ij| <= U*(delta_i-E_i). Violación estricta es otro certificado local
de incompatibilidad que tampoco puede rescatarse con columnas continuas.

En cambio una incompatibilidad causada por la dispersión entre un coeficiente
entero y uno continuo sí puede desaparecer: 2^30 z-x<=0 no cabe por filas
en [2^-10,2^10], pero un cambio de unidad de x lo permite con z intacta.
Es un ejemplo construido, no una nueva aplicación independiente.

## Antecedentes y novedad aún no establecida

La reducción logarítmica, los grafos, los ciclos y el escalamiento óptimo ya
figuran en [Rothblum–Schneider (1980)](https://people.math.wisc.edu/hans/paper_archive/scanned_papers/hs060.pdf)
y [Orlin–Rothblum (1985)](https://doi.org/10.1007/BF01585655).
[OR-Tools LPScale](https://github.com/google/or-tools/blob/stable/ortools/lp_data/matrix_scaler.cc)
implementa una formulación minimax logarítmica. La derivación aquí integra
contratos y límites exactos binary64 en esa estructura clásica. No se afirma
prioridad histórica de la combinación sin una revisión especializada más amplia.
No se añade este teorema al paper por tener un algoritmo correcto: falta probar
que cambia una decisión de resolución con utilidad suficiente.
