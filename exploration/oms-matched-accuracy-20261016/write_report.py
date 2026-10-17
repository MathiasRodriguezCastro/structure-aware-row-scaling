#!/usr/bin/env python3
"""Generate descriptive reports only after all assigned calls pass saved-point replay."""
import csv
import json
from pathlib import Path
import statistics as st

HERE=Path(__file__).resolve().parent


def read(name):
    result=[]
    for r in csv.DictReader((HERE/name).open()):
        for k,v in r.items():
            if v in ('True','False'):r[k]=v=='True'
            elif v=='':r[k]=None
            else:
                try:r[k]=float(v)
                except ValueError:pass
        result.append(r)
    return result


def number(x):return f'{x:.4g}' if x is not None else '--'
def integer(x):return str(int(x))


def main():
    summary=read('verified-summary.csv');cases=read('verified-cases.csv')
    runs=read('verified-runs.csv');pairs=read('verified-pairs.csv')
    valid=json.loads((HERE/'VALIDATION.json').read_text())
    assert valid['checked_milp_calls']==len(runs)==144 and len(summary)==8
    lookup={(r['presolve'],r['policy']):r for r in summary}
    for p in (-1,0):
        assert lookup[p,'L2-NF3']['budgets_pass']==18
        assert lookup[p,'L2-NF3']['bound_contradictions']==lookup[p,'L2-NF3']['completion_contradictions']==0
        assert lookup[p,'Budget-L2']['budgets_pass']==18
        assert lookup[p,'Budget-L2']['completion_contradictions']==0
    assert lookup[-1,'Budget-L2']['bound_contradictions']==1
    assert lookup[0,'Budget-L2']['bound_contradictions']==3
    assert lookup[-1,'L2']['budgets_pass']==18 and lookup[0,'L2']['budgets_pass']==15
    rows=[r'\begin{tabular}{llrrrrrrr}',r'\toprule',
        r'Presolve & Policy & Budgets & Max. $v_V$ & $B>U$ & Gap flags & Limits & Work & Total\\',
        r'\midrule']
    md='''# Precisión y costo con controles emparejados

16 de octubre de 2026. Extensión cerrada de seis modelos conocidos SG-Ter-Mer,
no una validación externa. Se conservaron las 144 asignaciones del protocolo.
Hubo 145 intentos nativos: 144 resultados terminales y un intento interrumpido
por un reinicio del equipo, preservado y repetido según RESTART_AMENDMENT.md.

**Hallazgo central:** la recuperación primal frente a L2 sigue limitada a
instance046 sin presolve. NumericFocus=3 cumple los presupuestos y no presenta
ninguna de las contradicciones detectadas en sus 36 llamadas. Budget-L2 cumple
los 36 presupuestos, pero mantiene una cota contradicha con presolve automático
y tres sin presolve. Sus cocientes geométricos de Work frente a NumericFocus=3
son 0,361 y 0,227 respectivamente: menor trabajo para el presupuesto primal,
con diferencias pendientes de calidad de las afirmaciones del solver. No se
establece una política de optimización generalmente preferible.

## Resultado completo

Presupuesto exigente: 0,01 MW y 100 m³. «Cumple» verifica las 4.320 filas auditadas
por punto después de redondear las variables enteras. Se guardan también los
residuos sin redondear. No se usa el residuo más cercano a cero como criterio de
superioridad cuando ambos métodos cumplen el presupuesto.

| Presolve | Política | Cumple /18 | Máximo activación (m³) | Cotas contradichas | Finalizaciones contradichas | Límites de tiempo | Media geom. Work | Mediana ciclo completo (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    for s in summary:
        label='Auto' if s['presolve']==-1 else 'Off'
        cells=[label,s['policy'],integer(s['budgets_pass'])+'/18',number(s['maximum_activation_m3']),
            integer(s['bound_contradictions']),integer(s['completion_contradictions']),integer(s['time_limit']),
            number(s['geometric_mean_work']),number(s['median_total_seconds'])]
        rows.append(' & '.join(cells)+r'\\')
        md+='| '+' | '.join(cells)+' |\n'
    rows.extend([r'\bottomrule',r'\end{tabular}'])
    (HERE/'matched-accuracy.tex').write_text('\n'.join(rows)+'\n')
    md+='''
Las cotas se comparan con doce testigos exactamente factibles del archivo nativo
correspondiente, con margen de presentación max(1e-6, 8 ulps). Una finalización
al 1 % se contradice cuando U < C - 0,01|C|. No detectar una contradicción no
certifica ni las cotas ni la optimalidad. Todas las llamadas, incluidas las
finalizaciones contradichas y los límites de tiempo, entran en los resúmenes.

## ¿En cuántos modelos se recupera precisión?

Cada celda indica cumplimiento entre tres semillas, con presolve desactivado.

