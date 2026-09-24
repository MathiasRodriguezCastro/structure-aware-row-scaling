#!/usr/bin/env python3
"""Classical, generator-aware integer-equivalent coefficient-reduction control.

This control uses the saved generator magnitude M. It makes no novelty claim.
Its reconstructed small-coefficient model is checked against all local binary
states, and the original optimum is independently recomputed by dynamic program.
"""
import argparse
import csv
from fractions import Fraction as F
import hashlib
from itertools import product
import json
from pathlib import Path
import shutil
import time

import numpy as np

from isolated_solvers import isolated_solve


def reconstruct(A, b, M, nlocal=6):
    n = A.shape[1]
    blocks = n // nlocal
    assert n == nlocal * blocks and A.shape[0] == 2 * blocks + 1
    assert np.array_equal(A, np.rint(A))
    rows, rhs, certificates = [], [], []
    for k in range(blocks):
        sl = slice(k * nlocal, (k + 1) * nlocal)
        pair = A[2 * k:2 * k + 2, sl].astype(np.int64)
        v = np.rint((pair[0] - pair[1]) / (2 * M)).astype(np.int64)
        u, w = pair[0] - M * v, pair[1] + M * v
        assert np.array_equal(M * v + u, pair[0])
        assert np.array_equal(-M * v + w, pair[1])
        # For any binary z with integral v'z >= 1, original row 1 fails;
        # with v'z <= -1, original row 2 fails. These exact lower bounds
        # certify v'z=0 at every original integer feasible point.
        dominance = [F(int(M + np.minimum(u, 0).sum())) - F(float(b[2 * k])),
                     F(int(M + np.minimum(w, 0).sum())) - F(float(b[2 * k + 1]))]
        assert min(dominance) > 0
        small_rhs = [int(F(float(b[2 * k])) // 1),
                     int(F(float(b[2 * k + 1])) // 1)]
        for a, r in [(v, 0), (-v, 0), (u, small_rhs[0]), (w, small_rhs[1])]:
            full = np.zeros(n, dtype=np.int64)
            full[sl] = a
            rows.append(full)
            rhs.append(r)
        certificates.append(dict(v=v.tolist(), u=u.tolist(), w=w.tolist(),
                                 small_rhs=small_rhs,
                                 dominance_margins=list(map(str, dominance))))
    rows.append(A[-1].astype(np.int64))
    rhs.append(int(F(float(b[-1])) // 1))
    return np.array(rows, dtype=float), np.array(rhs, dtype=float), certificates


def independent_check(A, b, c, B, rhs, saved_opt, nlocal=6):
    states = np.array(list(product([0, 1], repeat=nlocal)), dtype=np.int64)
    n = A.shape[1]
    assert np.max(np.abs(A)) * n < 2 ** 62
    assert np.array_equal(c, np.rint(c))
    floors = np.array([int(F(float(r)) // 1) for r in b], dtype=np.int64)
    cap = int(floors[-1])
    resource = A[-1].astype(np.int64)
    profit = c.astype(np.int64)
    assert np.min(resource) >= 0
    dp = {0: 0}
    cardinalities = []
    for k in range(n // nlocal):
        sl = slice(k * nlocal, (k + 1) * nlocal)
        original_good = np.all(states @ A[2 * k:2 * k + 2, sl].astype(np.int64).T
                               <= floors[2 * k:2 * k + 2], axis=1)
        control_good = np.all(states @ B[4 * k:4 * k + 4, sl].astype(np.int64).T
                              <= rhs[4 * k:4 * k + 4].astype(np.int64), axis=1)
        assert np.array_equal(original_good, control_good)
        good = states[original_good]
        cardinalities.append(len(good))
        next_dp = {}
        for z in good:
            weight, value = int(z @ resource[sl]), int(z @ profit[sl])
            for old_weight, old_value in dp.items():
                total = old_weight + weight
                if total <= cap:
                    next_dp[total] = max(next_dp.get(total, -10**18), old_value + value)
        dp = next_dp
    optimum = max(dp.values())
    assert optimum == saved_opt
    return optimum, cardinalities


def exact_max_violation(A, b, x):
    return float(max([F(0)] + [sum((F(float(a)) * F(float(y)) for a, y in zip(row, x)), F(0))
                                 - F(float(r)) for row, r in zip(A, b)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise ValueError('Use a new output directory; saved controls are never overwritten')
    args.out.mkdir(parents=True)
    sources = {}
    for name in ['explore_lattice_decomposition.py', 'isolated_solvers.py', 'residual_budget_experiment.py']:
        p = Path(__file__).parent / name
        sources[name] = hashlib.sha256(p.read_bytes()).hexdigest()
        shutil.copy2(p, args.out / ('source-' + name))
    models = sorted(args.input.glob('M*_s*.npz'))
    (args.out / 'design.json').write_text(json.dumps(dict(
        purpose='Classical generator-aware lattice decomposition baseline; no novelty claim',
        generator_metadata='M from saved instance identifier',
        models=[p.name for p in models], model_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in models},
        source_sha256=sources, solvers=['highs', 'gurobi'], presolve=[False, True],
        epsilon=1e-6, eta=1e-6, external_wall_limit=25,
        primary='Exact original feasibility of rounded assignment',
        secondary='Exact original optimum, checked by independently recomputed dynamic program'), indent=2) + '\n')
    runs, certificates = [], {}
    for path in models:
        model = np.load(path)
        A, b, c = model['A'], model['b'], model['c']
        M, seed = map(int, path.stem[1:].split('_s'))
        tic = time.perf_counter()
        B, rhs, proof = reconstruct(A, b, M)
        prep = time.perf_counter() - tic
        tic = time.perf_counter()
        optimum, cardinalities = independent_check(A, b, c, B, rhs, int(model['optimum']))
        check_seconds = time.perf_counter() - tic
        certificates[path.stem] = dict(blocks=proof, local_feasible_cardinalities=cardinalities,
                                      optimum_recomputed=optimum, equivalence_checked=True)
        np.savez_compressed(args.out / path.name, A_original=A, b_original=b, c=c,
                            A_exported=B, b_exported=rhs, optimum=optimum)
        for presolve in [False, True]:
            for solver in ['highs', 'gurobi']:
                status, x, wall, nodes = isolated_solve(solver, B, rhs, c, presolve, 1e-6, seed)
                feasible = optimal = within_eta = False
                error = objective = exported_violation = None
                if x is not None:
                    z = np.rint(x)
                    error = float(np.max(abs(x - z)))
                    within_eta = error <= 1e-6
                    if np.all((z >= 0) & (z <= 1)):
                        zi = z.astype(np.int64)
                        floors = np.array([int(F(float(r)) // 1) for r in b], dtype=np.int64)
                        feasible = bool(np.all(A.astype(np.int64) @ zi <= floors))
                        objective = int(c.astype(np.int64) @ zi)
                        optimal = bool(feasible and objective == optimum)
                    exported_violation = exact_max_violation(B, rhs, x)
                record = dict(M=M, seed=seed, method='Lattice-decomposition', solver=solver,
                              presolve=presolve, status=status, rounded_feasible=feasible,
                              rounded_optimal=optimal, within_eta=within_eta,
                              integer_error=error, objective_rounded=objective, true_optimum=optimum,
                              prep_seconds=prep, equivalence_and_dp_seconds=check_seconds,
                              solver_seconds=wall, nodes=nodes, exported_rows=len(B),
                              nnz=int(np.count_nonzero(B)), max_abs_coefficient=float(np.max(abs(B))),
                              max_exported_violation=exported_violation,
                              x=json.dumps(None if x is None else x.tolist()))
                runs.append(record)
                with (args.out / 'runs-progress.jsonl').open('a') as stream:
                    stream.write(json.dumps(record) + '\n')
        print(path.stem, 'complete', flush=True)
    with (args.out / 'runs.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(runs[0]))
        writer.writeheader()
        writer.writerows(runs)
    (args.out / 'certificates.json').write_text(json.dumps(certificates, indent=2) + '\n')
    summary = {solver: dict(n=sum(r['solver'] == solver for r in runs),
                           feasible=sum(r['rounded_feasible'] for r in runs if r['solver'] == solver),
                           optimal=sum(r['rounded_optimal'] for r in runs if r['solver'] == solver))
               for solver in ['highs', 'gurobi']}
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
