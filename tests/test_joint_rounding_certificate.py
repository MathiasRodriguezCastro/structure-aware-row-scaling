from fractions import Fraction as F
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research'))
from joint_rounding_certificate import certify_binary_block,row_gap


def test_joint_cancellation_strictly_improves_bound_aware_rows():
    M=10**9;A=[[M,1-M],[1-M,M]];b=[F(1,2)]*2
    t=[F(1,4)]*2;eta=F(1,10**6)
    for tau in [0,eta]:
        rows=certify_binary_block(A,b,t,eta,pairs=False,bound_tolerance=tau)
        joint=certify_binary_block(A,b,t,eta,bound_tolerance=tau)
        assert (1,1) in rows['uncovered']
        assert joint['certified']
        assert any(all(F(x)>0 for x in p['lambda_']) for p in joint['certificates'])


def test_two_row_certificate_complete_against_independent_lp():
    rng=np.random.default_rng(992313)
    for _ in range(60):
        A=rng.integers(-20,21,(2,3));b=rng.integers(-10,11,2)+.25
        t=rng.integers(0,101,2)/100.;eta=float(rng.integers(1,40))/100.
        tau=eta if rng.random()<.5 else 0.
        result=certify_binary_block(A,b,t,eta,bound_tolerance=tau)
        for z in np.ndindex(2,2,2):
            if np.all(A@z<=b):continue
            bounds=[(max(-eta,-v-tau),min(eta,1-v+tau)) for v in z]
            lp=linprog(np.zeros(3),A_ub=A,b_ub=b+t-A@z,bounds=bounds,method='highs',
                       options={'primal_feasibility_tolerance':1e-9})
            assert lp.status in (0,2),lp.message
            assert lp.success==(z in result['uncovered'])


def test_exact_boundary_is_not_strictly_certified():
    A=[[2,-1],[-1,2]];b=[F(1,2)]*2;eta=F(1,10)
    # x=(.9,.9) rounds to (1,1), violates each original row by exactly .4.
    result=certify_binary_block(A,b,[F(2,5)]*2,eta)
    assert (1,1) in result['uncovered']


def test_certificate_transports_under_row_reemission():
    A=[[10**9,1-10**9],[1-10**9,10**9]];b=[F(1,2)]*2;eta=F(1,10**6)
    lam=[F(1,2),F(1,2)];q=[F(3,7),F(19)]
    g=row_gap(A,b,[1,1],lam,eta)
    changed=row_gap([[q[i]*v for v in row] for i,row in enumerate(A)],
                    [q[i]*v for i,v in enumerate(b)],[1,1],[lam[i]/q[i] for i in range(2)],eta)
    assert g==changed


def test_hardness_construction_matches_small_sat_instances():
    from itertools import product
    patterns=list(product([0,1],repeat=3))
    # A clause indexed by pattern excludes exactly that binary assignment.
    for excluded in [patterns,patterns[:-1],patterns[::2]]:
        A=[];b=[]
        for pattern in excluded:
            signs=[1 if bit==0 else -1 for bit in pattern]
            A.append([-v for v in signs]+[1]);b.append(sum(v==1 for v in pattern))
        A.append([0,0,0,1]);b.append(.9)
        A=np.array(A,float);b=np.array(b,float)
        assert np.all(A@np.zeros(4)<=b)
        collision=False
        for z0 in patterns:
            z=np.array([*z0,1])
            bounds=[(max(0,v-.1),min(1,v+.1)) for v in z]
            lp=linprog(np.zeros(4),A_ub=A,b_ub=b,bounds=bounds,method='highs')
            collision|=lp.success
        assert collision==(len(excluded)<8)


def test_sparse_occurrence_copy_hardness_construction():
    from itertools import product
    patterns=list(product([0,1],repeat=3))
    for clauses in [patterns,patterns[:-1]]:
        count=len(clauses);n=4*count;rows=[];rhs=[]
        for k,pattern in enumerate(clauses):
            row=np.zeros(n);row[3*count+k]=1
            for j,bit in enumerate(pattern):row[3*k+j]=1 if bit else -1
            rows.append(row);rhs.append(sum(pattern))
        # Each occurrence copy has at most two chain edges, each represented
        # by two inequalities, plus its one clause row.
        for chain in [[3*k+j for k in range(count)] for j in range(3)]+[list(range(3*count,n))]:
            for first,second in zip(chain,chain[1:]):
                row=np.zeros(n);row[first]=1;row[second]=-1
                rows.extend([row,-row]);rhs.extend([0,0])
        row=np.zeros(n);row[3*count]=1;rows.append(row);rhs.append(.9)
        A=np.array(rows);b=np.array(rhs)
        assert set(np.unique(A))<=set([-1,0,1])
        assert np.max(np.count_nonzero(A,axis=1))<=4
        assert np.max(np.count_nonzero(A,axis=0))<=5
        assert np.all(A@np.zeros(n)<=b)
        collision=False
        for assignment in patterns:
            z=np.array(list(assignment)*count+[1]*count)
            bounds=[(max(0,v-.1),min(1,v+.1)) for v in z]
            lp=linprog(np.zeros(n),A_ub=A,b_ub=b,bounds=bounds,method='highs')
            collision|=lp.success
        assert collision==(len(clauses)<8)
