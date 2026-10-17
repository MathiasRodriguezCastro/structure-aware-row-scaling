#!/usr/bin/env python3
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def main():
    d=json.loads((HERE/'analysis.json').read_text());g=d['scenarios'];v=d['independent']
    md='''# Selección de factores considerando exportación: resultados

**Decisión:** se implementó y verificó un selector que amplía las potencias de
dos a todos los multiplicadores binary64 que exportan la fila exactamente.
También se implementó un selector finito que reserva el defecto de exportación
de candidatos redondeados. Hay una mejora de centrado y menos abstenciones
en pruebas artificiales, pero **ninguna admisibilidad adicional en los tres
escenarios físicos solicitados**. No se inicia otra campaña MILP ni se añade
este estudio al artículo. No se afirma novedad histórica.

## 1. Qué se implementó

Para cada dato no nulo, z=signo N_z 2^p_z, con N_z impar. Todo factor binary64
positivo tiene alpha=h 2^k, h impar. El producto es exactamente representable
si y solo si h N_z tiene a lo sumo 53 bits, p_z+k>=-1074 y su mayor exponente
no excede 1023; se comprueban también los límites del propio factor. Por tanto
el significando impar permitido cumple h<=floor((2^53-1)/max N_z).

El selector **Exact** recorre exponentes y, para cada uno, obtiene el intervalo
de significandos impares admisibles. Compara exactamente los vecinos del óptimo
real y los extremos. Encuentra el mínimo global de Q(alpha)=max(alpha M,
1/(alpha m)) sobre todos los factores binary64 de exportación exacta. Q es la
exponencial del objetivo logarítmico de centrado; no es un número de condición.
El RHS participa en la exactitud y representabilidad, no en m/M.

El control **Pow2** restringe h=1. **Rounded** escoge el GM binary64 sin
reserva por exportación. **Aware** compara un conjunto finito declarado: Exact,
Pow2, Rounded, extremos redondeados hacia dentro y ocho vecinos nextafter a cada
lado de Rounded. Conserva solo candidatos que cumplen el contrato completo y
la ventana de coeficientes realmente exportados. Aware no es un óptimo global
entre factores que redondean productos.

Para ahat=fl(alpha a), bhat=fl(alpha b), se calcula exactamente sobre la caja
original rho(alpha)=max_x |(a-ahat/alpha)^T x+bhat/alpha-b|.
El contrato suficiente es epsilon/alpha + E + rho(alpha) <= delta.
La hipótesis epsilon es un límite del residuo efectivamente exportado, no una
promesa de FeasibilityTol. E es la reserva independiente por redondeo entero.
Si un error no nulo multiplica una coordenada sin cota finita, esta prueba de
caja no da una envolvente finita; no se inventan cotas para obtenerla.

## 2. Banco y escenarios reales

Tres modelos SG-Ter-Mer conocidos, 360 períodos, cada uno con 6.120 variables,
10.080 filas y 1.440 variables enteras. Se preservan los datos binary64
canónicos del paquete precision-work. Son 30.240 filas y 12.960 filas físicas
por escenario, incluyendo la extensión documentada de activaciones.
No se vuelven a resolver los modelos ni se cambia el generador.

Ventana [1e-9,1e9], epsilon=1e-6 y E=1e-9 sum_entero |a_j|, con las entradas
binary64 del padre. Los objetivos físicos son exigente (.01 MW,100 m3),
referencia (.1 MW,1000 m3) y permisivo (1 MW,10000 m3). Se convierten a unidades
algebraicas fila a fila. No son tolerancias establecidas por UTE.

| Escenario | Filas | Pow2 cumple | Exact cumple | Aware cumple | Exact cambia respecto de Pow2 |
|---|---:|---:|---:|---:|---:|
'''
    for name in ['Demanding','Reference','Permissive']:
        x=g[name];md+=f"| {name} | {x['rows']} | {x['Pow2']['contract_pass']} | {x['Exact']['contract_pass']} | {x['Aware']['contract_pass']} | {x['exact_changed_from_pow2']} |\n"
    md+='''
Sin presupuesto, Exact cambia 5.364/30.240 factores (17,74 %), todos con defecto
de exportación cero. La mediana del cociente Q_Exact/Q_Pow2 sobre todas las
filas es 1; el mejor cociente es 0,70710678. Una mejora de Q no prueba una
mejora de condición, de solución o de trabajo del solver. En cada escenario
físico cambia 2.160/12.960 factores, sin rescatar ningún contrato.

En 17.773/30.240 filas, las potencias de dos son los únicos multiplicadores
exactos posibles incluso antes de imponer el intervalo. En otras filas existen
significandos impares mayores que 1. Por ejemplo, a1_cota_altura_4(1) de
instance001 pasa de factor 32 a 36, con todos los productos exactos.
No hay una garantía de invariancia ante reemisión arbitraria: la representación
de los datos puede modificar el conjunto de multiplicadores exactos.

Rounded también cumple todos los contratos físicos de este banco. Su máximo
defecto de exportación dividido por el presupuesto restante es 1,732e-8 en el
escenario exigente, 1,535e-9 en referencia y 1,517e-10 en permisivo. Este dato
explica por qué reservarlo explícitamente no rescata casos aquí; no dice que
el defecto sea despreciable en cualquier problema.

En el banco completo sin presupuestos, 4.320 filas falla_tramo no tienen una
envolvente finita del defecto sobre la caja almacenada para Rounded. Intervienen
variables con cotas infinitas en el modelo importado. Es una limitación del
certificado por caja, no prueba de error infinito en la región factible: otras
restricciones podrían proporcionar cotas. La exportación exacta evita ese
defecto sin necesitar tales cotas.

## 3. Sensibilidad construida con intervalos estrechos

Se reemplaza el presupuesto de cada fila física por delta=E+epsilon/(theta H),
con H=1e9/M. Son presupuestos artificiales dependientes de la fila. No se mezclan
con los tres escenarios físicos ni se presentan como necesidades del despacho.

| theta | Filas | Pow2 admite | Exact admite | Abstenciones evitadas |
|---|---:|---:|---:|---:|
'''
    for theta,x in d['constructed_stress'].items():md+=f"| {theta} | {x['rows']} | {x['pow2_admissible']} | {x['exact_admissible']} | {x['exact_rescues']} |\n"
    md+='''
En theta=1, por ejemplo, las filas físicas con coeficientes de magnitud 1
exigen alpha=1e9. Ese número es binary64 exacto y sus productos por +/-1 son
exactos, pero no es potencia de dos. Se evitan 3.240 abstenciones: filas
g4h_def, gh_total y gen_menor_demanda. El presupuesto residual correspondiente
es del orden de 1e-15 MW, lejos del escenario exigente solicitado de .01 MW.
Esto ilustra una limitación de la grilla conservadora; no descubre una necesidad
práctica ni refuta el certificado de incompatibilidad para factores reales.
El selector del paper ya distingue abstención dyádica de intervalo real vacío.

## 4. Verificación y alcance

'''
    md+=f"El verificador independiente comprobó {v['factor_decisions_checked']:,} decisiones, {v['native_product_checks']:,} productos, {v['complete_optimality_checks']:,} condiciones de optimalidad discreta y {v['stress_interval_checks']:,} intervalos de estrés.\n"
    md+='''
La optimalidad se verifica excluyendo la existencia de un factor con mejor Q,
sin reutilizar el minimizador del productor. Se validan también 14.000
comparaciones exhaustivas en un formato binario pequeño, 300 pares binary64
con límites de exponente y cinco tests. Se corrigió un contador agregado después
de la primera corrida; los dos archivos de decisiones conservaron exactamente
sus hashes. Ver IMPLEMENTATION_NOTES.md. No se modificó ninguna política.

Los datos canónicos se incluyeron en el paquete. Su procedencia y hashes quedan
fijados; el estudio padre ya comprobó su identidad con los LP originales. Este
paquete no vuelve a importar esos LP ni ejecuta un solver. La medición de costo
es tiempo del script con caché y verificaciones; no es rendimiento MILP.

## 5. Revisión de los límites conjuntos y decisión para OMS

LITERATURA.md amplía la revisión: la homogeneización fraccional tiene un
antecedente explícito en Charnes–Cooper (1962), y el mínimo libre por filas y la
invariancia de Skeel ya eran clásicos. Se revisaron las reformulaciones de
precondicionamiento diagonal de Qu et al.; trabajan con condición espectral y
no certifican ni descartan prioridad de la extensión acotada en norma infinito.
La novedad específica continúa sin establecerse. La ausencia de un caso real
útil sigue siendo el límite práctico principal.

**Resultado tangible:** ahora existe un selector completo de factores de
exportación exacta y otro selector finito que verifica la reserva de exportación.
La mejora observada se limita a centrado y estrés construido. No hay evidencia
suficiente para otra contribución al paper ni para invertir en una campaña de
solver sobre estos escenarios. La versión OMS v1.3.5 y los diez paquetes previos
se preservan por SHA256. El diagnóstico LP–DW entero y el predictor validado
siguen pendientes y no se confunden con esta exploración.
'''
    (HERE/'RESULTADOS.md').write_text(md)
    tex=r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,amsmath,amssymb,booktabs,tabularx}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\begin{document}
