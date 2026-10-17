#!/usr/bin/env python3
from pathlib import Path
import json
from common import load

HERE=Path(__file__).resolve().parent


def main():
    a=load(HERE/'analysis.json');v=load(HERE/'independent-verification.json')
    md='''# Incumbente común y efecto del escalamiento: resultados para OMS

**Pregunta del artículo:** ¿cuánto del beneficio observado del escalamiento
externo depende del acceso temprano a un incumbente, aun con escalamiento
interno y presolve normales?

**Resultado:** en los dos casos conocidos donde GM ayudaba, proporcionar un
incumbente común hace que Base pase de 0/3 a 3/3 terminaciones nativas y elimina
la ventaja de terminación de GM. En instance001, GM usa más trabajo en las tres
semillas con Start común. En instance003, las diferencias de trabajo tienen
signos mezclados. Esto aporta una explicación acotada para la contribución A
de OMS, sin proponer un algoritmo ni demostrar superioridad general.

## Diseño y control

Tres modelos conocidos del generador SG-Ter-Mer, 360 períodos, 6.120 variables,
10.080 filas y 1.440 binarias cada uno. Se eligieron retrospectivamente dos
casos favorables a GM (001,003) y un control donde costaba más (042). Son
diagnósticos, no validación externa ni muestra aleatoria. Se mantiene el modelo
canónico MPS del estudio de mecanismos, con todos sus enteros originales.
Este banco auxiliar usa GM en potencias de dos y sus salvaguardas congeladas.
No reproduce el exportador LP ni todos los factores de la campaña histórica
del artículo; el diagnóstico no atribuye retrospectivamente su ganancia de
trabajo a una causa única.

Cada caso tiene Base/GM x Cold/CommonStart x semillas nuevas 503,509,521:
36 MILP secuenciales. Parámetros iguales: Gurobi 13.0.2, cuatro hilos, 12 s y
12 unidades de trabajo, gap .001, tolerancias primal 1e-6 e integral 1e-5,
IntegralityFocus=0, presolve y escalamiento interno automáticos. No se usan
como comparación las configuraciones que desactivaban mecanismos internos.

Por caso se toma el patrón de GM archivado con semilla 307 y se resuelve una
sola continuación LP racional, máximo 15 s. Las tres producen óptimos exactos
del LP con enteros fijados. No son óptimos MILP certificados. El punto racional
se convierte a binary64 para Start; ambas representaciones reciben exactamente
el mismo vector. Se verifican sus residuos originales/exportados, cotas y
enteros. Los 18 Start se cargan y se observa su patrón y costo en los candidatos.

## Resultados, sin razones de velocidad sobre corridas censuradas

Cada celda indica terminaciones al criterio nativo / 3 y mediana del trabajo
de las tres llamadas, incluidas las censuradas. No es una tabla de velocidad
a optimalidad exacta ni de resultados con cotas MILP certificadas.

| Caso | Inicio | Base: termina; trabajo | GM: termina; trabajo |
|---|---|---:|---:|
'''
    for instance,gs in a['groups'].items():
        for mode,ps in gs.items():
            md+=f"| {instance} | {mode} | {ps['Base']['native_completions']}/3; {ps['Base']['median_work']:.4f} | {ps['GM']['native_completions']}/3; {ps['GM']['median_work']:.4f} |\n"
    md+='''
Con inicio común y calidad comparable, los cocientes apareados GM/Base en 001
son 1,0555; 1,0519; 1,3686 (mediana 1,0555). En 003 son 0,9957; 1,1114;
0,7683 (mediana 0,9957). No se hace una prueba estadística poblacional con tres
semillas ni se agrupan velocidades de distintos modelos. En 042 ambos métodos
reportan cero unidades de trabajo con el Start: no se divide por cero ni se
interpreta ese contador como costo total nulo. Hay construcción, carga y
adquisición del punto fuera del contador nativo.

En los pares con relajación raíz impresa, su objetivo coincide entre Base y GM
para cada caso, modo y semilla: 15/15 pares. La precisión impresa no certifica
igualdad exacta ni el óptimo LP. El Start cambia algunos objetivos raíz frente
a Cold, por lo que tampoco se afirma que la intervención deje intacta toda la
tubería interna. En 042 con Start no se ejecuta una relajación raíz registrada.

**Interpretación:** la ventaja de terminación observada está condicionada por
el acceso al incumbente. El escalamiento cambia la trayectoria de búsqueda;
el beneficio no puede atribuirse solo a la condición de la matriz exportada.
Un Start también cambia cortes por objetivo, presolve y búsqueda posterior:
no se identifica una heurística específica ni se prueba que sea la única causa.
Estos datos no prueban una ventaja adicional de la información del generador.

## Adquisición y comprobación exacta

Los puntos iniciales no son una entrada gratuita de un algoritmo nuevo. Los
patrones provienen de resoluciones GM previas; su continuación racional tarda
lo siguiente, incluyendo exportación y chequeo del LP:

| Caso | Costo exacto factible, aprox. | Adquisición LP nueva, s | Trabajo GM archivado que obtuvo el patrón |
|---|---:|---:|---:|
'''
    for instance,ref in a['references'].items():
        old=load(HERE/'inputs'/instance/'Algebraic-archived.json.gz')
        md+=f"| {instance} | {float(__import__('fractions').Fraction(ref['objective_exact'])):.6f} | {ref['acquisition_seconds']:.3f} | {old['work']:.4f} |\n"
    md+='''
No se suman costos de campañas distintas para anunciar una aceleración, ni se
omite el costo de encontrar el patrón como si el Start se obtuviera gratis.
La intervención es un diagnóstico con información fuera de línea.

Se conserva una cola fijada antes de comprobar todos los patrones finales
únicos: 15 LP, límite de 5 s, sin sustituciones. Trece tienen óptimos de patrón
certificados; dos quedan unknown por el límite. Ambos desconocidos corresponden
a Base-Cold de 001, donde no hubo terminación al gap solicitado. Se retienen
como desconocidos. Las comparaciones Warm tienen continuaciones exactas y
costos comparables. Ninguna cota reportada supera el testigo común en este
experimento; la ausencia de contradicción no certifica las cotas.

'''
    md+=f"El verificador independiente reconstruye las {v['native_lp_reference_calls']} referencias y los {v['native_lp_posthoc_calls']} LP de patrones desde las filas originales; comprueba duales y primales racionales, {v['exact_product_checks']:,} productos exactos, {v['candidate_exact_objective_checks']} objetivos de candidatos y los residuos de los {v['final_original_row_replays']} puntos finales. Verifica las 18 cargas del patrón/costo común y las 36 asignaciones a patrones. Cuatro tests pasaron antes de las llamadas MILP.\n"
    md+='''
## Decisión para OMS

Este resultado pasa el filtro temático: esclarece una afirmación central sobre
el mecanismo del escalamiento y su dependencia de la trayectoria del solver.
Merece un párrafo corto de evidencia, sin anunciar otra contribución principal.
No es razón para reabrir DW, cortes, predictores ni otra campaña de tiempos.
Se deja PAPER_INSERT_CANDIDATE.tex como texto concreto, sujeto al mismo nivel
de cautela que el manuscrito. La versión congelada OMS v1.3.5 no se modifica
en esta exploración. Los once paquetes previos se preservan por hashes.

La evidencia se limita a tres casos conocidos, un solver/version y límites
breves. La aceptación nativa y la calidad de los patrones se distinguen de una
prueba global MILP. El estudio apoya una atribución acotada; no demuestra que
el escalamiento solo afecte heurísticas ni que el Start sea un método superior.

Referencia de API: [Gurobi, atributo Start](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html#attr:Start).
El proveedor describe un intento de construir un incumbente, no una garantía
de carga; de ahí la comprobación adicional de logs, patrón y costo.
'''
    (HERE/'RESULTADOS.md').write_text(md)
    candidate=r'''An auxiliary MPS-based diagnostic with power-of-two GM factors further
limits mechanism attribution.
On three known dispatch cases with three new seeds, Base and GM receive the
same independently checked feasible reference as a MIP start. In the two cases
where cold-start GM reaches the requested native gap in 3/3 calls while Base
reaches it in 0/3, the common start makes both reach it in 3/3. GM then requires
more work in all three pairs on one case and has mixed work differences on the
other. This diagnostic conditions on an offline reference; it is not a new
solution method or a global optimality certificate. It shows that the observed
completion advantage depends on incumbent access and cannot be attributed to
exported-matrix conditioning alone; it does not isolate a particular heuristic.
'''
    (HERE/'PAPER_INSERT_CANDIDATE.tex').write_text(candidate)
    tex=r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,amsmath,booktabs,tabularx}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}
