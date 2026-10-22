#!/usr/bin/env python3
"""Render the complete closed confirmation without selecting favorable strata."""
import hashlib
import json
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
    print('Four confirmation tables regenerated from all 48 comparisons and final-point diagnostics.')


if __name__ == '__main__':
    main()
