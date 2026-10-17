# Límites conjuntos del escalamiento: nota preliminar

**Resultado:** hay un criterio LP verificable para compatibilizar intervalos de
factores, un objetivo de condición infinito y una garantía de error hacia delante
en una matriz cuadrada fija. Se deriva un mínimo explícito para condición sola y
se comprueba una incompatibilidad conjunta con un certificado de Farkas exacto.
No se declara novedad: la parte libre es clásica y las extensiones necesitan una
revisión específica más amplia. No hay evidencia de mejora MILP que justifique
incorporar esto a OMS. Son notas separadas del manuscrito.

## 1. Antecedentes y alcance

Para A cuadrada no singular y D diagonal positiva, la cantidad de Skeel
S(A)=|| |A^{-1}| |A| ||_infinito es invariante por D y satisface
S(A)=min_D kappa_infinito(D A). La equilibración por sumas absolutas de filas
alcanza ese mínimo. Ambos resultados están explícitos en
[Higham (1994), ecuaciones 2.11–2.12](https://eprints.maths.manchester.ac.uk/651/1/SURVEY.pdf).
No son hallazgos de esta exploración. El trabajo de
[Rump (2003)](https://www.tuhh.de/ti3/paper/rump/Ru03a.pdf) estudia el óptimo
de escalamiento bilateral en varias normas. La formulación de precondicionamiento
óptimo también tiene antecedentes modernos, por ejemplo
[Qu et al.](https://arxiv.org/abs/2209.00809), con problemas cuasiconvexos y SDP.
No se equiparan esos problemas con el caso acotado de esta nota.

Aquí se mantienen fijos matriz, columnas, coordenadas y norma infinito. La
conclusión no se traslada a una matriz rectangular, a condición 1/2, a todas
las bases de un MILP o a la matriz realmente usada por el solver. Reintroducir
holguras unitarias después de escalar puede producir una base distinta de D B.

## 2. Mínimo con intervalos de factores

Sea r_i=sum_j|a_ij|, C=|A^{-1}| y 0<L_i<=alpha_i<=H_i<infinito.
Los intervalos pueden proceder de contratos, coeficientes y límites de RHS.
Definir

    t0=max_i L_i r_i,
    alpha_i*=min(H_i,t0/r_i),
    K*=max_j sum_i C_ji max(r_i,t0/H_i).

Entonces alpha* es admisible y min_alpha kappa_infinito(D_alpha A)=K*.
Para seleccionar los factores no hace falta la inversa; para certificar el
valor K* en general sí hace falta C, que puede ser costosa o densa.

Prueba. Para cualquier factor admisible, t=max_i alpha_i r_i>=t0 y

    kappa_infinito(D A)=max_j sum_i C_ji t/alpha_i,
    t/alpha_i>=max(r_i,t/H_i)>=max(r_i,t0/H_i).

Esto prueba la cota inferior. La elección alpha* tiene norma máxima de filas t0
y alcanza todas esas cotas simultáneamente, por lo que alcanza K*. En particular,
la especificación Kobjetivo<K* es imposible aunque todos los intervalos locales
sean no vacíos. Es una derivación corta propia de estas notas, sin prioridad
histórica ni novedad editorial comprobadas.

Ejemplos exactos: una matriz 2x2 casi paralela, con coeficientes entre 1 y
1+2^-20, tiene mínimo 4.194.307 por cualquier escalamiento de filas. No se
explica por dispersión de coeficientes dentro de una fila. Para A=I, intervalos
[1,10^9] y [1/16,1/8] dan mínimo 8, frente a Skeel=1; todos los contratos locales
son compatibles. Los intervalos del segundo ejemplo pueden proceder de un
límite de RHS: no se los presenta como tolerancias operativas reales.

## 3. Compatibilidad conjunta con error hacia delante

Para A x=b, residuo exportado |D(A xhat-b)|<=epsilon 1 implica

    |xhat-x|<=epsilon C (1/alpha).

Esa es la mejor envolvente componente a componente sobre la caja independiente
de residuos considerada. Otros límites del problema pueden excluir sus extremos.
epsilon es una hipótesis a verificar, no una consecuencia automática de fijar
FeasibilityTol. No incluye perturbaciones adicionales de datos o redondeo entero.

Exigir simultáneamente kappa_infinito(D A)<=K y error<=Delta es equivalente a
la factibilidad del siguiente LP, con variables v_i y t:

    v_i >= r_i,
    t/H_i <= v_i <= t/L_i,
    C v <= K 1,
    epsilon C v <= t Delta.

La caja y v>=r implican t>=t0>0. Dado alpha, usar t=max_i alpha_i r_i y
v_i=t/alpha_i prueba necesidad. Dado un punto LP, alpha_i=t/v_i está en la
caja, la norma de filas es <=t, y las dos últimas filas garantizan los objetivos.
Esto prueba suficiencia. La transformación es lineal fraccional elemental;
no se presenta como una nueva técnica general de optimización.

### Contraejemplo conjunto, con todos los factores dyádicos

    A=[[1,-1],[0,1]], L=(1,1), H=(1,128), epsilon=1,
    K=10, Delta=(2,1/128).

Condición sola: alpha=(1,2) da kappa=3<=10. Error solo: alpha=(1,128) alcanza
Delta, pero da kappa=129. La segunda precisión y la caja fuerzan alpha_2=128;
la primera caja fuerza alpha_1=1. Por tanto no hay solución conjunta.
La normalización epsilon=1 solo evita constantes; no define un estándar físico.

El LP guarda un certificado Farkas de cuatro filas, todas en sentido <=:

    129*(-v_2<=-1)
    + (v_1+v_2<=10)
    + (t-v_1<=0)
    + 128*(v_2-t/128<=0)
    da 0<=-119.

No depende de tolerancias ni de una etiqueta de un solver. Relajar K a 129
admite (v_1,v_2,t)=(128,1,128). Es un contraejemplo construido, no una
incompatibilidad encontrada en un despacho real.

## 4. Restricción dyádica

Si cada intervalo contiene potencias de dos exactas, tomar su envolvente dyádica
[2^ceil(log2 L),2^floor(log2 H)], resolver el caso continuo anterior y redondear
cada factor hacia abajo a potencia de dos. El factor sigue en la caja y cada
recíproco crece por menos de dos. La condición resultante es menor que dos
veces el óptimo continuo de esa caja y, por tanto, es una aproximación por factor
dos al óptimo dyádico. Los extremos de la caja deben incluir también los límites
de representabilidad por dato, como en el paper.

Esta afirmación solo trata la condición. No garantiza conservar una cota conjunta
de error Delta al redondear factores ni encontrar un punto dyádico cuando el LP
real sea factible. En cambio, inviabilidad del LP real descarta también todos
sus factores dyádicos. No se propone otro teorema para el paper.

## 5. Comprobación en almacenamiento hidroeléctrico real

Se verifican los tres modelos originales de 360 períodos del paquete anterior,
que conservan 1.440 enteras cada uno. Solo se extraen las columnas de volumen
de sus balances, fijando caudales y vertimientos. El bloque resultante B es
bidiagonal inferior, con diagonal 1 y subdiagonal -1; B^{-1} tiene unos en el
triángulo inferior. Se comprueban todos los coeficientes y B B^{-1}=I.

Por tanto kappa_infinito(B)=720 y su mínimo por filas es 719. Lo alcanza D con
primer factor 1 y los demás 1/2; satisface todos los escenarios físicos y exporta
exactamente. La equilibración ya no puede reducir ese piso estructural. Los
prefijos analíticos T=8 y T=24 tienen pisos 15 y 47. Son submatrices del mismo
subsistema, no nuevas instancias MILP ni un cálculo de la brecha LP–DW.

| Modelo | Condición inicial del bloque | Mínimo por filas | Máx. error acumulado observado, m³ |
|---|---:|---:|---:|
| instance001 | 720 | 719 | 0.0022244977 |
| instance022 | 720 | 719 | 3.3755359e-06 |
| instance046 | 720 | 719 | 0.0035252826 |


Los errores acumulados se calculan sobre los 1093 eventos originales (incluidos
finales repetidos) mediante aritmética entera exacta. Para cada tiempo se suma
el residuo de los balances anteriores y se comprueba el telescopado directo.
Es la diferencia respecto de reconstruir almacenamiento con los mismos flujos
e inicialización; no es un error físico medido ni una solución reparada del MILP.

La suma de presupuestos locales de 100 m3 solo daría una cota uniforme genérica
de 36.000 m3 al final de 360 períodos; en los puntos reales el máximo fue menos
de 0,004 m3. No hay una necesidad práctica de corregir este efecto en este banco.
La cota genérica no incluye restricciones adicionales que puedan impedir el peor
caso. Tampoco prueba imposibilidad de una garantía mejor por escalamiento:
factores mayores reducen epsilon/alpha si la hipótesis exportada se cumple.

La mejor cota terminal condicional usando los factores máximos admisibles de
estas filas es aproximadamente 1,296e-9 m3; no es residuo observado ni promesa
del solver, y no analiza la representación binary64 del vector solución. Esa
precisión extrema no se solicita en los escenarios autorizados.

## 6. Decisión y siguientes condiciones para avanzar

La nota aporta una derivación comprobable y un certificado conjunto, pero no
una nueva contribución experimental: el bloque hidráulico no muestra una
dificultad práctica y la parte clásica no tiene novedad. Antes de considerar
OMS harían falta una auditoría de antecedentes específica de la formulación
acotada/conjunta y un caso real donde el certificado cambie una decisión útil.
No se incorpora nada al manuscrito ni se afirma un algoritmo MILP nuevo.

La caracterización exige una matriz cuadrada fija y una inversa absoluta. Usarla
antes de resolver un MILP requiere saber qué sistema se quiere proteger; no
certifica simultáneamente todas sus bases o patrones. No hay afirmación sobre
runtime, cortes, brecha entera o factores internos de Gurobi.

Las 24 matrices racionales pequeñas de validación dan 4667 comprobaciones
exactas de grillas, además de cuatro tests. Ninguno es una comparación de
rendimiento ni una prueba de generalización. La matemática se verifica sin
solver; la auditoría de datos requiere el ZIP padre fijado por SHA256. No se
incluye otra copia de sus 30 MB.