\begin{document}
\begin{center}\Large Common incumbents and row-scaling attribution\\[3pt]
\normalsize Focused exploration for OMS --- 15 October 2026\end{center}
\textbf{Question.} How much of the observed external-scaling benefit survives
when Base and GM receive the same feasible incumbent? This addresses mechanism
attribution in the existing paper, without introducing cuts, decomposition,
prediction or a new preconditioner.

\section*{1. Controlled intervention}
Three known SG--Ter--Mer cases retain 6,120 variables, 10,080 rows and 1,440
binaries each. Cases 001 and 003 previously favored GM; case 042 favored Base.
This is retrospective diagnosis in one family, not held-out validation.
Base/GM $\times$ Cold/CommonStart $\times$ seeds 503,509,521 gives 36 sequential
MILP calls. Gurobi 13.0.2 uses four threads, 12 seconds/12 work units, gap
$10^{-3}$, primal tolerance $10^{-6}$, integer tolerance $10^{-5}$, normal
presolve/internal scaling and IntegralityFocus=0. Frozen exact row factors are
reused; objectives, domains and the underlying mathematical models are fixed.
This auxiliary MPS/power-of-two bank differs from the historical LP campaign;
it does not establish the cause of that campaign's reported work reduction.

For each case, only the integer pattern of archived GM seed 307 is used.
SoPlex produces an exact feasible continuation and a matching dual bound for
the fixed-pattern LP. This certifies that LP, not global MILP optimality.
The rational point is converted to one binary64 vector supplied identically to
both policies. All 18 starts are loaded and their pattern/cost is observed.
Original/exported residuals from conversion are retained separately.