\begin{center}\Large Exact row multipliers beyond powers of two\\[3pt]
\normalsize Independent exploration for OMS --- 15 October 2026\end{center}
\textbf{Decision.} A complete exact-product selector and a finite export-aware
selector are implemented and checked. They improve coefficient centering and
avoid some abstentions in constructed narrow intervals. Neither admits any
additional contract in the three requested physical scenarios. There are no
new solver calls, performance claims or manuscript additions.

\section*{1. Complete exact-product selection}
Write every nonzero row datum, including the right-hand side, as
$z=\operatorname{sign}(z)N_z2^{p_z}$, with $N_z$ odd. Write a positive
binary64 factor uniquely as $\alpha=h2^k$, $h$ odd. Assuming gradual underflow,
all products are exactly representable if and only if, for every datum,
\[
 hN_z\le 2^{53}-1,\qquad p_z+k\ge-1074,\qquad
 p_z+k+\lfloor\log_2(hN_z)\rfloor\le1023,
\]
and the factor itself is representable. Thus $h\le
\lfloor(2^{53}-1)/\max_z N_z\rfloor$. Exponent and interval limits leave an
interval of odd integers $h$ at each exponent. For
\[
 Q(\alpha)=\max\{\alpha M,1/(\alpha m)\},\qquad
 m=\min_{a_j\ne0}|a_j|,\quad M=\max_j|a_j|,
\]
the endpoints and the neighbors of the real optimum suffice. Exact rational
comparisons produce a global minimum on the full exact-export set. The
power-of-two control restricts $h=1$. These are elementary consequences of
binary representation; historical novelty is not claimed. $Q$ is the
exponential of the logarithmic centering objective, not a condition number.

