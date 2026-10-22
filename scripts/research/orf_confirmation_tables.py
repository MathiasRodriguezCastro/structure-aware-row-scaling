#!/usr/bin/env python3
"""Render the complete closed confirmation without selecting favorable strata."""
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT/'exploration/orf-confirmatory-extension-20261019'
OUT = ROOT/'paper/orf/editorial'


def load(name):
    return json.loads((HERE/name).read_text())


def sha(name):
    return hashlib.sha256((HERE/name).read_bytes()).hexdigest()


def ci(record, metric):
    value = record['metrics'][metric]
    ratio = value['geometric_mean_paired_ratio']
    if 'interval_95' in value:
        a, b = value['interval_95']
        return f'{ratio:.3f} [{a:.3f}, {b:.3f}]'
    return f'{ratio:.3f}'


def main():
    analysis = load('CONFIRMATION_ANALYSIS.json')
    replay = load('CONFIRMATION_ANALYSIS_REPLAY.json')
    closure = load('CONFIRMATION_CLOSURE.json')
    diagnostics = load('CONFIRMATION_FINAL_DIAGNOSTICS.json')
    assert replay['status'] == 'passed' and replay['comparisons_reproduced'] == 48
    assert replay['bootstrap_intervals_reproduced'] == 80
    assert closure['status'] == 'closed_verified' and closure['local_complete_raw_seal_verified']
    assert sha('CONFIRMATION_ANALYSIS.json') == closure['hashes']['CONFIRMATION_ANALYSIS.json']
    assert diagnostics['analysis_sha256'] == sha('CONFIRMATION_ANALYSIS.json')
    indexed = {(r['solver'], r['stratum'], r['denominator']):r for r in analysis['comparisons']}
    assert len(indexed) == 48
    main = r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{4pt}
\caption{Larger fixed-policy confirmation: Budget-L2/L2 over 477 eligible pairs
per solver. Ratios are paired geometric means with marginal 95\% whole-parent
bootstrap intervals. Success requires the common verified accuracy and cost
target. PAR2 penalizes unattained targets; it is not online stopping time.}
\label{tab:orf-large-confirmation}
\begin{tabular}{lccc}\toprule
Solver & \shortstack{Targets\\Budget/L2} & PAR2 ratio [95\% interval] & \shortstack{Complete-process time\\ratio [95\% interval]}\\\midrule
'''
    for solver, label in [('gurobi', 'Gurobi'), ('cplex', 'CPLEX')]:
        r = indexed[solver, 'all', 'L2']
        main += f"{label} & {r['numerator_successes']}/{r['denominator_successes']} & {ci(r,'par2_seconds')} & {ci(r,'complete_process_seconds')}\\\\\n"
    main += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-summary-table.tex').write_text(main)
    controls = r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{3pt}
\caption{All global controls in the larger confirmation. Budget-L2 is the
numerator; work is solver-specific and right-censored. Only the L2 comparison
has the registered bootstrap intervals; secondary controls are descriptive.}
\label{tab:orf-large-controls}
\begin{tabular}{llcrrr}\toprule
Solver & Control & Targets B/C & PAR2 B/C & Time B/C & Work B/C\\\midrule
'''
    for solver, label in [('gurobi', 'Gurobi'), ('cplex', 'CPLEX')]:
        for control in ['L2', 'Base', 'L2-NF3' if solver == 'gurobi' else 'L2-NumEmphasis']:
            r = indexed[solver, 'all', control]
            values = [r['metrics'][m]['geometric_mean_paired_ratio'] for m in
                      ['par2_seconds', 'complete_process_seconds', 'solver_work']]
            controls += f"{label} & {control} & {r['numerator_successes']}/{r['denominator_successes']} & "+' & '.join(f'{v:.3f}' for v in values)+r'\\'+'\n'
    controls += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-controls-table.tex').write_text(controls)
    precision = r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{3pt}
\caption{Final-point checks in the larger confirmation, out of 477 eligible
points per policy/solver. Physical budgets and rounded-point domains are
distinct. The last column gives available bound contrasts/detected
contradictions. A zero available denominator provides no evidence about bounds.}
\label{tab:orf-large-precision}
\begin{tabular}{llrrrr}\toprule
Solver & Policy & Physical & Domains & Targets & Bound contrasts/flags\\\midrule
'''
    for solver, label in [('gurobi', 'Gurobi'), ('cplex', 'CPLEX')]:
        for policy in ['Base', 'L2', 'Budget-L2', 'L2-NF3' if solver == 'gurobi' else 'L2-NumEmphasis']:
            d = next(r for r in diagnostics['rows'] if r['solver'] == solver and r['policy'] == policy)
            p = next(r for r in analysis['policy_counts'] if r['solver'] == solver and r['policy'] == policy)
            c = d['counts']
            precision += f"{label} & {policy} & {c['physical_pass']} & {c['domain_pass']} & {p['verified_target_successes']} & {p['bound_comparisons']}/{p['detected_bound_contradictions']}\\\\\n"
    precision += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-precision-table.tex').write_text(precision)
    strata = r'''\begin{table}[htbp]
