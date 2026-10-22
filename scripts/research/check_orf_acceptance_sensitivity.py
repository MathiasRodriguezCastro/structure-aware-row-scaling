#!/usr/bin/env python3
"""Independently check post hoc thresholds from saved vectors and written bounds."""
import hashlib
import importlib.util
import json
import math
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'exploration/orf-confirmatory-extension-20261019'
OUT = ROOT/'exploration/orf-acceptance-sensitivity-20261022'


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = load(OUT/'SENSITIVITY.json')
    assert data['primary_endpoint_modified'] is False and data['optimizer_calls'] == 0
    assert data['plan_sha256'] == sha(OUT/'PLAN.json')
    for name, digest in data['inputs'].items():
        assert sha(ROOT/name) == digest, name
    spec = importlib.util.spec_from_file_location('written_bounds_reader', SOURCE/'verify_reference_witnesses_stdlib.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    plan = load(SOURCE/'CONFIRMATION_PLAN.json')
    metadata = load(SOURCE/'MODEL_PREPARATION.json')['models']
    jobs = {j['id']:j for b in plan['blocks'] for j in b['jobs']}
    replays = {r['job']['id']:r for p in (SOURCE/'confirmation-replay').glob('*.json') for r in load(p)['rows']}
    cache = {}
    groups = defaultdict(list)
    checked = 0
    for index, row in enumerate(data['runs']):
        job = jobs[row['id']]
        replay = replays[job['id']]
        assert not job['diagnostic'] and replay['status'] == 'completed' and replay['returncode'] == 0
        instance = job['instance']
        if instance not in cache:
            path = SOURCE/'models'/instance/'Base.lp'
            assert sha(path) == metadata[instance]['base_sha256']
            model = reader.read_model(path)
            cache[instance] = model[1], model[3]
        bounds, integers = cache[instance]
        folder = SOURCE/'confirmation-runs'/job['id']
        result = load(folder/'result.json')
        assert sha(folder/'candidates.npz') == replay['candidate_archive_sha256']
        first = [None]*len(data['thresholds'])
        with np.load(folder/'candidates.npz', allow_pickle=False) as vectors:
            names, points = vectors['names'].tolist(), vectors['x']
            assert len(names) == len(bounds) and set(names) == set(bounds)
            lower = np.array([float(bounds[n][0]) if bounds[n][0] is not None else -np.inf for n in names])
            upper = np.array([float(bounds[n][1]) if bounds[n][1] is not None else np.inf for n in names])
            integral = np.array([n in integers for n in names])
            assert points.shape == (len(result['events']), len(names)) and np.isfinite(points).all()
            for i, (event, vector) in enumerate(zip(result['events'], points)):
                if not event['quality_pass'] and event['kind'] != 'final':
                    continue
                rounded = vector.copy()
                rounded[integral] = np.rint(vector[integral])
                # All written bounds in this dialect are binary64 values. The
                # comparisons screen exactly; rational subtraction avoids any
                # rounded residual or threshold comparison.
                violation = Fraction(0)
                for col in np.flatnonzero((rounded < lower) | (rounded > upper)):
                    n = names[col]
                    x = Fraction.from_float(float(rounded[col]))
                    lo, hi = bounds[n]
                    violation = max(violation, lo-x if lo is not None else 0, x-hi if hi is not None else 0)
                int_positions = np.flatnonzero(integral & (vector != rounded))
                distance = max((abs(Fraction.from_float(float(vector[c]))-int(rounded[c])) for c in int_positions), default=Fraction(0))
                audit = event['audit']
                assert violation == Fraction(audit['max_bound_violation']), (job['id'], i)
                assert distance == Fraction(audit['max_integrality'])
                checked += 1
                admissible = (event['quality_pass'] and audit['physical_pass'] and audit['other_rows_pass']
                              and distance <= Fraction.from_float(1e-9))
                for k, threshold in enumerate(data['thresholds']):
                    if admissible and violation <= Fraction(threshold) and first[k] is None:
                        first[k] = i
                if event['kind'] == 'final':
                    assert str(violation) == row['final_bound_exact']
                    assert str(distance) == row['final_integrality_exact']
        assert first == row['first_indices'], job['id']
        assert (first[0] is not None) == replay['success']
        groups[job['solver'], job['policy']].append(row)
        if (index+1) % 500 == 0:
            print('Vector/domain sensitivity replay:', index+1, flush=True)
    assert len(data['runs']) == len({r['id'] for r in data['runs']}) == 3816
    for summary in data['summary']:
        group = groups[summary['solver'], summary['policy']]
        assert len(group) == summary['assignments'] == 477
        for k, threshold in enumerate(data['thresholds']):
            successes = sum(r['first_indices'][k] is not None for r in group)
            domains = sum(Fraction(r['final_bound_exact']) <= Fraction(threshold) and
                          Fraction(r['final_integrality_exact']) <= Fraction.from_float(1e-9) for r in group)
            assert successes == summary['target_successes'][k]
            assert domains == summary['final_domains'][k]
        positives = sorted(Fraction(r['final_bound_exact']) for r in group if Fraction(r['final_bound_exact']) > 0)
        assert len(positives) == summary['positive_final_bounds']
        for key, rank in [('positive_final_min', 1), ('positive_final_median', math.ceil(len(positives)*.5)),
                          ('positive_final_p95', math.ceil(len(positives)*.95)), ('positive_final_max', len(positives))]:
            assert summary[key] == (str(positives[rank-1]) if positives else None)
    proof = dict(status='passed', sensitivity_sha256=sha(OUT/'SENSITIVITY.json'),
        checker_sha256=sha(Path(__file__)), eligible_assignments=3816, policies=8,
        threshold_levels=len(data['thresholds']), independently_checked_candidate_domains=checked,
        registered_successes_reproduced=True, optimizer_calls=0, primary_endpoint_modified=False,
        scope='Domain and threshold arithmetic independently reconstructed from vectors; physical, other-row and quality checks reuse the sealed independently replayed audits.')
    (OUT/'VALIDATION.json').write_text(json.dumps(proof, indent=2, sort_keys=True)+'\n')
    print('Acceptance sensitivity independently verified:', checked, 'candidate domains.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O.')
    main()
