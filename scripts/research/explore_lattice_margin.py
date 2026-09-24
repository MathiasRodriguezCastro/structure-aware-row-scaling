#!/usr/bin/env python3
"""Exploratory *classical presolve* controls for the frozen binary stress set.

GCD division/RHS flooring are established reductions, not proposed novelty.
Midgap RHS positioning preserves integer feasibility but generally weakens the LP
relative to flooring. All frozen input models and original results are read-only.
"""
import argparse
import csv
from fractions import Fraction
from functools import reduce
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from residual_budget_experiment import solve_highs, solve_gurobi, solve_cplex


METHODS = ['GCD-floor', 'GCD-floor-GM', 'GCD-midgap-GM']


def transform(A, b, method):
    if not np.all(np.isfinite(A)) or not np.all(A == np.rint(A)):
        raise ValueError('This exploratory control requires exact integer coefficients.')
    gcds = [reduce(math.gcd, (abs(int(a)) for a in row)) for row in A]
    B = np.array([[int(a)//g for a in row] for row, g in zip(A, gcds)], dtype=float)
    floors = [Fraction.from_float(float(rhs))//g for rhs, g in zip(b, gcds)]
    rhs = np.array(floors, dtype=float)
    if method == 'GCD-midgap-GM':
        rhs += .5
    if method.endswith('-GM'):
        factors = np.array([1/math.sqrt(np.abs(row[row != 0]).min()*np.abs(row).max())
                            for row in B])
        B = factors[:, None]*B
        rhs = factors*rhs
    return B, rhs, gcds, floors


def check(A, b, c, optimum, x):
    if x is None:
        return False, False, None
    z = np.rint(x)
    exact = all(sum(Fraction.from_float(float(a))*int(v) for a, v in zip(row, z))
                <= Fraction.from_float(float(rhs)) for row, rhs in zip(A, b))
    domain = bool(np.all((z >= 0) & (z <= 1)))
    close = float(np.max(np.abs(x-z)))
    accepted = bool(exact and domain and close <= 1e-9 and
                    np.all(x >= -1e-9) and np.all(x <= 1+1e-9) and
                    int(c@z) == optimum)
    return accepted, bool(exact and domain), close


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[2]
    parser.add_argument('--models', type=Path, default=root/'results-revision/research-audit/budget-final/models')
    parser.add_argument('--out', type=Path, default=root/'results-revision/research-audit/exploration-lattice')
    parser.add_argument('--solvers', nargs='+', choices=['highs', 'gurobi', 'cplex'], default=['highs', 'gurobi'])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    versions, env = {}, None
    if 'highs' in args.solvers:
        import highspy
        versions['highspy_version'] = highspy.Highs().version()
    if 'gurobi' in args.solvers:
        import gurobipy as gp
        versions['gurobipy_version'] = gp.gurobi.version()
        env = gp.Env(empty=True)
        env.setParam('OutputFlag', 0)
        env.start()
    if 'cplex' in args.solvers:
        import cplex
        versions['cplex_version'] = cplex.Cplex().get_version()
    rows = []
    equivalence = []
    model_hashes = {}
    for model_path in sorted(args.models.glob('*.npz')):
        model_hashes[model_path.name] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        data = np.load(model_path)
        A, b, c, optimum = data['A'], data['b'], data['c'], int(data['optimum'])
        model_id = model_path.stem
        family, seed_txt, exp_txt = model_id.rsplit('_', 2)
        seed, exponent = int(seed_txt[1:]), int(exp_txt[1:])
        z = ((np.arange(2**len(c))[:, None] >> np.arange(len(c))) & 1).astype(np.int64)
        original = np.all(z@A.astype(np.int64).T <= np.floor(b)[None, :], axis=1)
        assert int((z[original]@c).max()) == optimum
        for method in METHODS:
            B, rhs, gcds, floors = transform(A, b, method)
            # Integer-domain equivalence is checked with exact normalized integers,
            # independently of potentially rounded GM products sent to a solver.
            W = np.array([[int(a)//g for a in row] for row, g in zip(A, gcds)], dtype=np.int64)
            reduced = np.all(z@W.T <= np.array(floors)[None, :], axis=1)
            assert np.array_equal(original, reduced)
            equivalence.append(dict(model_id=model_id, method=method, assignments=len(z), equal=True))
            for presolve in [False, True]:
                for solver in args.solvers:
                    if solver == 'highs':
                        status, x, elapsed, nodes = solve_highs(B, rhs, c, presolve, 1e-6, seed)
                    elif solver == 'cplex':
                        status, x, elapsed, nodes = solve_cplex(B, rhs, c, presolve, 1e-6, seed)
                    else:
                        status, x, elapsed, nodes = solve_gurobi(B, rhs, c, presolve, 1e-6, seed, env)
                    accepted, feasible, error = check(A, b, c, optimum, x)
                    rows.append(dict(model_id=model_id, family=family, seed=seed, exponent=exponent,
                                     method=method, presolve=presolve, solver=solver, status=status,
                                     rounded_optimal=accepted, rounded_exact_feasible=feasible,
                                     max_integrality_error=error, solver_seconds=elapsed, nodes=nodes,
                                     x=json.dumps(None if x is None else x.tolist()),
                                     exported_A=json.dumps(B.tolist()), exported_b=json.dumps(rhs.tolist())))
        print(model_id, flush=True)
    if env is not None:
        env.dispose()
    with (args.out/'runs.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = []
    for solver in args.solvers:
        for method in METHODS:
            group = [r for r in rows if r['solver']==solver and r['method']==method]
            counts.append(dict(solver=solver, method=method, n=len(group),
                               accepted=sum(r['rounded_optimal'] for r in group)))
    protocol = dict(purpose='exploratory controls; established presolve; no novelty claim',
                    models=str(args.models), model_sha256=model_hashes,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    methods=METHODS, solver_tolerance=1e-6, time_limit=10,
                    **versions,
                    model_count=len(model_hashes), solve_count=len(rows),
                    integer_equivalence_checks=equivalence, summary=counts)
    (args.out/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