| Instancia | L2 | Budget-L2 | L2-tight | L2-NF3 |
| --- | ---: | ---: | ---: | ---: |
'''
    improvements=[];case_rows=[r'\begin{tabular}{lrrrr}',r'\toprule',
        r'Instance & L2 & Budget-L2 & L2-tight & L2-NF3\\',r'\midrule']
    for n in sorted({r['instance'] for r in cases}):
        selected=[next(r for r in cases if r['instance']==n and r['presolve']==0 and r['policy']==p)
            for p in ('L2','Budget-L2','L2-tight','L2-NF3')]
        cells=[n]+[integer(r['budgets_pass'])+'/3' for r in selected]
        case_rows.append(' & '.join(cells)+r'\\');md+='| '+' | '.join(cells)+' |\n'
        if selected[1]['budgets_pass']>selected[0]['budgets_pass']:improvements.append(n)
    case_rows.extend([r'\bottomrule',r'\end{tabular}'])
    (HERE/'matched-cases.tex').write_text('\n'.join(case_rows)+'\n')
    md+='\nModelos con mayor cumplimiento Budget-L2 frente a L2 sin presolve: '+(', '.join(improvements) or 'ninguno')+'.\n'
    assert improvements==['instance046']
    md+='''
## Comparación de costo al presupuesto común

Los cocientes se calculan por instancia y semilla; nunca se mezclan configuraciones
de presolve. Un cociente menor que uno favorece a Budget-L2 en trabajo. El resumen
condicionado a que ambos cumplan se identifica como tal, con su denominador. No
representa por sí solo eficiencia hasta una calidad objetiva común ni tiempo hasta
el primer incumbente verificable. Los objetivos y todos los pares se suministran.

