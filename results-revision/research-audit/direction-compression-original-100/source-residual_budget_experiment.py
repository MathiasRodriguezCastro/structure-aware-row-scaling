#!/usr/bin/env python3
"""Enumerated binary stress tests of row scaling and residual budgets.

This is an adversarial mechanism experiment, not an application runtime benchmark.
Models, solutions, versions and protocol are retained; all binary optima are
enumerated independently. No solver status is treated as a primal certificate.
"""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import time

import numpy as np
from scipy.sparse import csr_matrix

from budget_scaling import select_factor, dyadic_factor, exact_row_violation

METHODS = ['Base', 'GM', 'L2', 'GM-tight', 'Budget-only', 'Budget-GM', 'Budget-round',
           'Dyadic-GM', 'Budget-dyadic']
FAMILIES = ['cardinality', 'packing', 'signed']


def generate(family, seed, exponent, n=12):
    rng = np.random.default_rng(20260908 + seed)
    if family == 'cardinality':
        weights = np.ones((1, n), dtype=int)
    elif family == 'packing':
        weights = rng.integers(1, 10, size=(3, n))
    else:
        weights = rng.integers(-9, 10, size=(3, n))
        weights[weights == 0] = 1
    cap = np.maximum(2, np.floor(np.maximum(weights, 0).sum(axis=1)*.55)).astype(int)
    profits = rng.integers(1, 31, size=n)
    scale = 10.**exponent
    A = weights.astype(float)*scale
    b = cap.astype(float)*scale - .1
    delta = np.full(len(b), .01)
    assignments = ((np.arange(2**n)[:, None] >> np.arange(n)) & 1).astype(int)
    # Exactly: integer weights*x <= cap - .1/scale iff weights*x <= cap-1.
    # Confirm that the binary64 RHS still lies strictly between adjacent integers.
    for target, rhs in zip(cap, b):
        assert Fraction(int(target-1))*Fraction.from_float(scale) < Fraction.from_float(rhs)
        assert Fraction.from_float(rhs) < Fraction(int(target))*Fraction.from_float(scale)
    feasible = np.all(assignments @ weights.T <= cap[None, :]-1, axis=1)
    optimum = int((assignments[feasible] @ profits).max())
    return A, b, profits.astype(float), delta, optimum


def factors(A, b, delta, method):
    if method == 'Base':
        return np.ones(len(A))
    if method == 'Budget-only':
        return 1e-6/delta
    if method in {'Dyadic-GM', 'Budget-dyadic'}:
        ds = [dyadic_factor(row, rhs, d if method=='Budget-dyadic' else None)
              for row, rhs, d in zip(A, b, delta)]
        if any(r.factor is None for r in ds):
            return None
        return np.array([r.factor for r in ds])
    if method in {'Budget-GM', 'Budget-round'}:
        decisions = [select_factor(row, d, rounding_allowance=(1e-6*np.abs(row).sum()
                                   if method == 'Budget-round' else 0.)) for row, d in zip(A, delta)]
        if any(r.factor is None for r in decisions):
            return None
        return np.array([r.factor for r in decisions])
    if method == 'L2':
        return 1./np.linalg.norm(A, axis=1)
    return np.array([1./math.sqrt(np.abs(row[row != 0]).min()*np.abs(row).max()) for row in A])


def solve_highs(A, b, profits, presolve, tolerance, seed):
    import highspy as hs
    h = hs.Highs()
    for key, value in [('output_flag', False), ('threads', 1), ('random_seed', seed),
                       ('presolve', 'on' if presolve else 'off'), ('time_limit', 10.),
                       ('mip_rel_gap', 0.), ('mip_abs_gap', 0.),
                       ('primal_feasibility_tolerance', tolerance),
                       ('mip_feasibility_tolerance', tolerance)]:
        assert h.setOptionValue(key, value) == hs.HighsStatus.kOk, key
    m, n = A.shape
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), -profits)
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), np.ones(n, dtype=np.uint8))
    mat = csr_matrix(A)
    h.addRows(m, np.full(m, -hs.kHighsInf), b, mat.nnz,
              mat.indptr.astype(np.int32), mat.indices.astype(np.int32), mat.data)
    tic = time.perf_counter()
    h.run()
    elapsed = time.perf_counter()-tic
    sol = h.getSolution()
    info = h.getInfo()
    return (h.getModelStatus().name, np.array(sol.col_value) if sol.value_valid else None,
            elapsed, info.mip_node_count)


