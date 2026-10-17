#!/usr/bin/env python3
"""Render a preliminary derivation; no novelty or MILP-performance claim."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    m=json.loads((HERE/'mathematical-checks.json').read_text());a=json.loads((HERE/'storage-audit.json').read_text())
    table='| Modelo | Condición inicial del bloque | Mínimo por filas | Máx. error acumulado observado, m³ |\n|---|---:|---:|---:|\n';texrows=[]
    for r in a['original_models']:
        table+=f"| {r['instance']} | 720 | 719 | {r['observed_max_cumulative_water_error_m3']:.8g} |\n"
        texrows.append(r['instance'].replace('instance','')+' & 720 & 719 & '+f"{r['observed_max_cumulative_water_error_m3']:.5g}"+r' \\')
    text=r'''# Límites conjuntos del escalamiento: nota preliminar

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

TABLE

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

Las 24 matrices racionales pequeñas de validación dan GRID comprobaciones
exactas de grillas, además de cuatro tests. Ninguno es una comparación de
rendimiento ni una prueba de generalización. La matemática se verifica sin
solver; la auditoría de datos requiere el ZIP padre fijado por SHA256. No se
incluye otra copia de sus 30 MB.
'''.replace('TABLE',table).replace('GRID',str(m['exact_grid_comparisons']))
    (HERE/'RESULTADOS.md').write_text(text)
    latex=r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage[spanish]{babel}
\usepackage[margin=2cm]{geometry}\usepackage{amsmath,amssymb,booktabs,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue}\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\begin{document}
\begin{center}{\Large Límites conjuntos del escalamiento por filas}\\[3pt]
Nota preliminar independiente, 15 de octubre de 2026\end{center}
\textbf{Estado.} Derivación y certificados comprobados; novedad editorial y
ventaja práctica no establecidas. OMS v1.3.5 permanece sin cambios. Ninguna
llamada nueva a optimizadores.

\textbf{Antecedente clásico.} Para $A$ cuadrada no singular,
$S(A)=\|\,|A^{-1}|\,|A|\,\|_\infty$ es invariante por filas y
$\min_D\kappa_\infty(DA)=S(A)$; equilibrar las sumas absolutas de filas alcanza
el mínimo. Véase \href{https://eprints.maths.manchester.ac.uk/651/1/SURVEY.pdf}{Higham (1994), ecuaciones 2.11--2.12}.
No es un resultado nuevo de estas notas. El escalamiento óptimo tiene extensa
literatura, incluyendo \href{https://www.tuhh.de/ti3/paper/rump/Ru03a.pdf}{Rump (2003)}
y \href{https://arxiv.org/abs/2209.00809}{Qu et al.} Una búsqueda preliminar no
determina prioridad para la extensión acotada siguiente.

\textbf{Intervalos.} Sean $r_i=\sum_j|a_{ij}|$, $C=|A^{-1}|$ y
$0<L_i\leq\alpha_i\leq H_i<\infty$. Definir
\[
 t_0=\max_i L_i r_i,\quad
 \alpha_i^*=\min\{H_i,t_0/r_i\},\quad
 K_* = \max_j\sum_i C_{ji}\max\{r_i,t_0/H_i\}.
\]
Entonces $\alpha^*$ es admisible y alcanza el mínimo $K_*$ de
$\kappa_\infty(D_\alpha A)$. Es una derivación corta propia aquí, sin afirmar
novedad. Seleccionar factores no exige la inversa; certificar $K_*$ en general sí.

\emph{Prueba.} Para cualquier $\alpha$ admisible, $t=\max_i\alpha_i r_i\geq t_0$,
\[
 \kappa_\infty(D_\alpha A)=\max_j\sum_i C_{ji}\frac{t}{\alpha_i},\qquad
 \frac{t}{\alpha_i}\geq\max\{r_i,t/H_i\}\geq\max\{r_i,t_0/H_i\}.
\]
Esto prueba la cota inferior; $\alpha^*$ tiene norma máxima de filas $t_0$
y alcanza todas esas cotas, probando optimalidad.

\textbf{Qué detecta.} Intervalos locales no vacíos no garantizan
$\kappa_\infty\leq K$ si $K<K_*$. Para $A=I$, cajas $[1,10^9]$ y
$[1/16,1/8]$ dan mínimo $8$, aun con $S(A)=1$. La matriz
$\left[\begin{smallmatrix}1&1\\1&1+2^{-20}\end{smallmatrix}\right]$ tiene
piso $4\,194\,307$, aunque casi no hay dispersión de coeficientes dentro de filas.
Son ejemplos construidos, no casos operativos del despacho.

\newpage
\textbf{Compatibilidad conjunta.} Para $Ax=b$, la hipótesis de residuo
exportado $|D(A\widehat x-b)|\leq\epsilon\mathbf1$ da
$|\widehat x-x|\leq\epsilon C(1/\alpha)$. Es la mejor envolvente sobre la caja
independiente de residuos; otras restricciones pueden excluir sus extremos.
No se deduce esa hipótesis de un parámetro del solver.

Exigir a la vez $\kappa_\infty(DA)\leq K$ y esa envolvente $\leq\Delta$ equivale
a la factibilidad del LP en $(v,t)$:
\[
 v_i\geq r_i,\qquad t/H_i\leq v_i\leq t/L_i,\qquad
 Cv\leq K\mathbf1,\qquad \epsilon Cv\leq t\Delta.
\]
Las primeras restricciones implican $t\geq t_0>0$. Necesidad: usar
$t=\max_i\alpha_i r_i$, $v_i=t/\alpha_i$. Suficiencia: tomar
$\alpha_i=t/v_i$; la norma de filas es $\leq t$ y las dos últimas filas
garantizan los objetivos. Es una transformación lineal fraccional elemental.

\textbf{Certificado exacto.} Para
\[
 A=\begin{pmatrix}1&-1\\0&1\end{pmatrix},\quad
 L=(1,1),\ H=(1,128),\ \epsilon=1,\ K=10,\ \Delta=(2,1/128),
\]
condición sola es factible con $\alpha=(1,2)$, dando $\kappa=3$.
Error solo es factible con $(1,128)$, pero da $\kappa=129$.
La caja y la segunda precisión fuerzan esa última pareja, así que los objetivos
son incompatibles juntos. Todos esos factores son potencias de dos.
El LP tiene el certificado Farkas (multiplicadores no negativos)
\[
\begin{aligned}
129(-v_2\leq-1)&+(v_1+v_2\leq10)\\
&+(t-v_1\leq0)+128(v_2-t/128\leq0)
\end{aligned}
\quad\Longrightarrow\quad 0\leq-119.
\]
No usa tolerancias ni etiquetas de un optimizador. Relajar $K$ a $129$ admite
$(v_1,v_2,t)=(128,1,128)$. $\epsilon=1$ es una normalización del ejemplo.

\textbf{Grilla dyádica.} Reducir la caja a extremos dyádicos admisibles,
resolver el mínimo continuo y redondear cada factor hacia abajo conserva la
caja. La norma de filas no aumenta y la norma de la inversa crece por menos de
dos. Se obtiene una aproximación por factor dos al óptimo dyádico de condición.
Esto no preserva automáticamente una meta conjunta $\Delta$ ni garantiza
representabilidad del vector solución. La inviabilidad del LP real sí descarta
factores dyádicos. La representabilidad de productos debe entrar en los extremos.

\newpage
\textbf{Bloque hidráulico real.} En tres MILP originales de 360 períodos,
con 1440 enteras intactas, se extraen las columnas de volumen en sus balances,
fijando flujos y vertimientos. El bloque $B$ tiene diagonal $1$ y subdiagonal
$-1$; $B^{-1}$ tiene unos en el triángulo inferior. Se comprueban sus entradas
y $BB^{-1}=I$. Por eso $\kappa_\infty(B)=720$ y el mínimo por filas es $719$.
Lo alcanza $D=\operatorname{diag}(1,1/2,\ldots,1/2)$, admisible para los tres
escenarios y con exportación exacta. Los prefijos analíticos $T=8,24$ tienen
pisos $15,47$; no son instancias MILP ni resultados LP--DW.

\begin{center}\begin{tabular}{lrrr}\toprule
Caso & Inicial & Mínimo & Error acumulado máximo, m$^3$\\\midrule
TABLE
\bottomrule\end{tabular}\end{center}

Se auditan los 1093 eventos del paquete anterior, incluyendo finales repetidos.
Se suma exactamente el residuo de agua hasta cada período y se verifica el
telescopado directo. Es discrepancia respecto de reconstruir almacenamiento
con los mismos flujos/inicialización; no un error físico medido ni reparación
del MILP. Aunque 100 m$^3$ por balance permitiría una cota genérica de 36\,000
m$^3$ al final, el máximo observado es menor que 0.004 m$^3$. No aparece una
necesidad práctica en este banco.

La cota terminal teórica al usar factores máximos es aproximadamente
$1.296\cdot10^{-9}$ m$^3$, siempre condicionada a un residuo exportado que
realmente se cumpla. No es residuo observado ni promesa del solver. Los
escenarios autorizados no exigen esa precisión extrema.

\textbf{Límites y decisión.} El piso 719 corresponde a ese subsistema con flujos
fijos: no es una cota de condición de la matriz rectangular completa, de todas
las bases ni de la matriz interna del solver. La norma infinito no es la norma
1/2 del resto de los diagnósticos. Cambiar las holguras unitarias al construir
una base puede dar una matriz distinta de $DB$. La caracterización requiere
un sistema cuadrado fijo y puede necesitar una inversa densa costosa.

Se verifican GRID comparaciones exactas de grillas en 24 matrices pequeñas,
el certificado Farkas y cuatro tests. Esto comprueba las fórmulas, no prioridad
histórica ni generalización. La parte libre es clásica; la formulación acotada
y conjunta requiere revisar más antecedentes y demostrar utilidad real antes
de considerar OMS. No se añade un teorema al artículo por sí solo.

README.md describe el replay sin solvers. La auditoría completa usa el ZIP padre
fijado por SHA256; no se incluye otra copia de sus 30 MB. Los nueve paquetes
previos y la entrega OMS permanecen sin cambios.
\end{document}
'''.replace('TABLE','\n'.join(texrows)).replace('GRID',str(m['exact_grid_comparisons']))
    (HERE/'joint-limits-note.tex').write_text(latex)


if __name__=='__main__':main()
