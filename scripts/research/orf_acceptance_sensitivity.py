#!/usr/bin/env python3
"""Post hoc bound-threshold sensitivity; retain the registered endpoint unchanged.

Uses the candidate audits already independently replayed in the frozen study.
No new clocks, optimizer calls, repairs, or altered physical/integer/cost tests.
"""
import hashlib
import json
from collections import defaultdict
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'exploration/orf-confirmatory-extension-20261019'
OUT = ROOT/'exploration/orf-acceptance-sensitivity-20261022'
THRESHOLDS = ['0', '1e-12', '1e-9', '1e-6', '1e-5']


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')


def main():
    protocol = load(OUT/'PLAN.json')
    assert protocol['bound_thresholds_exact_decimal'] == THRESHOLDS
    rows, inputs = [], {}
    for report_path in sorted((SOURCE/'confirmation-replay').glob('*.json')):
        report = load(report_path)
        assert report['status'] == 'passed'
        inputs[str(report_path.relative_to(ROOT))] = sha(report_path)
        for replay in report['rows']:
            if replay['diagnostic']:
                continue
            job = replay['job']
            path = SOURCE/'confirmation-runs'/job['id']/'result.json'
            assert sha(path) == replay['result_sha256']
            inputs[str(path.relative_to(ROOT))] = replay['result_sha256']
            result = load(path)
            assert result['status'] == 'completed' and replay['returncode'] == 0
            events = result['events']
            final = events[-1]
            assert final['kind'] == 'final'
            indices = []
            for threshold in map(Q, THRESHOLDS):
                accepted = [i for i, event in enumerate(events)
                    if event['quality_pass'] and event['audit']['physical_pass']
                    and event['audit']['other_rows_pass']
                    and Q(event['audit']['max_integrality']) <= Q.from_float(1e-9)
                    and Q(event['audit']['max_bound_violation']) <= threshold]
                indices.append(accepted[0] if accepted else None)
            assert (indices[0] is not None) == replay['success']
            assert indices[0] == (None if result['first_qualified'] is None else result['first_qualified']['index'])
            a = final['audit']
            rows.append(dict(id=job['id'], solver=job['solver'], policy=job['policy'],
                parent=job['parent_id'], horizon=job['horizon'], first_indices=indices,
                final_bound_exact=a['max_bound_violation'], final_integrality_exact=a['max_integrality'],
                final_physical=a['physical_pass'], final_other=a['other_rows_pass'],
                final_quality=final['quality_pass']))
    assert len(rows) == 3816
    groups = defaultdict(list)
    for row in rows:
        groups[row['solver'], row['policy']].append(row)
    summary = []
    for (solver, policy), group in sorted(groups.items()):
        positive = sorted(Q(r['final_bound_exact']) for r in group if Q(r['final_bound_exact']) > 0)
        # Nearest-rank quantiles of positive final-point residuals, not all points.
        quantile = lambda p: str(positive[max(0, (len(positive)*p+99)//100-1)]) if positive else None
        summary.append(dict(solver=solver, policy=policy, assignments=len(group),
            target_successes=[sum(r['first_indices'][i] is not None for r in group) for i in range(len(THRESHOLDS))],
            final_domains=[sum(Q(r['final_bound_exact']) <= t and
                Q(r['final_integrality_exact']) <= Q.from_float(1e-9) for r in group) for t in map(Q, THRESHOLDS)],
            positive_final_bounds=len(positive), positive_final_min=str(positive[0]) if positive else None,
            positive_final_median=quantile(50), positive_final_p95=quantile(95),
            positive_final_max=str(positive[-1]) if positive else None,
            final_physical_pass=sum(r['final_physical'] for r in group),
            final_other_pass=sum(r['final_other'] for r in group)))
    save(OUT/'SENSITIVITY.json', dict(status='computed', post_hoc=True, optimizer_calls=0,
        primary_endpoint_modified=False, alternate_thresholds_are_new_physical_standards=False,
        thresholds=THRESHOLDS, plan_sha256=sha(OUT/'PLAN.json'),
        frozen_analysis_sha256=sha(SOURCE/'CONFIRMATION_ANALYSIS.json'),
        inputs=inputs, summary=summary, runs=rows,
        timing='No alternative PAR2 or availability times: per-candidate audit timestamps were not saved.'))
    print('Sensitivity: 3816 assignments, all saved quality-eligible candidates; zero endpoint reproduced.')


if __name__ == '__main__':
    if __import__('sys').flags.optimize:
        raise RuntimeError('Integrity assertions require execution without -O.')
    main()