| Presolve | Control | Cumplen ambos /18 | Recuperaciones Budget | Pérdidas Budget | Cociente Work, todos | Cociente Work, cumplen ambos | Ambos cumplen y sin flags /18 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    pair_summary=[]
    for p in (-1,0):
        for control in ('L2','L2-tight','L2-NF3'):
            selected=[r for r in pairs if r['presolve']==p and r['control']==control]
            both=[r for r in selected if r['joint_pass']]
            clean=[r for r in selected if r['budget_flagfree'] and r['control_flagfree']]
            r={'presolve':p,'control':control,'pairs':len(selected),'joint_pass':len(both),
                'recoveries':sum(r['budget_pass'] and not r['control_pass'] for r in selected),
                'losses':sum(r['control_pass'] and not r['budget_pass'] for r in selected),
                'all_work_ratio':st.geometric_mean(r['work_ratio'] for r in selected),
                'joint_pass_work_ratio':st.geometric_mean(r['work_ratio'] for r in both) if both else None,
                'joint_pass_no_flags':len(clean),
                'joint_pass_no_flags_work_ratio':st.geometric_mean(r['work_ratio'] for r in clean) if clean else None,
                'joint_pass_time_ratio':st.geometric_mean(r['time_ratio'] for r in both) if both else None}
            pair_summary.append(r)
            cells=['Auto' if p==-1 else 'Off',control,str(len(both))+'/18',str(r['recoveries']),str(r['losses']),
                number(r['all_work_ratio']),number(r['joint_pass_work_ratio']),str(len(clean))+'/18']
            md+='| '+' | '.join(cells)+' |\n'
    (HERE/'paired-summary.json').write_text(json.dumps(pair_summary,indent=2)+'\n')
    md+='''
## Diseño, costo completo y límites

Instancias 001,005,022,027,031,046; semillas 11,23,47; presolve automático y
desactivado; cuatro políticas. Cada llamada reconstruye el generador C++ original
una vez, sin modificar su código. Los archivos L2 y Budget reproducen por SHA-256
los usados en la investigación anterior; los controles utilizan el mismo archivo L2.
El contrato cambia 1.440 factores por modelo, sobre 10.080 filas y 6.120 variables
(1.440 binarias). Las entradas no contienen la inversión de demanda documentada.

Gurobi 13.0.2, cuatro hilos, 120 s, gap 1 %, ScaleFlag=-1 e IntegralityFocus=0.
L2 y Budget comparten FeasibilityTol=1e-6 e IntFeasTol=2^-28. L2-tight usa 1e-9
en ambas tolerancias; L2-NF3 conserva las tolerancias emparejadas y añade NumericFocus=3.
No hay MIP starts. El orden aleatorio se fijó antes de optimizar. No se ajustaron
parámetros después de observar los resultados ni se ejecutaron nuevos LP de referencia.

Total abarca un proceso Python nuevo: imports, lanzamiento C++, construcción y
exportación Base, metadatos, selección, escritura escalada, lectura e igualdad de
la importación nativa, resolución, extracción, comprobación y persistencia. Las
etapas disjuntas están en verified-runs.csv. Son tiempos de un prototipo en una
máquina compartida, no un benchmark de producción; Work es el indicador principal
del esfuerzo nativo. Compilación y adquisición previa de testigos son costos fuera
de línea; witness-revalidation-timing.json registra la revalidación actual separada.
Los tiempos además abarcan un reinicio: se conservaron las 37 llamadas completas
anteriores y se repitió únicamente el intento que perdió su proceso. Ese intento
sin resultado final se identifica como fallo externo de entrega, no como réplica
completa ni como fallo atribuible al solver. No se deduce un resultado de sus logs.

Este experimento evalúa la solución terminal del criterio nativo de parada. No
construye una frontera completa sobre diferentes presupuestos ni mide tiempo hasta
el primer incumbente que cumpla. Los menores tiempos de llamadas con cotas o gaps
contradichos no cuentan como optimizaciones exitosas equivalentes.

## Reproducción y decisión

`python3 exploration/oms-matched-accuracy-20261016/independent_check.py` revalida
los doce testigos completos y los residuos físicos con fracciones exactas de los
datos binary64. No importa Gurobi ni llama a un optimizador. `write_report.py`
regenera esta nota y las tablas. `study.py prepare/run` corresponde a la campaña
nativa, requiere licencia y rechaza sobrescribir el diseño existente.

La mejora se evalúa dentro de una sola familia de seis modelos ya conocidos; las
semillas también habían sido utilizadas. No son una muestra externa. Cumplir los
presupuestos auditados no constituye una certificación integral de factibilidad
u optimalidad. Un resultado favorable con presolve desactivado no demuestra una
ventaja con los ajustes predeterminados. Se cierra esta cohorte sin abrir más
barridos en función del resultado.
'''
    (HERE/'RESULTADOS.md').write_text(md)
    (HERE/'matched-accuracy-note.tex').write_text(r'''\documentclass[11pt]{article}
\usepackage[margin=0.8in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,booktabs,graphicx,microtype}
\usepackage[colorlinks=true]{hyperref}
\title{Matched accuracy and cost controls for pre-export scaling}
\author{Research note accompanying the OMS manuscript}
\date{16 October 2026}
\begin{document}\maketitle
Six known demand-inversion-free dispatch models, three previously used seeds,
automatic/off presolve and four policies give 144 fixed assignments. This is a
within-generator confirmation, not external validation. Targets are 0.01 MW and
100 m$^3$, checked exactly in original units after integer rounding on all 4,320
audited rows per saved point.

\begin{center}\resizebox{\linewidth}{!}{\input{matched-accuracy}}\end{center}
Every policy has 18 calls in each presolve configuration. Maximum activation
violation is in m$^3$; Limits counts native time limits. Work is the geometric mean
over all calls; Total is the median full fresh-process wall time in seconds.
$B>U$ counts bounds contradicted by exact feasible witnesses of the actual export,
allowing max($10^{-6}$,8 bound ulps). Gap flags count reported 1\% completions
satisfying $U<C-0.01|C|$. Absence of a flag does not certify a bound or optimality.

\begin{center}\input{matched-cases}\end{center}
Per-model budget compliance, out of three seeds, with presolve disabled. Tight
tolerances and NumericFocus are matched controls on the identical L2 export.
All 144 terminal outcomes, including time limits, are retained. Objective values
and paired Work ratios appear in the machine-readable reports; comparable primal
budget compliance alone is not comparable optimization success.

\paragraph{Settings and cost scope.}
Gurobi 13.0.2, four threads, 120 seconds, 1\% gap, ScaleFlag=-1,
IntegralityFocus=0, seeds 11/23/47 and no MIP starts. L2/Budget-L2 use
FeasibilityTol=$10^{-6}$ and IntFeasTol=$2^{-28}$; L2-tight uses $10^{-9}$ for
both; L2-NF3 adds NumericFocus=3 to the matched L2 tolerances. A fixed permutation
sets the order. The C++ generator constructs the model once per call; exports reproduce
the prior model hashes. Only 1,440 activation factors per model differ for Budget-L2.
Total includes startup, C++ generation/Base writing, metadata, factor selection,
scaled export, native import/equality checks, optimization, extraction, verification
and persistence. Stages are supplied; shared-machine wall times describe this
prototype. Compilation and historical witness acquisition are offline costs;
current witness revalidation is timed separately.

\paragraph{Scope.}
The experiment measures terminal delivery at the native stopping rule, not time
to first verified incumbent or a full precision--cost frontier. Exact feasible
witnesses refute specific bounds; they do not establish global optima. The
reader-only replay checks twelve witnesses and every saved candidate without
optimizer calls. The protocol, sources, logs, points, exact-unit checks and
complete discussion are supplied alongside this note. OMS v1.3.8 and all previous
closed research archives are preserved. A host reboot interrupted one additional
attempt; its partial output is retained and that assignment alone was repeated,
giving 145 native attempts and 144 terminal comparisons. The 37 completed calls
before the reboot were kept; models, parameters and endpoints were unchanged.
\end{document}
''')
    print('Generated complete matched report, two tables and standalone note')


if __name__=='__main__':main()
