# Una envolvente computable sin enumerar familias duales completas

Es una derivación suficiente basada en hechos poliédricos y Hadamard. No se
establece novedad, ni eficiencia práctica de los presupuestos obtenidos. Amplía
la nota preliminar anterior con una forma de **calcular** una envolvente.

Sean datos racionales, z entero, y libre y Ay≤b−Bz. Todas las cotas continuas
son filas; se supone que el conjunto dual común es no vacío (por ejemplo, si
algún subproblema es factible de valor finito). Multiplicamos
cada fila completa por s_i, el mínimo común múltiplo de los denominadores de
A_i, B_i **y b_i**, para obtener A', B', b' enteros. Los presupuestos pasan a
w'_i=s_i w_i. No se redondean los datos racionales a enteros aproximados.

Sea r una cota superior entera del rango de A', por ejemplo min(m,n), sin
estimación de rango en coma flotante. Sean M≥1 el mayor módulo de A',
G=ceil(log₂M), L=ceil(log₂max(1,r)), C=max_j|c_j|, W=max_i w'_i.
Se usan las potencias exactas

\[
H_r=2^{r(G+L)},\qquad H_{r-1}=2^{\max(0,r-1)(G+L)}.
\]

Todo menor de tamaño k≤r tiene módulo ≤(sqrt(k)M)^k≤H_r por Hadamard.
Para menores de tamaño hasta r−1 vale H_{r−1}. No se necesita construirlos.

## Vértices duales y costo

Un vértice de D={π≤0:A'ᵀπ=c} tiene un soporte independiente S de tamaño k≤r.
Elegir k columnas independientes reduce el cálculo a un sistema cuadrado.
Su determinante entero no nulo tiene módulo al menos uno. Por Cramer, cada
|π_i|≤k C H_{r−1}; por tanto

\[
\max_{\pi\text{ vértice de }D}|\pi|^\top w'
\le r^2 C H_{r-1} W=:K_C.
\]

Así se protege v_z(0)−v_z(tw)≤tK_C para **cualquier patrón factible** sin conocer
su dual ni enumerar todos los vértices. Se conserva el costo entero fijo.

## Rayos y patrones inviables

Un rayo extremo de {r̃≤0:A'ᵀr̃=0} tiene soporte mínimo de tamaño k≤rank(A')+1.
Sus componentes enteras primitivas se obtienen de cofactores de orden k−1,
divididos por un máximo común divisor. Por tanto cada |r̃_i|≤H_r y

\[
|\widetilde r|^\top w'\le(r+1)H_rW=:K_F.
\]

Como b'−B'z es entero, una función de Farkas positiva tiene valor al menos uno.
Imponer tK_F≤1/2 excluye todo patrón entero sin continuación factible. La
factibilidad original implica la relajada por inclusión. En combinación con
tK_C≤ε se obtienen las dos garantías uniformes. El caso costo cero es trivial.
El código usa ε=1 y elige un t diádico mediante aritmética entera/racional.

No es necesario acotar z para el argumento de retícula. Si se trabaja después
de redondear enteros, deben incluirse también |B|γ y residuos de cotas/exportación
en w: ese término fijo puede agotar el margen y hacer el contrato incompatible.

## Por qué todavía puede ser poco útil

La dependencia en dimensión y tamaño de los enteros puede volver t minúsculo.
Los denominadores binary64 son exactamente racionales pero pueden ser grandes.
Una cota suficiente así de pequeña **no prueba** que presupuestos mayores sean
inseguros: solo muestra la debilidad de esta envolvente. Harían falta cotas
estructurales certificadas más ajustadas para defender una aplicación práctica.

La comprobación completa de sistemas pequeños no certifica el cálculo en sistemas
grandes por muestreo: estos últimos se apoyan en la derivación anterior y en
cotejos exactos de datos/exponentes, no en una lista parcial de patrones.

## Límite al trasladarlo a un maestro Benders continuo

La retícula requiere parámetros enteros. Si z es continuo en y≥z, y≤1/2,
para todo t>0 suficientemente pequeño se puede elegir z=1/2+t y y=1/2.
Ese patrón continuo es inviable exactamente, pero satisface las filas con
presupuesto t. **No existe un presupuesto positivo uniforme que conserve
la factibilidad de todos los parámetros continuos de este ejemplo.**
Esto no contradice las cotas de Hoffman: aquellas presuponen que el conjunto
al que se mide distancia es no vacío. Proteger costo en patrones factibles y
excluir patrones inviables son problemas diferentes.

## Antecedentes

La ruta de Hoffman y sus constantes computables está desarrollada por
[Peña, Vera y Zuluaga](https://arxiv.org/abs/1905.02894).
Hay cotas de error mixtas de
[Stein](https://doi.org/10.1007/s10107-015-0872-7).
Esta nota no sustituye una comparación teórica exhaustiva con esos resultados
ni presenta la envolvente de cofactores como un teorema nuevo para OMS.