\centering\scriptsize\setlength{\tabcolsep}{3pt}
\caption{Every formulation/horizon stratum of the primary Budget-L2/L2
comparison. Each row retains the common infeasibility mask. Ratios and marginal
95\% intervals use complete-parent resampling; these are not simultaneous
intervals or evidence of equivalence.}
\label{tab:orf-large-strata}
\begin{tabular}{llrccc}\toprule
Solver & Stratum & Pairs & Targets B/L2 & PAR2 ratio [95\% interval] & Time ratio [95\% interval]\\\midrule
'''
    labels = [('simple','Simple'), ('sgtm','SG-Ter-Mer'), ('completo','Full'),
              ('h24','24 h'), ('h72','72 h'), ('h168','168 h'), ('h360','360 h')]
    for solver, label in [('gurobi', 'Gurobi'), ('cplex', 'CPLEX')]:
        for group, group_label in labels:
            r = indexed[solver, group, 'L2']
            strata += f"{label} & {group_label} & {r['paired_assignments']} & {r['numerator_successes']}/{r['denominator_successes']} & {ci(r,'par2_seconds')} & {ci(r,'complete_process_seconds')}\\\\\n"
    strata += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-strata-table.tex').write_text(strata)
    horizons = r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{3pt}
\caption{Primary Budget-L2/L2 comparison by horizon in the larger confirmation.
Targets give successful assignments B/L2; $n$ is the number of eligible pairs.
Ratios are paired geometric means with marginal 95\% whole-parent intervals.
PAR2 and complete-process time measure distinct costs.}
\label{tab:orf-large-horizons}
\begin{tabular}{llrccc}\toprule
Solver & Hours & $n$ & Targets B/L2 & PAR2 ratio [95\% interval] & Time ratio [95\% interval]\\\midrule
'''
    for solver, label in [('gurobi', 'Gurobi'), ('cplex', 'CPLEX')]:
        for horizon in [24,72,168,360]:
            r = indexed[solver, f'h{horizon}', 'L2']
            horizons += f"{label} & {horizon} & {r['paired_assignments']} & {r['numerator_successes']}/{r['denominator_successes']} & {ci(r,'par2_seconds')} & {ci(r,'complete_process_seconds')}\\\\\n"
    horizons += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-horizons-table.tex').write_text(horizons)
    folder = ROOT/'exploration/orf-acceptance-sensitivity-20261022'
    sensitivity = json.loads((folder/'SENSITIVITY.json').read_text())
    validation = json.loads((folder/'VALIDATION.json').read_text())
    assert validation['status'] == 'passed'
    assert validation['sensitivity_sha256'] == hashlib.sha256((folder/'SENSITIVITY.json').read_bytes()).hexdigest()
    table = r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{6pt}
\caption{Post hoc CPLEX acceptance sensitivity. Counts out of 477 assignments
per policy use any saved cost-eligible candidate. Only the maximum written-bound
residue threshold $\tau_b$ changes, in the respective variable's algebraic units;
physical, integrality, remaining-row and cost checks are fixed. The registered
endpoint is $\tau_b=0$; the other columns are diagnostic.}
\label{tab:orf-large-sensitivity}
\begin{tabular}{lrrrrr}\toprule
Policy & $0$ & $10^{-12}$ & $10^{-9}$ & $10^{-6}$ & $10^{-5}$\\\midrule
'''
    for policy in ['Base','L2','Budget-L2','L2-NumEmphasis']:
        r = next(r for r in sensitivity['summary'] if r['solver']=='cplex' and r['policy']==policy)
        table += policy+' & '+' & '.join(map(str,r['target_successes']))+r'\\'+'\n'
    table += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-sensitivity-table.tex').write_text(table)
    details = r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{4pt}
\caption{Positive final-point written-bound residues in the larger confirmation.
Quantiles are nearest ranks among positive residues only; values use the
respective variable units. The exact rational values are in Online Resource~2.}
\label{tab:orf-large-bound-magnitudes}
\begin{tabular}{llrrrrr}\toprule
Solver & Policy & Positive/$477$ & Min & Median & 95th percentile & Max\\\midrule
'''
    for r in sensitivity['summary']:
        values = [float(Fraction(r[k])) for k in ['positive_final_min','positive_final_median','positive_final_p95','positive_final_max']]
        def scientific(v):
            mantissa, exponent = f'{v:.2e}'.split('e')
            return f'${mantissa}\\!\\times\\!10^{{{int(exponent)}}}$'
        solver_label = 'CPLEX' if r['solver']=='cplex' else 'Gurobi'
        details += solver_label+' & '+r['policy']+f" & {r['positive_final_bounds']} & "+' & '.join(scientific(v) for v in values)+r'\\'+'\n'
    details += '\\bottomrule\\end{tabular}\\end{table}\n'
    details += r'''\begin{table}[htbp]
\centering\small\setlength{\tabcolsep}{4pt}
\caption{Complete post hoc bound-threshold sensitivity for both solvers. Each
cell gives attained targets/final-point domain passes, out of 477 assignments.
An earlier candidate may attain the target even when the final domains fail.
The first column of counts reproduces the registered endpoint.}
\label{tab:orf-large-sensitivity-full}
\begin{tabular}{llrrrrr}\toprule
Solver & Policy & $0$ & $10^{-12}$ & $10^{-9}$ & $10^{-6}$ & $10^{-5}$\\\midrule
'''
    for r in sensitivity['summary']:
        solver_label = 'CPLEX' if r['solver']=='cplex' else 'Gurobi'
        details += solver_label+' & '+r['policy']+' & '+' & '.join(f'{a}/{b}' for a,b in zip(r['target_successes'],r['final_domains']))+r'\\'+'\n'
    details += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/'confirmation-sensitivity-details-table.tex').write_text(details)
    print('Seven confirmation table fragments regenerated; registered results and post hoc sensitivity kept distinct.')


if __name__ == '__main__':
    main()