def solve_gurobi(A, b, profits, presolve, tolerance, seed, env):
    import gurobipy as gp
    m = gp.Model(env=env)
    for key, value in [('OutputFlag', 0), ('Threads', 1), ('Seed', seed),
                       ('Presolve', -1 if presolve else 0), ('TimeLimit', 10.),
                       ('MIPGap', 0.), ('MIPGapAbs', 0.),
                       ('FeasibilityTol', tolerance), ('IntFeasTol', tolerance)]:
        m.setParam(key, value)
    x = m.addMVar(A.shape[1], vtype=gp.GRB.BINARY)
    m.addMConstr(A, x, '<', b)
    m.setObjective(-profits@x)
    tic = time.perf_counter()
    m.optimize()
    elapsed = time.perf_counter()-tic
    result = (str(m.Status), np.array(x.X) if m.SolCount else None, elapsed, m.NodeCount)
    m.dispose()
    return result


def check(A, b, profits, delta, optimum, x):
    if x is None:
        return dict(primal_budget_ok=False, rounded_exact_feasible=False,
                    rounded_optimal=False, max_budget_ratio=None, max_integrality_error=None)
    violations = [exact_row_violation(row, rhs, x) for row, rhs in zip(A, b)]
    budget_ok = all(v <= Fraction.from_float(float(d)) for v, d in zip(violations, delta))
    integers = np.rint(x)
    integer_error = float(np.max(np.abs(x-integers)))
    bounds_ok = bool(np.all(x >= -1e-9) and np.all(x <= 1.+1e-9))
    exact_ok = all(exact_row_violation(row, rhs, integers) == 0 for row, rhs in zip(A, b))
    obj = int(profits@integers)
    return dict(primal_budget_ok=bool(budget_ok and bounds_ok and integer_error <= 1e-9),
                rounded_exact_feasible=bool(exact_ok and np.all((integers >= 0) & (integers <= 1))),
                rounded_optimal=bool(exact_ok and obj == optimum and bounds_ok and integer_error <= 1e-9),
                max_budget_ratio=max(float(v)/d for v, d in zip(violations, delta)),
                max_integrality_error=integer_error)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seeds', type=int, default=8)
    ap.add_argument('--start-seed', type=int, default=100)
    ap.add_argument('--solvers', nargs='+', choices=['highs', 'gurobi'], default=['highs', 'gurobi'])
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    models = args.out/'models'
    models.mkdir(exist_ok=True)
    versions = {'python': platform.python_version(), 'numpy': np.__version__}
    env = None
    if 'highs' in args.solvers:
        import highspy
        versions['highs'] = highspy.Highs().version()
    if 'gurobi' in args.solvers:
        import gurobipy as gp
        versions['gurobi'] = gp.gurobi.version()
        env = gp.Env(empty=True)
        env.setParam('OutputFlag', 0)
        env.start()
    protocol = dict(families=FAMILIES, methods=METHODS,
                    seeds=list(range(args.start_seed, args.start_seed+args.seeds)),
                    exponents=[0, 3, 6, 9], n_binary=12, presolve=[False, True],
                    row_budget=.01, row_margin=.1, solver_tolerance=1e-6,
                    tight_tolerance=1e-9, time_limit=10, versions=versions,
                    solvers=args.solvers, purpose='adversarial mechanism; no runtime generalization',
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    selector_sha256=hashlib.sha256((Path(__file__).parent/'budget_scaling.py').read_bytes()).hexdigest())
    (args.out/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    rows = []
    for family in FAMILIES:
        for seed in protocol['seeds']:
            for exponent in protocol['exponents']:
                A, b, c, delta, optimum = generate(family, seed, exponent)
                model_id = f'{family}_s{seed}_e{exponent}'
                np.savez_compressed(models/f'{model_id}.npz', A=A, b=b, c=c,
                                    delta=delta, optimum=optimum)
                for presolve in [False, True]:
                    # Fixed randomized ordering mitigates an incidental warm-cache ordering effect.
                    order = np.random.default_rng(seed+exponent+int(presolve)).permutation(METHODS)
                    for method in order:
                        d = factors(A, b, delta, method)
                        for solver in args.solvers:
                            tol = 1e-9 if method == 'GM-tight' else 1e-6
                            if d is None:
                                status, x, wall, nodes = 'ABSTAIN', None, 0., 0
                            elif solver == 'highs':
                                status, x, wall, nodes = solve_highs(d[:, None]*A, d*b, c, presolve, tol, seed)
                            else:
                                status, x, wall, nodes = solve_gurobi(d[:, None]*A, d*b, c, presolve, tol, seed, env)
                            row = dict(model_id=model_id, family=family, seed=seed, exponent=exponent,
                                       presolve=presolve, method=method, solver=solver, status=status,
                                       solver_tolerance=tol, solver_seconds=wall, nodes=nodes,
                                       true_optimum=optimum, x=json.dumps(x.tolist() if x is not None else None),
                                       factors=json.dumps(d.tolist() if d is not None else None),
                                       **check(A, b, c, delta, optimum, x))
                            rows.append(row)
                print(f'{model_id}: {len(rows)} solves', flush=True)
    if env is not None:
        env.dispose()
    with (args.out/'runs.csv').open('w') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(json.dumps({'runs': len(rows), 'output': str(args.out)}))


if __name__ == '__main__':
    main()