\section*{2. Completion and work}
Each cell gives native completions out of three and median native work over
all three calls, including censored ones. Ratios of censored runs are not
interpreted as speedups; native completion is not a certified MILP gap.
\begin{center}\small
\begin{tabular}{llrr}\toprule
Case&Initialization&Base: completes; work&GM: completes; work\\\midrule
'''
    for instance,gs in a['groups'].items():
        for mode,ps in gs.items():
            tex+=f"{instance.replace('instance','')}&{mode}&{ps['Base']['native_completions']}/3; {ps['Base']['median_work']:.4f}&{ps['GM']['native_completions']}/3; {ps['GM']['median_work']:.4f}\\\\\n"
    tex+=r'''\bottomrule\end{tabular}\end{center}
The common start removes the completion advantage of GM in both favorable
cases. In 001, paired GM/Base work ratios are 1.0555, 1.0519 and 1.3686; GM
requires more work in all three pairs. In 003 the ratios are 0.9957, 1.1114 and
0.7683, with mixed signs. The zero native-work reports for warm 042 do not mean
zero total cost and are not divided into ratios. No root LP is logged there.

Root objectives match at printed precision within all 15 Base/GM pairs where
root relaxations are logged. The start changes some root objectives relative
to Cold: it can alter objective cutoffs, presolve and later search. Therefore
the intervention supports dependence on incumbent access, without isolating
one heuristic or proving that all effects have that cause.
\newpage
\section*{3. Acquisition and exact checks}
The references are offline diagnostic inputs. Their patterns came from
previous GM runs; the new exact LP construction/check took 1.79--1.84 seconds
per case, separate from the earlier work needed to obtain those patterns.
This is not a deployable algorithm with free starts, nor a total-time speedup.

All 15 unique final integer patterns entered a queue fixed before posthoc LP
checking (five-second limit, no replacement). Thirteen have exact primal/dual
optima. Two remain unknown, both from Base-Cold 001, which did not reach the
requested gap. Warm comparisons have certified continuations at comparable
costs. Conditional pattern optima are not global MILP lower bounds.

No reported bound exceeds the common exact feasible objective in this
experiment. Absence of contradiction is not validation of global bounds.
All native candidates and logs are retained. Original-row checks use stored
binary64 coefficients and rational arithmetic after integer rounding; they do
not certify an intended pre-rounding physical model.

'''
    tex+=f"The independent replay checks {v['exact_product_checks']:,} exact products, {v['candidate_exact_objective_checks']} candidate objectives, all 36 final points and pattern assignments, all 18 loaded common starts, three reference LPs and 15 final-pattern LPs. Four tests passed before MILP calls.\n"
    tex+=r'''
\section*{4. What this contributes to OMS}
The result directly tests a mechanism behind the paper's observed operational
effects. It supports a short qualification of existing evidence, rather than
another principal contribution or a claim that scaling strengthens the LP.
No extra campaign is warranted by these three known cases.

\textit{Concrete candidate paragraph:}

'''+candidate.replace('cold-start','cold-start')+r'''

\section*{5. Limits and reproducibility}
One application family, three selected cases, one solver/version and short
limits cannot establish a general ranking. A common start affects the whole
solver pipeline. Its acceptance is checked because the
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html#attr:Start}{Gurobi Start API}
does not guarantee that a supplied vector becomes an incumbent. The incumbent
source is fully declared and is not used to train a predictive rule.

The package contains canonical inputs, source provenance, archived discovery
records, exact references, schedules, native logs, candidates, fixed-pattern
LPs, rational certificates and solver-free replay. Python, NumPy and pytest
suffice for checks; pdfLaTeX builds this note. New solves additionally require
the declared Gurobi and GMP-enabled SoPlex binaries/licences. The manuscript,
frozen OMS v1.3.5 delivery and eleven previous research archives are preserved.
\end{document}
'''
    (HERE/'root-attribution-note.tex').write_text(tex)
    print('Focused OMS report and candidate paragraph regenerated')


if __name__=='__main__':main()
