#!/usr/bin/env python3
"""Regenerate the separate four-page research note and short results summary."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    v=json.loads((HERE/'independent-verification.json').read_text());assert v['benders_arms']==45 and v['common_dual_nonemptiness_proofs']==8
    preventive=json.loads((HERE/'preventive-results.json').read_text())
    rows=list(csv.DictReader((HERE/'dispatch-summary.csv').open()))
    budgets='\n'.join(f"{r['model']} & {r['continuous_variables']} & {r['scale_exponent']} & {r['negative_decimal_exponent_approx']:.0f} \\\\" for r in preventive)
    names={'rn8':'RN','rn8-base':'RN-base','sg8':'SG'}
    table='\n'.join(f"{names[r['model']]} & {r['policy']} & {r['iterations']} & {r['cuts']} & {float(r['median_total_seconds']):.4f} \\\\" for r in rows)
    md='''# Resultados de las otras dos líneas

Estudio independiente de OMS, con fuentes C++ sin modificar.

## Garantías preventivas

Hay una envolvente computable de todas las familias duales y de Farkas usando
menores enteros y Hadamard, sin enumerar vértices/rayos. Protege costo para
patrones factibles y excluye los inviables bajo las hipótesis racionales y
enteras indicadas. Se comprobaron las hipótesis de acotación con ocho pruebas
duales y las familias completas de tres sistemas pequeños (diez patrones).
No se establece novedad; la prueba es una cota suficiente muy conservadora.

| Modelo | Continuas | Factor uniforme suficiente | Aproximación decimal |
|---|---|---|---|
'''+ '\n'.join(f"| {r['model']} | {r['continuous_variables']} | {r['uniform_scale']} | 10^(-{r['negative_decimal_exponent_approx']:.0f}) |" for r in preventive)+'''

El factor multiplica todos los presupuestos algebraicos originales, incluidas
cotas; epsilon=1 unidad de costo, margen de Farkas rho=1/2. No es el presupuesto
máximo admisible. Su pequeñez no prueba que todo presupuesto mayor sea inseguro.
No se calculó la constante de Hoffman óptima de esos modelos.

Para un maestro continuo, el margen entero no se traslada automáticamente:
y>=z,y<=1/2 admite parámetros inviables z arbitrariamente cercanos a 1/2.
No existe un presupuesto positivo uniforme que preserve todos sus parámetros
continuos. La existencia de una continuación y la precisión de su costo son
garantías distintas. Ver DERIVACION.md y complete-small-checks.json.

## Selección de cortes del despacho

Se implementó Benders temporal multicut sobre tres LP reales archivados de ocho
períodos, dos RN relacionados y un SG. Cinco políticas y tres repeticiones:
45 corridas, 1896 LP de recourse, 237 LP maestros, 24 LP para pisos compartidos
y nueve referencias compactas. Los pisos y los 1896 duales/cortes se comprueban
racionalmente; las decisiones de filtrado se reproducen sin solver.

| Modelo | Política | Iteraciones | Cortes | Mediana de segundos completos |
|---|---|---|---|---|
'''+ '\n'.join(f"| {names[r['model']]} | {r['policy']} | {r['iterations']} | {r['cuts']} | {float(r['median_total_seconds']):.4f} |" for r in rows)+'''

Los filtros no mejoran All y no reducen el número final de cortes. La geometría
cruda es ortogonal por soportes horarios disjuntos; la proyección hidráulica no
produjo una mejora. La etiqueta física fue siempre balance/demanda: la ablasión
física no tuvo variación y no permite afirmar que esa información carezca de valor.
El compacto tarda alrededor de 1–2 ms. No hubo un maestro grande cuyo costo
justificara filtrar, ni se estudió el MILP completo.

Todas las corridas coinciden numéricamente con la referencia; residuo máximo
original final 9.41e-10. Dos LP tienen certificado racional de óptimo; en RN,
SoPlex devolvió unknown, sin prueba de inviabilidad ni certificado de óptimo.
Los tres intentos exactos fueron posteriores y no influyeron en las políticas.
Ver AUDITORIA_DESPACHO.md para las conclusiones y límites de las notas anteriores.

## Estado real

Ambas líneas avanzaron más allá de una propuesta. No se resolvió todavía cómo
obtener presupuestos uniformes útiles para los modelos grandes, ni apareció un
selector que mejore el despacho. No se incorporó material a OMS v1.3.5. Los
resultados y el intento de referencia sin certificar se conservan completos.
'''
    (HERE/'RESULTADOS.md').write_text(md)
    tex=r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=1.9cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[spanish,es-nodecimaldot]{babel}
\usepackage{lmodern,amsmath,amssymb,booktabs,microtype}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}
\begin{document}
\begin{center}
{\Large Garantías preventivas y filtrado de cortes del despacho}\par
{\large Resultados y límites de las dos líneas pendientes}\par
14 de octubre de 2026 --- Fuera de OMS v1.3.5
\end{center}

\textbf{Resultado matemático implementado.} Se obtuvo una envolvente
\emph{calculable} de todas las familias duales y de Farkas usando determinantes,
sin enumerarlas. Da condiciones suficientes uniformes para patrones enteros
desconocidos, pero los presupuestos resultan demasiado conservadores para
defender su aplicación práctica en los modelos examinados. No se afirma novedad.

Para $Ay\le b-Bz+w$, $z$ entero e $y$ libre, todas las cotas continuas son filas.
Se supone un dual común no vacío. Se convierte cada fila completa a enteros
mediante un factor racional exacto $s_i$ que incluye denominadores de $A_i$,
$B_i$ y $b_i$. Sean $r\le\min(m,n)$ una cota superior del rango, $M\ge1$ el
máximo módulo de la matriz continua entera, $C=\|c_C\|_\infty$ y
$W=\max_i s_iw_i$. Con $G=\lceil\log_2M\rceil$, $L=\lceil\log_2\max(1,r)\rceil$,
\[
 K_C=r^2 C\,2^{\max(0,r-1)(G+L)}W,\qquad
 K_F=(r+1)2^{r(G+L)}W.
\]
Elegir $tK_C\le1$ y $tK_F\le1/2$ protege el costo de cualquier patrón factible
en una unidad y conserva exactamente qué patrones enteros admiten continuación
al usar $tw$. La cota usa menores enteros, Cramer y Hadamard; no rango numérico.

\begin{center}\small
\begin{tabular}{lrrr}\toprule
Modelo & Continuas & $t=2^{-N}$: $N$ & $-\log_{10}t$ aprox.\\\midrule
@@BUDGETS@@
\bottomrule\end{tabular}
\end{center}
Los presupuestos de referencia son algebraicos: fila
$10^{-4}\max(1,|b_i|)$ y cotas $10^{-4}$, incluidos los almacenados en los cinco
MILP previos. $t$ multiplica esos valores; no es una tolerancia física del operador.
Las aproximaciones decimales solo facilitan lectura: el cálculo usa potencias
exactas. Estos valores suficientes diminutos \textbf{no demuestran que todos los
presupuestos mayores sean inseguros}. No se calcula aquí el mayor presupuesto
admisible ni la constante de Hoffman óptima.

\newpage
\textbf{Por qué la envolvente cubre patrones desconocidos.}
Cada vértice de $\{\pi\le0:A'^\top\pi=c_C\}$ tiene soporte independiente de tamaño
$k\le r$. Un subsistema cuadrado tiene determinante entero de módulo al menos
uno y cofactores acotados por Hadamard. Así $\sum_i|\pi_i|s_iw_i\le K_C$.
La dualidad da $0\le v_z(0)-v_z(tw)\le tK_C$ para cualquier patrón factible.
El costo entero fijo se cancela. No se garantiza una continuación cercana al
punto numérico ni un valor globalmente óptimo del MILP.

Un rayo extremo de $\{\widetilde r\le0:A'^\top\widetilde r=0\}$ tiene soporte
de tamaño a lo sumo $r+1$. Su representante entero primitivo tiene componentes
acotadas por menores de orden hasta $r$, por lo que
$\sum_i|\widetilde r_i|s_iw_i\le K_F$. Si un patrón entero es inviable,
Farkas da algún rayo con $\widetilde r^\top(b'-B'z)\ge1$.
Tras relajar $tw$, ese valor sigue siendo al menos $1-tK_F>0$.
La inclusión de factibilidad en el otro sentido es inmediata porque $w\ge0$.

\textbf{Comprobaciones.} Se enumeraron familias completas, con aritmética
racional, de tres sistemas pequeños: uno de un período, otro de dos y otro con
acoplamiento racional. Se verificaron sus cinco vértices y siete rayos,
diez patrones binarios, pérdidas de costo y exclusión de los cuatro patrones
inviables. No se extrapola la completitud de estos ejemplos a los modelos grandes.
Para los ocho modelos se comprobaron independientemente los exponentes y la
hipótesis dual: cinco certificados originales de continuación y tres duales
compuestos a partir de pisos horarios y cotas finitas de costo del maestro.
Estas últimas pruebas no afirman factibilidad primal de RN.

\textbf{Límite al trasladar la garantía al despacho descompuesto.}
Si el maestro contiene parámetros continuos, la retícula no aparece automáticamente.
En $y\ge z$, $y\le1/2$, para todo $t>0$ pequeño se puede tomar
$z=1/2+t$, $y=1/2$. El parámetro es exactamente inviable, pero satisface ambas
filas con presupuesto $t$. No existe presupuesto positivo uniforme que preserve
la factibilidad de \emph{todos} esos parámetros continuos.
Las cotas de Hoffman no contradicen esto: su estimación de distancia requiere
un conjunto factible no vacío [1]. Costo en patrones factibles y exclusión de
patrones inviables exigen hipótesis distintas.

Si se redondean enteros numéricos antes de certificar, hay que añadir $|B|\gamma$
a los presupuestos efectivos, además de cotas y exportación. Esa perturbación
fija puede agotar el margen. El resultado no obliga al solver a respetar un
presupuesto menor que su tolerancia o que la resolución de binary64.
La pregunta abierta útil es obtener envolventes estructurales mucho más ajustadas,
no repetir el argumento de existencia. Hoffman [1] y las cotas mixtas de Stein [2]
son antecedentes que requieren una comparación teórica adicional antes de afirmar
novedad. La derivación completa y los cotejos están en \texttt{DERIVACION.md}.

\newpage
\textbf{Selección de cortes: implementación y experimento nuevos.}
La tesis implementa DW y branch-and-price. Sus ejemplos de Benders no constituyen
un selector productivo. Se construyó un prototipo aislado de Benders multicut
temporal sobre tres MPS reales archivados de ocho períodos. Son LP continuos,
dos RN relacionados y un SG; \textbf{no se resolvió aquí el MILP completo}.
El maestro conserva volúmenes, caudales, vertimientos y todas las filas temporales
de agua; el resto se separa en ocho LP horarios. El parser independiente coteja
todos los coeficientes, RHS, objetivo y cotas contra el MPS original.

All incorpora todos los cortes. Los filtros eligen hasta cuatro cortes de costo,
siempre incluyendo el de mayor eficacia: Top, diversidad cruda, diversidad
proyectada sobre el núcleo hidráulico escalado y una bonificación física fija.
Los cortes de factibilidad violados se agregarían todos. Cinco políticas,
tres repeticiones/semillas, un hilo, dual simplex Gurobi 13.0.2, tolerancias
$10^{-9}$, presolve/escalado normales. Protocolo y código fijados antes de resolver.

\begin{center}\small
\begin{tabular}{llrrr}\toprule
Modelo & Política & Iteraciones & Cortes finales & Mediana total (s)\\\midrule
@@TABLE@@
\bottomrule\end{tabular}
\end{center}
Los tiempos incluyen preparar el maestro, pisos horarios, reconstrucción racional,
subproblemas, selección y exportación. Los pisos compartidos se cobran completos
a cada brazo. El compacto tarda aproximadamente 0.001--0.002 s; los tiempos
son pequeños y no se infiere significancia estadística. Todos los filtros
terminan con el mismo número de cortes que All, pero necesitan más iteraciones.
No se detecta una ventaja del filtrado en este banco.

Hubo 45 brazos, 237 LP maestros, 1896 LP horarios, 24 LP de pisos compartidos
y nueve referencias compactas. Se reconstruyeron y verificaron racionalmente
los 1896 duales y su exportación hacia el exterior; se agregaron 810 filas.
No aparecieron rayos de factibilidad. El replay también comprueba las decisiones
de los cinco filtros. No es una comparación con los algoritmos completos de [3--5].

\newpage
\textbf{Hallazgos estructurales y límites de la evidencia.}
Los gradientes de cortes de un lote horario tienen soportes disjuntos: su coseno
crudo es cero. Esa ortogonalidad no refleja el acoplamiento del agua, que está
en el maestro. La proyección hidráulica cambia la métrica, pero el máximo coseno
medio absoluto observado sigue siendo $0.000258$. No mejoró los resultados.
La normalización por anchos usa un piso de una unidad para anchos pequeños o
variables libres: es una heurística registrada, no invariancia física universal.
PCA/Gram--Schmidt tampoco autorizan sustituir desigualdades por combinaciones
con pesos arbitrarios de signo mixto, que pueden dejar de ser válidas.

La etiqueta dominante asignó los 1896 candidatos al grupo balance/demanda.
La bonificación de otra familia quedó inactiva. Este ensayo no identifica el
valor de diferenciar información hidráulica/térmica. Los maestros finales solo
tienen 8--30 cortes: conservar muchas filas no fue un cuello de botella.
Para otra etapa haría falta demostrar ese cuello de botella y variación física
en el modelo elegido, no añadir pesos o modelos para buscar una mejora.

\textbf{Precisión de las conclusiones.} Las 45 corridas convergieron
numéricamente al LP compacto, con diferencia de objetivo máxima
$4.66\,10^{-10}$ y residuo máximo original final $9.41\,10^{-10}$.
Tres intentos racionales \emph{posteriores}, sin influir en políticas, certificaron
los óptimos de SG y RN-base. SoPlex devolvió \texttt{unknown} en RN;
\textbf{no es un certificado de inviabilidad ni de óptimo}. Se conserva ese intento.
La validez exacta de los cortes no convierte por sí sola la salida flotante o
su gap en un certificado racional de óptimo del despacho.

El análisis histórico prueba igualdad entre la proyección Benders-LP completa
y el LP compacto de su partición. Eso no prueba tiempos relativos: una cota
igual o más débil no implica matemáticamente un algoritmo más lento.
Se separan esas predicciones de las propiedades demostradas, sin modificar
las notas históricas o C++. Ver \texttt{AUDITORIA\_DESPACHO.md}.

\textbf{Estado final.} Ambas líneas avanzaron de propuesta a cálculo/prueba.
No hay todavía presupuestos uniformes útiles para los modelos grandes ni un
selector que mejore el despacho. No se incorporó material a OMS v1.3.5.
Se conservaron los seis paquetes anteriores y la versión de envío por hash.
El paquete nuevo incluye protocolo, entradas, código fijado, familias pequeñas
completas, certificados, resultados y replay sin llamadas a solvers. El reporte
se regenera desde los datos; \texttt{VALIDATION.json} registra la extracción limpia.
La comprobación no sustituye una campaña sobre el MILP entero o muchos escenarios.

\small
[1] Peña, Vera y Zuluaga, \emph{New characterizations of Hoffman constants}.
\url{https://arxiv.org/abs/1905.02894}.

[2] Stein, \emph{Error bounds for mixed integer linear optimization problems}.
\url{https://doi.org/10.1007/s10107-015-0872-7}.

[3] Hosseini y Turner, \emph{Deepest Cuts for Benders Decomposition}.
\url{https://arxiv.org/abs/2110.08448}.

[4] Glomb, Liers y Rösel, \emph{A novel Pareto-optimal cut selection strategy}.
\url{https://doi.org/10.1007/s12532-025-00291-1}.

[5] Donkiewicz y Gaul, \emph{Benders Cut Filtering for Affine Potential-Based Flow
Problems with Robustness Scenarios and Topology Switching}, preprint 2026.
\href{https://optimization-online.org/wp-content/uploads/2026/04/donkiewicz2026benderscutfiltering.pdf}{Optimization Online}.
\end{document}
'''.replace('@@BUDGETS@@',budgets).replace('@@TABLE@@',table)
    (HERE/'preventive-dispatch-note.tex').write_text(tex)
    print('Four-page note sources regenerated from verified data')


if __name__=='__main__':main()