\section*{2. Reserving rounded-export error}
For $\widehat a=\operatorname{fl}(\alpha a)$ and
$\widehat b=\operatorname{fl}(\alpha b)$, compute exactly on the stored box $X$
\[
 \rho(\alpha)=\max_{x\in X}
 \left|(a-\widehat a/\alpha)^Tx+\widehat b/\alpha-b\right|.
\]
An exported residual at most $\epsilon$ and an integer-rounding allowance $E$
give the sufficient original-row guarantee
$\epsilon/\alpha+E+\rho(\alpha)\le\delta$.
The exported residual is a hypothesis to verify, not a consequence of setting
a solver tolerance. A nonzero export error on an unbounded coordinate makes
this box certificate inconclusive; other model rows might supply bounds.

The finite \textit{Aware} pool contains full exact GM, power-of-two GM,
binary64 GM, inward endpoints, and eight adjacent floats on either side of
binary64 GM. Candidates must meet the full contract and actual exported
coefficient limits. This finite search is not globally optimal among rounded
exports. Original rows, columns, bounds, objectives and integrality are fixed.

\section*{3. Validation scope}
Three known SG--Ter--Mer models retain 1,440 integer variables each. This is
one family, not external validation. The complete selector is checked by
excluding every strictly better factor with a separate feasibility program.
Five tests, 14,000 exhaustive toy-format comparisons and 300 binary64 boundary
pairs supplement the original-data replay. No optimizer is imported or run.
\newpage
\section*{4. Real contracts: no additional admissibility}
All 30,240 rows are audited. Each physical scenario covers 12,960 rows,
including the previously documented activation extension. The coefficient
window is $[10^{-9},10^9]$, $\epsilon=10^{-6}$, and
$E=10^{-9}\sum_{j\in J}|a_j|$, using the parent's binary64 inputs.
Physical budgets are converted to each row's algebraic units. They are study
accuracy targets, not operating standards.

\begin{center}\small
\begin{tabular}{lrrrr}\toprule
Scenario (MW, m$^3$)&Rows&Pow2 passes&Exact passes&Aware passes\\\midrule
Demanding (.01, 100)&12960&12960&12960&12960\\
Reference (.1, 1000)&12960&12960&12960&12960\\
Permissive (1, 10000)&12960&12960&12960&12960\\\bottomrule
\end{tabular}\end{center}

Without budgets, full exact GM changes 5,364/30,240 factors (17.74\%) while
retaining zero export defect. The median $Q_{\rm Exact}/Q_{\rm Pow2}$ over all
rows is 1; the best ratio is 0.70710678. For example, a stored height row changes
from factor 32 to 36 with all products exact. Each physical scenario changes
2,160/12,960 factors but rescues no contract.

In 17,773 rows, the only possible exact multipliers are powers of two, even
before interval limits. In other rows, short odd significands permit more
choices. Arbitrary re-emission can change this set: full invariance under
arbitrary changes of units is not established for the discrete selector.

