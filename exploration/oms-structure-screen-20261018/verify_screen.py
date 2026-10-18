"""Independent full-matrix SVD/iteration and rational contract checks; no solver."""
from fractions import Fraction as F
import json
import math

import numpy as np
from scipy.linalg import block_diag, svdvals

from screen import (HERE, BUDGETS, POLICIES, blocks, condition,
                    equivariant_equilibrate, factor_rows, native_models)


def full_matrix(b, c, d, k):
    top = np.c_[block_diag(*([b]*k)), np.zeros((k*len(b), d.shape[1]))]
    return np.r_[top, np.c_[np.tile(np.diag(c), (1,k)), d]]


def dense_equilibrate(a):
    a = a.copy()
    for _ in range(10):
        for axis in (1,0):
            norms = abs(a).max(axis=axis)
            norms[norms == 0] = 1.
            scale = np.ldexp(np.ones(len(norms)), -np.rint(np.log2(norms)/2).astype(int))
            a *= scale[:,None] if axis == 1 else scale[None,:]
    return a


def main():
    checks = 0
    models = native_models()
    assert models == json.loads((HERE/'models.json').read_text())
    for model in models:
        k = len(model['demands'])
        b,d = blocks(model)
        assert np.linalg.matrix_rank(b) == model['nodes']-1
        role, ablation = factor_rows(model,'Role-Hybrid'), factor_rows(model,'Coupling-only')
        assert [r['factor'] for r in role] == [r['factor'] for r in ablation]
        for budget in BUDGETS:
            for r in factor_rows(model,'Flat-L2',budget):
                epsilon,delta,E = F(1e-6),F(budget),F(r['allowance_exact'])
                lo = max(epsilon/(delta-E),F(1e-9)/F(r['minimum'])) if delta>E else None
                hi = F(1e9)/F(r['maximum'])
                feasible = lo is not None and lo <= hi
                assert feasible == r['compatible']
                if feasible:
                    alpha=F(r['factor'])
                    assert alpha >= lo and alpha <= hi
                    assert epsilon/alpha+E <= delta
                checks += k if r['role']=='local' else 1
        # Actual full native R01; small replicated cores for each native topology.
        count = k if model['name']=='r01.1' else 3
        for policy in POLICIES:
            factors = factor_rows(model,policy)
            local=np.array([r['factor'] for r in factors if r['role']=='local'])
            coupling=np.array([r['factor'] for r in factors if r['role']=='coupling'])
            bb,cc,dd=local[:,None]*b,coupling,coupling[:,None]*d
            a=full_matrix(bb,cc,dd,count)
            eq=dense_equilibrate(a)
            eb,ec,ed=equivariant_equilibrate(bb,cc,dd,10)
            assert np.array_equal(eq,full_matrix(eb,ec,ed,count))
            for full,parts in [(a,(bb,cc,dd)),(eq,(eb,ec,ed))]:
                singular=svdvals(full)
                positive=singular[singular > np.finfo(float).eps*max(full.shape)*singular[0]]
                compressed=condition(*parts,count)
                assert len(positive)==compressed['numerical_rank']
                assert math.isclose(positive[0]/positive[-1],compressed['kappa_positive'],rel_tol=2e-10)
                checks += 1
    result=dict(checks=checks, models=len(models), independent_full_svd_comparisons=120,
                checks_passed=True, optimizer_calls=0)
    (HERE/'verification-screen.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':
    main()
