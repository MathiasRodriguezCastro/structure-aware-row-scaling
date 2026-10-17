#!/usr/bin/env python3
"""Generate the focused note and supplement tables from independently checked data."""
import csv
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def main():
    rows=list(csv.DictReader((HERE/'verified-runs.csv').open()))
    summary=list(csv.DictReader((HERE/'verified-summary.csv').open()))
    assert len(rows)==12 and len(summary)==4
    v=json.loads((HERE/'VALIDATION.json').read_text())
    assert v['first_pass_native_outcomes_and_points_identical']
    budget_work=[float(r['work']) for r in rows if r['policy']=='Budget-L2' and r['focus']=='0']
    assert sorted(int(r['seed']) for r in rows if r['policy']=='Budget-L2' and r['focus']=='0')==[11,23,47]
    assert f'{statistics.geometric_mean(budget_work):.3f}'=='4.485'
    assert f'{statistics.median(budget_work):.3f}'=='4.975'
    accuracy=[r'\begin{tabular}{lrrrrrr}',r'\toprule',
        r'Policy & Calls & Budgets & Max. $v_V$ (m$^3$) & $B>U$ & Gap flags & Work\\',r'\midrule']
    timing=[r'\begin{tabular}{lrrrrrr}',r'\toprule',
        r'Policy & Generate & Select/export & Import/check & Solve & Verify & Total\\',r'\midrule']
    md='''# IntegralityFocus y costo completo: resultado para OMS

15 de octubre de 2026. Un caso retrospectivo, no una validación externa.
Aclaración editorial de agregación: 16 de octubre de 2026.

**Resultado útil:** IF1 no elimina la violación de L2 en este contraste. En los
seis pares IF0/IF1 coinciden exactamente los puntos guardados, los objetivos,
las cotas y las unidades de trabajo. Todas las coordenadas enteras devueltas son
exactamente integrales, por lo que este resultado no muestra un error de redondeo
entero corregido por IF1. Es un control negativo pertinente, no una afirmación de
inutilidad general del parámetro.

## Precisión y afirmaciones del solver

| Política | Llamadas | Cumple presupuestos | Máximo volumen, m³ | Cotas contradichas | Finalizaciones contradichas | Mediana Work |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    timings=[]
    for s in summary:
        policy=s['policy'];focus=int(s['focus']);label=f'{policy}, IF{focus}'
        maximum=float(s['maximum_activation_m3'])
        shown=f'{maximum:,.3f}' if maximum>=1 else f'${maximum/1e-5:.3f}\\times10^{{-5}}$'
        accuracy.append(f"{label} & 3 & {s['budgets_passed']}/3 & {shown} & {s['bound_contradictions']} & {s['completion_contradictions']} & {float(s['median_work']):.3f}\\\\")
        selected=[r for r in rows if r['policy']==policy and int(r['focus'])==focus]
        values=[statistics.median(float(r['generator_construction_base_export_seconds']) for r in selected),
            statistics.median(float(r['factor_selection_seconds'])+float(r['scaled_export_seconds']) for r in selected),
            statistics.median(float(r['native_environment_import_parameters_seconds'])+float(r['native_import_check_seconds']) for r in selected),
            statistics.median(float(r['solve_seconds']) for r in selected),
            statistics.median(float(r['verification_seconds']) for r in selected),
            statistics.median(float(r['total_seconds']) for r in selected)]
        timings.append((label,values))
        timing.append(label+' & '+' & '.join(f'{x:.3f}' for x in values)+r'\\')
        md+=f"| {label} | 3 | {s['budgets_passed']}/3 | {maximum:.9g} | {s['bound_contradictions']}/3 | {s['completion_contradictions']}/3 | {float(s['median_work']):.6f} |\n"
    for lines in (accuracy,timing):lines.extend([r'\bottomrule',r'\end{tabular}'])
    (HERE/'if1-accuracy.tex').write_text('\n'.join(accuracy)+'\n')
    (HERE/'workflow-cost.tex').write_text('\n'.join(timing)+'\n')
    md+='''
