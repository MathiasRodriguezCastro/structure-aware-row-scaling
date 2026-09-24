"""Exploratory redundant-row compiler with exact validity and cell certificates.

Classical ingredients: nonnegative row aggregation, safe coefficient rounding,
Farkas separation, and finite set cover. Novelty of the combined use is under review.
The input is a small binary block. No solver is called by this compiler.
"""
from fractions import Fraction as F
from itertools import product,combinations
import math
import numpy as np
from joint_rounding_certificate import rational,multipliers,row_gap
from budget_scaling import dyadic_factor


def upward(x):
    y=float(x)
    return math.nextafter(y,math.inf) if F(y)<x else y


def aggregate(A,b,lam):
    """Return a VALID redundant binary64 row, relaxed outward over [0,1]^n.

    The positive dyadic gamma sets moderate coefficient magnitudes. Coefficients
    are rounded independently; the RHS pays the exact support of that rounding
    error. Thus every point of the original LP in its box satisfies this row.
    """
    m=len(A);n=len(A[0]);lam=list(map(rational,lam))
    p=[sum((lam[i]*rational(A[i][j]) for i in range(m)),F(0)) for j in range(n)]
    q=sum((lam[i]*rational(b[i]) for i in range(m)),F(0))
    nz=[abs(x) for x in p if x]
    if not nz:return None
    target=-.5*(math.log2(float(min(nz)))+math.log2(float(max(nz))))
    gamma=F(2)**math.ceil(target)
    p=[gamma*x for x in p];q*=gamma
    ahat=[float(x) for x in p]
    correction=sum((max(F(0),F(x)-v) for x,v in zip(ahat,p)),F(0))
    bhat=upward(q+correction)
    validity=F(bhat)-q-correction
    assert validity>=0
    return dict(a=ahat,b=bhat,lambda_=list(map(str,lam)),gamma=str(gamma),
                rounding_allowance=str(correction),validity_margin=str(validity))


def compile_block(A,b,eta=1e-6,epsilon=1e-6,all_guards=False):
    A=np.asarray(A,float);b=np.asarray(b,float);eta=rational(eta);eps=rational(epsilon)
    scales=[dyadic_factor(row,rhs).factor for row,rhs in zip(A,b)]
    if any(d is None for d in scales):raise ValueError('No exact dyadic original-row export')
    d=np.array(scales)
    candidates=multipliers(A)
    candidates.append(tuple([F(1,len(A))]*len(A)))
    # Equivalent scaled multiplier rays may create the same exported cut.
    guards=[];seen=set()
    for lam in candidates:
        guard=aggregate(A,b,lam)
        if guard is None:continue
        key=(*guard['a'],guard['b'])
        if key not in seen:guards.append(guard);seen.add(key)
    bad=[];base_proofs=[]
    for z in product([0,1],repeat=A.shape[1]):
        if all(sum(F(a)*v for a,v in zip(row,z))<=F(rhs) for row,rhs in zip(A,b)):continue
        margins=[row_gap([row],[rhs],z,[1],eta,eta)-eps/F(float(alpha))
                 for row,rhs,alpha in zip(A,b,d)]
        if max(margins)>0:
            base_proofs.append(dict(z=z,row=int(np.argmax(margins)),margin=str(max(margins))))
        else:bad.append(z)
    masks=[]
    for guard in guards:
        mask=0
        for i,z in enumerate(bad):
            g=row_gap([guard['a']],[guard['b']],z,[1],eta,eta)-eps
            if g>0:mask|=1<<i
        masks.append(mask)
    target=(1<<len(bad))-1
    selected=None
    if all_guards:selected=list(range(len(guards)))
    else:
        for size in range(len(guards)+1):
            valid=[]
            for subset in combinations(range(len(guards)),size):
                mask=0
                for j in subset:mask|=masks[j]
                if mask==target:
                    valid.append((sum(np.count_nonzero(guards[j]['a']) for j in subset),subset))
            if valid:selected=list(min(valid)[1]);break
    mask=0
    if selected is not None:
        for j in selected:mask|=masks[j]
    proven=selected is not None and mask==target
    return dict(factors=d.tolist(),candidates=guards,selected=selected,
                certified=proven,unsafe_centers=bad,base_proofs=base_proofs,
                masks=list(map(str,masks)),eta=str(eta),epsilon=str(eps),
                bound_tolerance=str(eta))


def partial_nogoods(A,b,unsafe,all_bad=False):
    """Known Boolean no-good clauses, selected to cover only unsafe centers.

    Exhaustive local truth tables make the validity check exact. This is not a
    new cutting-plane family. The research question is which clauses the numerical
    certificate requires, compared with imposing the whole local truth table.
    """
    A=np.asarray(A,float);n=A.shape[1];centers=list(product([0,1],repeat=n))
    good=[z for z in centers if all(sum(F(a)*v for a,v in zip(row,z))<=F(float(rhs)) for row,rhs in zip(A,b))]
    bad=[z for z in centers if z not in good]
    targets=bad if all_bad else [tuple(z) for z in unsafe]
    if not targets:return []
    candidates=[]
    for size in range(1,n+1):
        for cols in combinations(range(n),size):
            for bits in product([0,1],repeat=size):
                if any(all(z[j]==v for j,v in zip(cols,bits)) for z in good):continue
                # Keep prime clauses; larger clauses containing an existing
                # forbidden partial assignment add no coverage.
                pattern=set(zip(cols,bits))
                if any(set(c['pattern']).issubset(pattern) for c in candidates):continue
                mask=sum(1<<i for i,z in enumerate(targets) if all(z[j]==v for j,v in zip(cols,bits)))
                if not mask:continue
                a=np.zeros(n)
                for j,v in zip(cols,bits):a[j]=1 if v else -1
                candidates.append(dict(pattern=list(zip(cols,bits)),a=a.tolist(),b=float(sum(bits)-1),mask=mask))
    # Greedy set cover (not claimed minimum); deterministic sparsity tie-break.
    covered=0;target=(1<<len(targets))-1;chosen=[]
    while covered!=target:
        j=max(range(len(candidates)),key=lambda j: ((candidates[j]['mask'] & ~covered).bit_count(),
                                                    -len(candidates[j]['pattern']),-j))
        item=candidates[j];gain=item['mask'] & ~covered
        if not gain:raise AssertionError('uncovered impossible local assignment')
        chosen.append(item);covered|=item['mask']
    return chosen