Binary64 GM without an export reserve also passes every physical contract.
The maximum export defect divided by remaining budget is $1.732\cdot10^{-8}$
in the demanding scenario, $1.535\cdot10^{-9}$ in the reference scenario, and
$1.517\cdot10^{-10}$ in the permissive scenario. Reserving this defect is
therefore nonbinding here. Over the full unbudgeted bank, 4,320 cost-envelope
rows have an unbounded box defect for rounded GM because affected coordinates
lack finite stored bounds. This is a limitation of the box certificate, not
proof of unbounded error over the feasible region. Exact exports avoid it.

\section*{5. Constructed narrow-interval sensitivity}
For each physical row set $\delta=E+\epsilon/(\theta H)$, $H=10^9/M$.
These artificial targets are separate from application scenarios.

\begin{center}\small
\begin{tabular}{lrrrr}\toprule
$\theta$&Rows&Pow2 admits&Exact admits&Abstentions avoided\\\midrule
1/2&12960&12960&12960&0\\
3/4&12960&5400&8640&3240\\
7/8&12960&1080&4320&3240\\
15/16&12960&1080&4320&3240\\
1&12960&0&3240&3240\\\bottomrule
\end{tabular}\end{center}

At $\theta=1$, rows with coefficient magnitudes 1 require factor $10^9$,
which is binary64-exact but not a power of two. This rescues 3,240 power rows.
Their residual target is around $10^{-15}$ MW, far below the requested
0.01 MW. This demonstrates a grid limitation, not a practical dispatch need
or an incompatibility of the real-factor interval. The manuscript already
distinguishes exact-grid abstention from real-interval incompatibility.
\newpage
\section*{6. Joint limits: what the literature review establishes}
The earlier joint-limits note treats a fixed nonsingular square matrix in the
infinity norm, with fixed columns and factor boxes. It does not certify the
solver's internally scaled matrix, all LP bases, or general MILP performance.
Its unrestricted minimum and Skeel invariance are classical; see
\href{https://eprints.maths.manchester.ac.uk/651/1/SURVEY.pdf}{Higham (1994),
equations 2.11--2.12}. They must not be presented as discoveries.

The new literature check examined
\href{https://iiif.library.cmu.edu/file/Cooper_box00010_fld00009_bdl0001_doc0001/Cooper_box00010_fld00009_bdl0001_doc0001.pdf}{Charnes--Cooper (1962), pp. 181--184}.
Homogenizing positive fractional variables into linear constraints is an
established technique. The previous substitution $v=t/\alpha$ is an instance
of that approach, not a new general optimization method. This does not imply
that the 1962 article solves the particular boxed row-scaling problem.

\href{https://arxiv.org/html/2209.00809v2}{Qu et al., sections 1, 2.1 and 3.1}
study optimal diagonal preconditioning in the spectral norm through
quasiconvex and SDP reformulations. Their formulations include diagonal
restrictions, but do not prove our boxed infinity-norm formula. The historical
priority of that specific extension remains unestablished; a limited search
cannot settle it. More importantly, no real instance has shown that the joint
certificate changes a useful dispatch decision.

For the present exact-export implementation,
\href{https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html}{Goldberg (1991)}
provides the standard binary-arithmetic background.
\href{https://ojs.aaai.org/index.php/AAAI/article/view/16482/16289}{Berthold--Hendel
(2021), p. 3662}, explicitly describe power-of-two scaling to avoid data error.
These precedents support the controls and limit novelty claims. Neither paper
is cited as a proof of our complete discrete selector.

\section*{7. Reproduction and editorial decision}
'''
    tex+=f"The independent replay checks {v['factor_decisions_checked']:,} factor decisions, {v['native_product_checks']:,} products, {v['complete_optimality_checks']:,} discrete optimality conditions, and {v['stress_interval_checks']:,} constructed intervals.\n"
    tex+=r'''
Canonical model inputs and exact decisions are included in the package. Their
identity to original LP exports was checked in the pinned parent study; this
study does not re-import LPs. A derived counter was corrected after the first
run: the odd-significand limit 2 also permits only 1. Factor decisions and
stress outputs retained identical hashes. The original source, correction
note and before/after hashes are retained.

The reported selection time includes caching, metadata and rational checks;
it is not MILP solution work. Complete replay requires Python, pytest and
pdfLaTeX, without optimizer libraries or licences. The frozen OMS v1.3.5
delivery and ten earlier research packages are checked unchanged by SHA256.

\textbf{Conclusion for this exploration.} Full exact multipliers give a
verified software extension and fewer grid abstentions under constructed
targets. The requested physical contracts show no additional admissibility.
There is no evidence here for better MILP performance or for another OMS
contribution. No solver campaign is launched and the manuscript is unchanged.
The original-integer LP--DW diagnosis and a validated predictive selector
remain separate outstanding tasks.
\end{document}
'''
    (HERE/'exact-factor-note.tex').write_text(tex)
    print('Spanish report and three-page note regenerated')


if __name__=='__main__':main()