El presupuesto exigente es 100 m³ y 0,01 MW. L2 viola la activación en
4.837,338 m³; Budget-L2 la limita a 1,4782e-5 m³. Budget mantiene dos cotas
contradichas de tres, aunque ninguna finalización al 1 % queda contradicha por
estos testigos. Ausencia de contradicción no certifica cotas ni optimalidad.
L2 presenta tres cotas y tres finalizaciones contradichas. No se comparan como
optimizaciones exitosas equivalentes por el solo hecho de terminar rápido.

**4,485 y 4,975 son compatibles.** Las unidades de trabajo Budget-L2 por semilla
11/23/47 son 3,6054776613; 4,9754950464; 5,0281587478, iguales a las de la campaña
anterior sin presolve. Su media geométrica es 4,4847271866 (4,485 en Tabla 11 histórica de v1.3.8 y
Tabla S12); su mediana es 4,9754950464 (4,975 en esta nota y Tabla S15).
La diferencia procede del resumen estadístico, sin cambiar configuraciones ni datos.

## Costo completo medido

Medianas, segundos; tres llamadas por celda, sin amortizar construcción.

| Política | Generar | Seleccionar/exportar | Importar/cotejar | Resolver | Verificar | Total del proceso |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    for label,values in timings:md+='| '+label+' | '+' | '.join(f'{x:.3f}' for x in values)+' |\n'
    md+='''
Generar incluye lanzamiento C++, lectura de entrada, construcción única y escritura
Base. Total mide un proceso Python nuevo e incluye también imports, lectura de
modelos, metadatos, comprobaciones de integridad, extracción y persistencia. Esas
etapas adicionales están desglosadas en verified-runs.csv: las columnas visibles
no cubren por sí solas todo el total, y las medianas no tienen por qué sumar.
El costo es del prototipo sobre una máquina compartida; no establece una ventaja
computacional general ni un costo de producción. Compilación y adquisición de
testigos son costos fuera de línea. Se conserva el tiempo de revalidación de dos
testigos en pre-incorporation-validation.json, separado del ciclo.

## Diseño, enmienda y comprobación

instance046, generador C++ original; 6.120 variables, 10.080 filas y 1.440 binarias.
Gurobi 13.0.2, cuatro hilos, 120 s, gap 1 %, presolve desactivado y escalado interno
automático; tolerancias primal 1e-6 y entera 2^-28; semillas 11,23,47. L2/Budget
reproducen exactamente los archivos históricos antes de cada llamada. No hay MIP
starts ni cambios de formulación, objetivo, cotas o dominios.

Doce tratamientos de la pasada principal. Una primera pasada completa se conserva
en first-pass/. Después se corrigió una copia repetida de vectores en el cotejo de
importación y se repitieron todos los tratamientos. Hubo 24 llamadas MILP nuevas,
sin nuevos LP de referencia. Los resultados nativos y puntos de ambas pasadas
coinciden exactamente. No se cuenta la repetición instrumental como otra muestra.

El checker separado no importa study.py ni Gurobi, y no optimiza. Revalida los dos
testigos completos con aritmética racional sobre 20.160 filas, 12.240 variables y
2.880 dominios enteros; comprueba 103.680 pares fila/punto físicos antes/después
de redondear. Los certificados corresponden al mismo hash de modelo importado.
Cuatro tests comprueban cancelación exacta, activaciones al redondear y refutaciones
de cotas/gap con objetivos negativos y márgenes de presentación.

## Decisión editorial

El control IF1 cierra una objeción concreta y justifica una frase en 7.9, con los
resultados y costos en el suplemento. No crea una tercera contribución. El abstract
y la introducción se conservan; el cierre editorial v1.3.8 también simplifica la carta.
No se amplía la campaña de mecanismos ni
se reclama generalidad a partir de un solo caso.
'''
    (HERE/'RESULTADOS.md').write_text(md)
    tex=r'''\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}
\usepackage[margin=2cm]{geometry}\usepackage{booktabs,amsmath,hyperref}
\begin{document}
\title{IntegralityFocus and the complete scaling workflow}
\author{Auxiliary OMS investigation}\date{16 October 2026: aggregation clarification}\maketitle
\noindent\textbf{Finding.} On the known instance046 with presolve off, IF1 and IF0
return identical points, objectives, bounds and work in all six matched comparisons.
All returned integer coordinates are exactly integral. L2 retains a 4,837.338\,m$^3$
activation violation; Budget-L2 limits it to $1.4782\times10^{-5}$\,m$^3$. This is
a pertinent control, not evidence that IF1 is generally ineffective.

\paragraph{Design.} Two policies, two IF settings and seeds 11, 23, 47: twelve
principal calls. Each fresh process generates the original C++ model once, selects
factors, exports, imports, solves and verifies. All Base/scaled exports reproduce
the historical SHA-256 values. Gurobi 13.0.2 uses four threads, 120 seconds, 1\% gap,
presolve off, automatic scaling, primal tolerance $10^{-6}$ and integer tolerance
$2^{-28}$. No MIP starts, factor changes after observation or new reference LPs.

\paragraph{Accuracy and native reports.} Demanding study targets are 0.01 MW and
100 m$^3$, not operator standards. Budgets counts original-unit checks after integer
rounding. $B>U$ compares a reported lower bound with an exactly feasible objective
of the same imported file, allowing $\max(10^{-6},8\operatorname{ulp}(B))$.
Gap flags contradict a native 1\% completion when $U<C-0.01|C|$.
Unflagged reports do not certify optimality. Work is the median of all three calls.
\begin{center}\small
\input{if1-accuracy.tex}
\end{center}
Budget retains two contradicted bounds of three despite no flagged completion
at the requested 1\% gap. Native termination and primal accuracy are separate.

\paragraph{Why 4.485 and 4.975 agree.} The Budget-L2 Work values for seeds 11/23/47
are 3.6054776613, 4.9754950464 and 5.0281587478, identical to the earlier
presolve-off campaign. Their geometric mean is 4.4847271866 (4.485 in manuscript
historical Table 11 of v1.3.8 and Table S12), while their median is 4.9754950464 (4.975 here and in
Table S15). Different summaries explain the figures; no data or settings changed.

\paragraph{Complete measured cost.} Medians in seconds, three calls per cell.
Generate includes C++ launch, input reading, construction and Base serialization.
Select/export is the factor and scaled-file stage; import/check includes native
environment setup and import equality checks. Total is the full fresh Python
process, including startup, model reading, metadata, integrity, extraction and
persistence. Additional stages are in the CSV; displayed stages are not an
exhaustive partition and medians need not add.
\begin{center}\small
\input{workflow-cost.tex}
\end{center}
The machine was shared with another thesis computation. These measurements
describe this prototype and do not establish a general speed comparison at equal
quality. Generator compilation and previous witness acquisition are offline costs.

\paragraph{Instrumentation amendment.} The first twelve-call pass is retained in
\texttt{first-pass/}. It repeatedly copied binding arrays inside its import checker.
After caching those arrays once, all twelve treatments were repeated with unchanged
models, factors, seeds, parameters and checks. All saved points and native outcomes
match exactly across passes. There are 24 new MILP calls in total; the first pass
is not pooled as an independent sample or used for the principal timing table.

\paragraph{Independent replay.} A separate rational checker revalidates both exact
feasible witnesses (20,160 rows, 12,240 variables, 2,880 integer domains) and checks
103,680 physical row/point combinations before/after rounding. It uses saved data
and an open-source model reader, without optimization or a commercial license.
Four endpoint tests cover rounding, exact cancellation and bound/gap refutations.
Witness revalidation cost is separate from the workflow. Neither witness is a
global MILP optimum certificate.

\paragraph{OMS decision.} Add a short matched-control statement in Section 7.9;
retain detail and timing in the supplement. Preserve the two contributions,
abstract and introduction; the v1.3.8 editorial closure also shortens the cover letter.
This closes a specific comparison rather
than opening a new mechanism campaign.
\end{document}
'''
    (HERE/'workflow-note.tex').write_text(tex)
    print('Two tables and the focused report regenerated from verified records')


if __name__=='__main__':main()
