#!/usr/bin/env python3
"""Independent exact replay of the generator's LP dialect using only the standard library.

This deliberately rejects unsupported syntax and repeated coefficients instead
of silently guessing how a general LP reader would interpret them.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
import sys

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
TERM = re.compile('(' + NUMBER + r')\s+(\S+)')
SENSE = re.compile(r'(<=|>=|=)\s+(' + NUMBER + ')')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar(text):
    value = float(text)
    assert math.isfinite(value), 'A finite coefficient is required.'
    return Q.from_float(value)


def read_model(path):
    rows, bounds, objective, integers = {}, {}, {}, set()
    mode = None
    current = None

    def declare(name):
        bounds.setdefault(name, [Q(0), None])

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower == 'min':
            assert mode is None
            mode = 'objective'
            continue
        if lower == 'obj:':
            assert mode == 'objective'
            continue
        if lower in ['s.t.', 'bounds', 'binary', 'binaries', 'generals', 'end']:
            mode = 'rows' if lower == 's.t.' else 'binary' if lower in ['binary','binaries'] else lower
            continue
        if mode in ['objective', 'rows']:
            if mode == 'rows' and line.endswith(':'):
                current = line[:-1]
                assert current not in rows
                rows[current] = dict(terms={}, sense=None, rhs=None)
                continue
            term = TERM.fullmatch(line)
            if term:
                text, name = term.groups()
                target = objective if mode == 'objective' else rows[current]['terms']
                assert name not in target, 'Repeated coefficient: ' + name
                target[name] = scalar(text)
                declare(name)
                continue
            sense = SENSE.fullmatch(line)
            assert mode == 'rows' and current is not None and sense, 'Unsupported LP line: ' + line
            assert rows[current]['sense'] is None
            rows[current].update(sense=sense[1], rhs=scalar(sense[2]))
        elif mode == 'bounds':
            words = line.split()
            if len(words) == 5 and words[1] == words[3] == '<=':
                low, name, high = words[0], words[2], words[4]
                lo, hi = float(low), float(high)
                assert not math.isnan(lo) and not math.isnan(hi)
                assert lo != math.inf and hi != -math.inf and lo <= hi
                declare(name)
                bounds[name] = [scalar(low) if math.isfinite(lo) else None,
                                scalar(high) if math.isfinite(hi) else None]
            elif len(words) == 2 and words[1].lower() == 'free':
                declare(words[0])
                bounds[words[0]] = [None, None]
            else:
                raise ValueError('Unsupported generator bound: ' + line)
        elif mode in ['binary', 'generals']:
            for name in line.split():
                declare(name)
                assert name not in integers
                integers.add(name)
                if mode == 'binary':
                    lo, hi = bounds[name]
                    bounds[name] = [max(lo, Q(0)) if lo is not None else Q(0),
                                    min(hi, Q(1)) if hi is not None else Q(1)]
        else:
            raise ValueError('Unsupported LP line: ' + line)
    assert mode == 'end' and rows and objective
    assert all(r['sense'] is not None for r in rows.values())
    return rows, bounds, objective, integers


def check_point(model, point):
    rows, bounds, objective, integers = model
    assert set(point) == set(bounds)
    for name, row in rows.items():
        residual = sum((a * point[n] for n, a in row['terms'].items()), Q(0)) - row['rhs']
        assert (residual == 0 if row['sense'] == '=' else residual <= 0 if row['sense'] == '<=' else residual >= 0), name
    for name, (lo, hi) in bounds.items():
        assert (lo is None or point[name] >= lo) and (hi is None or point[name] <= hi), name
    assert all(point[name].denominator == 1 for name in integers)
    return sum((a * point[n] for n, a in objective.items()), Q(0))


def check_infeasibility(model, certificate):
    rows, bounds, _, _ = model
    terms = defaultdict(Q)
    rhs = Q(0)
    for name, text in certificate['row_multipliers'].items():
        weight, row = Q(text), rows[name]
        assert row['sense'] == '=' or (row['sense'] == '<=' and weight >= 0) or (row['sense'] == '>=' and weight <= 0)
        rhs += weight * row['rhs']
        for variable, coefficient in row['terms'].items():
            terms[variable] += weight * coefficient
    for bound in certificate['bound_multipliers']:
        name, weight = bound['variable'], Q(bound['positive_multiplier'])
        assert weight >= 0
        if bound['bound'] == 'lower':
            assert bounds[name][0] == Q(bound['value'])
            terms[name] -= weight
            rhs -= weight * bounds[name][0]
        else:
            assert bound['bound'] == 'upper' and bounds[name][1] == Q(bound['value'])
            terms[name] += weight
            rhs += weight * bounds[name][1]
    assert not any(terms.values()) and rhs < 0 and rhs == Q(certificate['contradiction_rhs_exact'])


def verify(root):
    plan = json.loads((root / 'PENDING_VALIDATION_PLAN.json').read_text())
    preparation = json.loads((root / 'MODEL_PREPARATION.json').read_text())['models']
    audit = json.loads((root / 'STRUCTURAL_FEASIBILITY_AUDIT.json').read_text())
    certificates = {r['instance']: r for r in audit['certificates']}
    records = []
    for name in plan['confirmation_instances']:
        result = json.loads((root / 'confirmation-reference-acquisition' / name / 'result.json').read_text())
        assert result['plan_sha256'] == digest(root / 'PENDING_VALIDATION_PLAN.json')
        item = dict(instance=name, status=result['status'])
        if result['status'] in ['verified_feasible', 'certified_infeasible_diagnostic']:
            base = root / 'models' / name / 'Base.lp'
            assert digest(base) == preparation[name]['base_sha256']
            model = read_model(base)
            assert len(model[0]) == preparation[name]['rows']
            assert len(model[1]) == preparation[name]['columns']
            assert len(model[3]) == preparation[name]['integer_columns']
            if result['status'] == 'verified_feasible':
                folder = root / 'confirmation-references' / name
                proof = json.loads((folder / 'independent-certificate.json').read_text())
                assert digest(base) == result['original_model_sha256'] == proof['original_model_sha256']
                assert digest(folder / 'exact-witness.json') == result['witness_sha256'] == proof['witness_sha256']
                point = {n: Q(v) for n, v in json.loads((folder / 'exact-witness.json').read_text()).items()}
                cost = check_point(model, point)
                assert cost == Q(result['objective_exact']) == Q(proof['objective_exact_fraction'])
            else:
                assert digest(base) == certificates[name]['base_sha256']
                check_infeasibility(model, certificates[name])
            item.update(rows_checked=len(model[0]), variables_checked=len(model[1]), integers_checked=len(model[3]))
        else:
            assert result['status'] == 'unknown'
        records.append(item)
    assert len(records) == 160
    report = dict(status='passed', models_classified=len(records), records=records,
        verified_feasible=sum(r['status']=='verified_feasible' for r in records),
        certified_infeasible=sum(r['status']=='certified_infeasible_diagnostic' for r in records),
        unknown=sum(r['status']=='unknown' for r in records), optimizer_calls=0,
        third_party_packages=0, parser_scope='Strict multiline DummyLP dialect; exact rationals of binary64 data.',
        verifier_sha256=digest(Path(__file__).resolve()), optimality_certified=False)
    (root / 'STDLIB_REFERENCE_REPLAY.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Standard-library reference replay:', report['verified_feasible'], 'feasible,',
          report['certified_infeasible'], 'infeasible,', report['unknown'], 'unknown.')


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O: exact verification assertions are required.')
    if hasattr(sys, 'set_int_max_str_digits'):
        sys.set_int_max_str_digits(0)  # Trusted, hashed rational certificates.
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', type=Path, default=Path(__file__).resolve().parent)
    verify(parser.parse_args().directory.resolve())
