#!/usr/bin/env python3
"""Describe all prespecified outcomes, including adverse accuracy/quality findings."""
import csv
import json
import math
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def main():
    d=json.loads((HERE/'VALIDATION.json').read_text());assert d['status']=='passed'
    aggregates={r['control']:r for r in d['paired_comparisons'] if r['horizon'] is None}
    policies={r['policy']:r for r in d['policies']}
    f=list(csv.DictReader((HERE/'verified-factors.csv').open()))
    points=list(csv.DictReader((HERE/'verified-runs.csv').open()))
    pairs=list(csv.DictReader((HERE/'verified-pairs.csv').open()))
    model_rows=[]
    for factors in f:
        name=factors['instance'];budget=[r for r in points if r['instance']==name and r['policy']=='Budget-L2']
        for control in ['Base','Base-tight','L2','L2-NF3']:
            control_runs=[r for r in points if r['instance']==name and r['policy']==control]
            pp=[r for r in pairs if r['instance']==name and r['control']==control]
            gm=lambda key:math.exp(statistics.mean(math.log(float(r[key])) for r in pp))
            def preparation(rows):
                return statistics.median(sum(json.loads((HERE/'runs'/f"{name}-s{r['seed']}-{r['policy']}"/'result.json').read_text())['stages_seconds'].get(k,0.)
                    for k in ['generation','parse','metadata','selection','export']) for r in rows)
            budget_prep=preparation(budget);control_prep=preparation(control_runs)
            model_rows.append(dict(instance=name,horizon=factors['horizon'],control=control,
                modified_factors=factors['changed_rows'],max_factor_ratio=factors['max_ratio'],
                paired_work_ratio=gm('work_ratio'),paired_time_ratio=gm('time_ratio'),
                budget_max_residual_over_budget=max(float(r['max_budget_ratio']) for r in budget),
                control_max_residual_over_budget=max(float(r['max_budget_ratio']) for r in control_runs),
                budget_bound_flags=sum(r['bound_contradiction']=='True' for r in budget),
                control_bound_flags=sum(r['bound_contradiction']=='True' for r in control_runs),
                budget_preparation_seconds=budget_prep,control_preparation_seconds=control_prep,
                preparation_difference_seconds=budget_prep-control_prep))
    with (HERE/'verified-model-comparisons.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(model_rows[0]));writer.writeheader();writer.writerows(model_rows)
    intervals=list(csv.DictReader((HERE/'verified-intervals.csv').open()))
    within=sum(r['relative_width_percent']!='' and float(r['relative_width_percent'])<=1 for r in intervals)
    lines=['# Validación prospectiva de Budget-L2 para ORF','',
        'Diseño fijado antes de resolver; inicio 18 y cierre 19 de octubre de 2026.',
        '24 escenarios nuevos, ocho por horizonte de 24, 72 y 168 horas; tres semillas',
        'por escenario y cinco políticas: 360 MIP, todos conservados. No se modificaron',
        'el generador ni la política Budget-L2. Los escenarios perturban ventanas de',
        'seis entradas conocidas: son nuevos parámetros y tamaños, no datos de una',
        'aplicación independiente ni un test fuera de la familia del despacho.','',
        '## Precisión y contradicciones detectadas','',
        '| Política | Presupuestos | B/G | Hipótesis exportada |',
        '|---|---:|---:|---:|']
    for p,r in policies.items():
        lines.append(f"| {p} | {r['budgets_passed']}/72 | {r['bound_flags']}/{r['completion_flags']} | {r['exported_hypothesis_passed']}/72 |")
    lines += ['',
        'Todos los puntos cumplen los presupuestos, antes y después de redondear enteros.',
        'B/G son contradicciones de cota/cierre frente a testigos racionales de la',
        'representación efectivamente resuelta; G usa el criterio histórico del 1%.',
        'No son certificados de todas las cotas restantes. Base tiene dos puntos que',
        'exceden ligeramente la hipótesis de residuo exportado 1e-6, aunque cumplen',
        'los presupuestos originales; la tolerancia nominal no es esa hipótesis.','',
        'En new-h072-08, semilla 101, Budget-L2 devuelve una cota −531914,2655652602.',
        'El testigo exactamente factible de su exportación cuesta −534369,9691107974:',
        'la cota queda refutada por 2455,7035455372 unidades. Su cumplimiento primal',
        'no permite certificar esa cota. No se vuelve a resolver para eliminar el caso.','',
        '## Comparación emparejada','',
        '| Control | Trabajo B/C | Tiempo completo B/C | Pares sin contradicciones B/C | Trabajo filtrado | Tiempo filtrado | Mayor deterioro candidato |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for p,r in aggregates.items():
        lines.append(f"| {p} | {r['work_ratio']:.3f} | {r['time_ratio']:.3f} | {r['screened_pairs']}/72 | {r['screened_work_ratio']:.3f} | {r['screened_time_ratio']:.3f} | {r['max_candidate_deterioration_percent']:.3f}% |")
    lines += ['',
        'Son medias geométricas emparejadas; los 72 pares incluyen tres semillas de',
        '24 escenarios, no 72 modelos independientes. El filtrado es un resumen',
        'descriptivo adicional: retiene pares completados, con presupuestos satisfechos',
        'y sin contradicción detectada en ninguna rama. No demuestra optimalidad ni',
        'elimina los casos adversos del informe completo. Los tiempos incluyen',
        'generación, selección, exportación, importación, verificación y persistencia,',
        'en procesos nuevos intercalados y una máquina compartida.','',
        '**Resultado:** el menor trabajo frente a Base reaparece en escenarios nuevos.',
        'El aporte incremental frente a L2 es más limitado: bajan las contradicciones',
        'detectadas de siete a una, pero el trabajo solo baja 6,9% y el tiempo completo',
        'casi no cambia. Al filtrar contradicciones, la razón de trabajo es 0,971 y',
        'la temporal 1,023. NF3 no presenta contradicciones y tarda algo menos que',
        'Budget-L2 en el ciclo completo. El peor costo candidato de Budget-L2 empeora',
        '1,020% frente a Base/Base-tight; no se puede repetir para esta muestra la',
        'afirmación de deterioro inferior a 0,1% del experimento dirigido anterior.','',
        '## Intervención y referencias racionales','',
        f"El contrato cambia {sum(int(r['changed_rows']) for r in f):,} factores en las 24 instancias, siempre en activación.",
        'Es el 14,286% de las filas por modelo. La mayor razón Budget/L2 por modelo',
        'está entre 8,242 y 10,694. No se detectan incompatibilidades. Los factores',
        'identifican la intervención, sin demostrar el mecanismo interno del solver.','',
        f"Se verifican {d['global_LP_lower_bounds']}/24 cotas LP globales y 72/72 testigos enteros de las tres",
        f"representaciones por modelo. {within} referencias Base quedan certificadas al 1%;",
        'ninguna igualdad U=L certifica un óptimo MILP exacto en esta nueva muestra.',
        'Los otros siete LP globales terminan con estado desconocido de SoPlex y',
        'sin un certificado utilizable; no agotaron necesariamente los 30 segundos.',
        'Las 24 cotas superiores Base están disponibles. Son referencias reparadas,',
        'no certificados de todos los candidatos flotantes de las comparaciones.',
        f"Los 96 intentos racionales cuestan {d['certificate_acquisition_seconds']:.2f} s adicionales,",
        'sin incluirlos dentro de los tiempos MIP comparados.','',
        'Como indicador descriptivo adicional, PAR10 asigna 1200 s a una salida sin',
        'candidato, incompleta, fuera de presupuesto, con contradicción o sin testigo',
        'para el contraste. No se presenta como métrica prefijada en el protocolo.',
        'Las medias en segundos son: '+', '.join(f"{p}: {r['checked_completion_PAR10_seconds']:.3f}" for p,r in policies.items())+'.','',
        '## Incorporación al artículo','',
        'Se añade una subsección breve y los controles por horizonte al suplemento.',
        'El resumen conserva el resultado previo de seis modelos y añade el límite',
        'prospectivo. No se presenta superioridad general frente a L2 o NF3.',
        'La cota elemental de errores de exportación se documenta aparte y se prueba',
        'en 20000 verificaciones racionales, sin cambiar la política experimental.','',
        '## Reproducción sin licencia comercial','',
        'Extraer el archivo científico heredado y superponer el ZIP prospectivo.',
        'Desde esa raíz:', '', '```sh',
        'python3 exploration/orf-confirmatory-20261018/check.py',
        'python3 exploration/orf-confirmatory-20261018/check_export_bound.py',
        '```','',
        '`verified-runs.csv` conserva cada salida; `verified-pairs.csv`, cada comparación;',
        '`verified-factors.csv`, la intervención; `verified-certificates.csv` y',
        '`verified-intervals.csv`, las garantías y los desconocidos. No se requiere',
        'Gurobi ni SoPlex para comprobar los datos suministrados.']
    maintext=r'''\subsection{Prospective scenario validation}
\label{subsec:orf-prospective}
After freezing the 100\,m\textsuperscript{3} policy, we generated 24 new scenarios
at 24, 72 and 168 hourly periods, using fixed random windows and 10\% perturbations
of inflow and demand from the six known clean inputs. These are new parameter
scenarios within one family, not independent operational data. Five policies and
three new seeds give 360 interleaved calls with the previous solver settings.
All 72 Budget-L2 points meet the primal budgets; so do all controls. Paired
geometric-mean work ratios are 0.422 against Base and 0.931 against L2, with
complete-process ratios 0.797 and 0.996. After excluding pairs with detected
contradictions, the L2 comparison is 0.971 for work and 1.023 for time (64 pairs).
Exact witnesses detect seven L2 bound contradictions and one Budget-L2
contradiction; L2-NF3 has none and a Budget-L2/NF3 time ratio of 1.031.
Candidate deterioration reaches 1.020\% against Base. Thus lower work transfers
against unscaled controls, while an additional computational advantage over L2
and equally certified solution quality remain unestablished. Online Resource~1
reports every stratum, intervention and rational-reference outcome.
'''
    si=r'''\section{Prospective scenario validation}
\label{sec:orf-prospective-supplement}
This local protocol was frozen before optimization. It fixes Budget-L2 at
0.01 MW and 100 m\textsuperscript{3}, with exactly the previous kernel,
coefficient window, integer allowance and activation export reserve. No budget
or solver parameter is tuned on these outcomes. Eight scenarios per horizon
(24,72,168 hours) use contiguous windows of the six known clean inputs, in
round-robin order, and a fixed PRNG. Inflow receives independent hourly factors
in $[0.9,1.1]$; the two demand series receive the same hourly factor, preserving
local demand below total demand. The original generator and plant parameters
are unchanged. The 24 new exports retain $4H$ binary variables, $17H$ columns
and $28H$ rows. This tests prospective parameter transfer conditional on known
parent structure, not external validation or an observational holdout.

The 360 assignments use seeds 101,137,173 and five policies in a frozen shuffled
order, sequential fresh processes on a shared host. Common settings are Gurobi
13.0.2, four threads, 120 s, 1\% requested gap, automatic presolve,
FeasibilityTol=$10^{-6}$, IntFeasTol=$10^{-9}$, ScaleFlag=$-1$ and default
IntegralityFocus/NumericFocus. Base-tight changes only FeasibilityTol to
$10^{-9}$; L2-NF3 changes only NumericFocus to 3. No starts are supplied.
Every candidate and status is retained. All policies return points and native
completion in 72/72 assignments; native completion is not a certificate.

\begin{table}[htbp]
\centering\small
\caption{Prospective scenarios. Budgets include raw and integer-rounded points;
B/G are detected bound/1\%-completion contradictions against exact feasible
witnesses of the actual native export. No missing witness contrasts occur.}
\label{tab:orf-prospective-accuracy}
\begin{tabular}{lrrr}\toprule
Policy & Budgets & B/G & Export hypothesis\\\midrule
'''
    for p,r in policies.items():si+=f"{p} & {r['budgets_passed']}/72 & {r['bound_flags']}/{r['completion_flags']} & {r['exported_hypothesis_passed']}/72\\\\\n"
    si+=r'''\bottomrule\end{tabular}\end{table}
All original-unit checks use exact rational expressions in the supplied
binary64 data and points. The nominal exported tolerance is distinguished from
the observed residual: two Base points exceed the $10^{-6}$ physical-row
hypothesis slightly but still satisfy their original budgets. No policy gains
additional primal recoveries here. The contract changes 8,448 factors over the
24 models, always activation rows (14.286\% of each model's rows). The largest
Budget/L2 factor ratio per model ranges from 8.242 to 10.694. There are no
incompatible requirements. These measurements locate the changed representation,
without identifying a proprietary solver operation as its cause.

\begin{table}[htbp]
\centering\small
\caption{Paired geometric means for Budget-L2/control. Each horizon has eight
scenarios and three seeds; all rows include adverse outcomes. Time covers the
complete fresh process, including generation, selection, export, import,
verification and persistence. Certificate acquisition is separate.}
\label{tab:orf-prospective-performance}
\begin{tabular}{lrrrr}\toprule
Horizon & $W/ W_{\rm Base}$ & $W/W_{\rm L2}$ & $T/T_{\rm Base}$ & $T/T_{\rm L2}$\\\midrule
'''
    for h in [24,72,168,None]:
        base=next(r for r in d['paired_comparisons'] if r['horizon']==h and r['control']=='Base')
        l2=next(r for r in d['paired_comparisons'] if r['horizon']==h and r['control']=='L2')
        si+=f"{h or 'All'} & {base['work_ratio']:.3f} & {l2['work_ratio']:.3f} & {base['time_ratio']:.3f} & {l2['time_ratio']:.3f}\\\\\n"
    si+=r'''\bottomrule\end{tabular}\end{table}
Across all 72 pairs, Budget-L2/Base-tight work and time ratios are 0.170 and
0.643; Budget-L2/NF3 ratios are 0.476 and 1.031. There are only 24 scenarios,
not 72 independent models. Removing pairs with a contradiction in either arm
leaves 71 Base comparisons (work/time 0.419/0.796), 71 Base-tight
(0.168/0.641), 64 L2 (0.971/1.023), and 71 NF3 (0.472/1.028).
This descriptive screen does not certify the retained gaps. Candidate cost
deterioration reaches 1.020\% against Base/Base-tight and 0.778\% against L2.
Thus the six-known-model claim of deterioration below 0.1\% does not extend to
this prospective sample. Lower work against Base is replicated, but a broad
incremental speed advantage over L2 is not.

For new-h072-08, seed 101, Budget-L2 reports a lower bound of
$-531914.2655652602$. An exactly feasible point of that actual export has cost
$-534369.9691107974$, contradicting the bound by 2455.7035455372 units.
It does not trigger the separate 1\%-completion flag. This is an adverse outcome
under the frozen policy, not a reason to retune it.

The reference campaign attempts one unfixed global rational LP per original
model and one integer-pattern repair per representation (Base,L2,Budget-L2),
each at 30 s. For each representation the lowest-cost saved candidate selects
the pattern, with a lexical tie break; no alternative patterns are tried.
All 96 LP calls are recorded. Independent reconstruction checks 72 feasible
integer witnesses, one per native representation/model, and 17 global LP dual
lower bounds. Twelve Base references have certified relative interval width
at most 1\%; none has $L=U$. Seven SoPlex global-LP attempts terminate unknown
without usable certificates, rather than necessarily exhausting the time limit.
The complete reference campaign costs 50.90 s additional to the MIP comparisons.
These repaired references do not certify every returned floating-point point.

The archive also reports a descriptive checked-completion PAR10: use complete
time for a completed, budget-passing point with a known witness and no detected
contradiction; otherwise assign 1200 s. This additional score was not an original
prespecified endpoint. The means for Base, Base-tight, L2, NF3 and Budget-L2
are 1.860,2.431,117.623,1.095 and 17.696 s. The raw observations and exclusions
remain available. No one score replaces the separate accuracy, quality and
effort comparisons.
'''
    logging_path=HERE/'logging-confirmation/VALIDATION.json'
    if logging_path.exists():
        logging=json.loads(logging_path.read_text());assert logging['complete_native_logs']==360
        rep=logging['replication']
        aa={r['control']:r for r in logging['paired_comparisons'] if r['horizon'] is None}
        extra=['','## Confirmación con trazas nativas completas','',
            'La auditoría detectó que OutputFlag=0 había silenciado las trazas nativas',
            'de la primera campaña. Se conservaron todos sus puntos, resultados API y',
            'logs de cabecera, y se registró LOGGING_AMENDMENT.json antes de repetir',
            'las 360 asignaciones completas con OutputFlag=1. No se cambiaron modelos,',
            'política ni parámetros de optimización. Son 720 MIP totales, no 48 modelos.',
            f"La confirmación conserva exactamente {rep['identical_saved_points']}/360 puntos,",
            f"{rep['identical_work']}/360 valores de trabajo y {rep['identical_endpoints']}/360 conjuntos de endpoints.",
            'Se verifican racionalmente todas las soluciones nuevas y se reutilizan',
            'los testigos de las mismas exportaciones, sin nuevas llamadas LP.',
            'Las contradicciones originales no se eliminan. Tiempos completos de la',
            'confirmación, por separado:','',
            '| Control | Trabajo B/C | Tiempo completo B/C |','|---|---:|---:|']
        for p,r in aa.items():extra.append(f"| {p} | {r['work_ratio']:.3f} | {r['time_ratio']:.3f} |")
        extra+=['','`logging-confirmation/verified-replication.csv` muestra cada cotejo y',
            '`logging-confirmation/verified-runs.csv` retiene las nuevas verificaciones.',
            '`verified-model-comparisons.csv` cruza por modelo la intervención, esfuerzo,',
            'residuos, contradicciones y preparación adicional de la campaña principal.','']
        at=lines.index('## Incorporación al artículo');lines[at:at]=extra
        cmd='python3 exploration/orf-confirmatory-20261018/check.py --logging-confirmation'
        at=lines.index('python3 exploration/orf-confirmatory-20261018/check.py')+1;lines.insert(at,cmd)
        maintext=maintext.replace('reports every stratum, intervention and rational-reference outcome.',
            'reports every stratum, intervention, rational reference and the registered\n360-call logging confirmation.')
        si+=r'''
\paragraph{Native logging confirmation}
The packaging audit detected that the first campaign inherited OutputFlag=0,
which suppressed native traces; its API outcomes, saved points and header logs
remain intact. A registered amendment repeats all 360 assignments with
OutputFlag=1, changing no optimization parameter, model or policy. Both campaigns
are supplied: 720 MIP calls on the same 24 scenarios and three seeds, not an
enlarged independent sample. All confirmation traces contain complete optimizer
output and are checked against the saved endpoints.
'''
        si+=f"The confirmation reproduces {rep['identical_saved_points']}/360 saved points,\n{rep['identical_work']}/360 work values and {rep['identical_endpoints']}/360 endpoint sets exactly.\n"
        si+=r'''Every repeated point is checked rationally; the unchanged exports permit reuse
of the same witnesses without new LP acquisition. Work comparisons and adverse
bound outcomes remain available for both campaigns. Complete-process time is
reported separately for this technical replication on the shared host.
'''
        si+='Budget-L2 time ratios are '+', '.join(f"{r['time_ratio']:.3f} against {p}" for p,r in aa.items())+'.\n'
    (HERE/'RESULTADOS.md').write_text('\n'.join(lines)+'\n')
    editorial=ROOT/'paper/orf/editorial';editorial.mkdir(parents=True,exist_ok=True)
    (editorial/'prospective-main.tex').write_text(maintext)
    (editorial/'prospective-supplement.tex').write_text(si)

if __name__=='__main__':main()
