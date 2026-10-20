#!/usr/bin/env python3
"""Check the adapted acceptance path on saved pilot data without optimization."""
from fractions import Fraction as Q
import sys
import numpy as np
from runner import HERE, ROOT, load, save, sha, library
from replay_pilot import candidate_cost, candidate_audit
from verify_reference_witnesses_stdlib import read_model


def main():
    follow = library(ROOT / 'exploration/orf-v15-verified-20261019/study.py', 'confirmation_fixture_follow')
    fixtures = []
    for family in ['simple', 'sgtm', 'completo']:
        for solver in ['gurobi', 'cplex']:
            candidates = sorted((HERE / 'pilot-runs').glob('*-' + solver + '-s401-Base/result.json'))
            for path in candidates:
                result = load(path)
                name = result['job']['instance']
                metadata = load(HERE / 'MODEL_PREPARATION.json')['models'][name]
                if metadata['family'] == family and metadata['horizon'] == 24 and result['status'] == 'completed':
                    break
            else:
                raise AssertionError('Required saved pilot fixture is missing.')
            base = path.parent / 'Base.lp'
            model = follow.checker.canonical(base)
            literal = read_model(base)
            assert model[0] == literal[0] and model[3] == literal[3]
            assert {n: c for n, c in model[2].items() if c} == literal[2] and model[5] == 0
            model = (model[0], {n: tuple(literal[1][n]) for n in model[1]}, *model[2:])
            with np.load(path.parent / 'candidates.npz', allow_pickle=False) as arrays:
                names = arrays['names'].tolist()
                assert names == list(model[1])
                vector = arrays['x'][-1]
            point = {n: Q.from_float(float(x)) for n, x in zip(names, vector)}
            _, rounded = candidate_cost(model, point)
            assert follow.verify(model, vector, follow.CONTRACTS['b100']) == candidate_audit(model, point, rounded)
            corrupt = vector.copy()
            binary = next(n for n in names if n in model[3])
            corrupt[names.index(binary)] = .5
            assert not follow.verify(model, corrupt, follow.CONTRACTS['b100'])['domain_pass']
            point = {n: Q.from_float(float(x)) for n, x in zip(names, corrupt)}
            _, rounded = candidate_cost(model, point)
            assert not candidate_audit(model, point, rounded)['domain_pass']
            large = next((n for n in names if literal[1][n][1] is not None and literal[1][n][1] >= 10**20), None)
            if large is not None:
                corrupt = vector.copy(); corrupt[names.index(large)] = float(literal[1][large][1] * 2)
                assert not follow.verify(model, corrupt, follow.CONTRACTS['b100'])['domain_pass']
            fixtures.append(dict(instance=name, solver=solver, saved_candidate_sha256=sha(path.parent / 'candidates.npz'),
                independent_audit_equal=True, fractional_integer_rejected=True,
                explicit_large_bound_enforced=True if large is not None else None))
    assert any(r['explicit_large_bound_enforced'] for r in fixtures)
    save(HERE / 'CONFIRMATION_EXECUTION_CHECK.json', dict(status='passed', fixtures=fixtures,
        optimizer_calls=0, fixture_source='closed resource pilot, not new confirmation outcomes',
        source_sha256=sha(HERE / 'check_confirmation_execution.py')))
    print('Confirmation acceptance path: six saved fixtures and corrupted domains checked; zero optimizer calls.')


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    if hasattr(sys, 'set_int_max_str_digits'):
        sys.set_int_max_str_digits(0)
    main()
