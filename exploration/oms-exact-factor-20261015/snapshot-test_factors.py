from fractions import Fraction as Q
import math
import random
from factors import select,p2,representable,score,defect,export_aware


def toy_values(bits=5,emin=-8,emax=5):
    return sorted({Q(m)*p2(k) for m in range(1,1<<bits,2)
                   for k in range(emin,emax+1) if k+m.bit_length()-1<=emax})


def test_complete_small_format_enumeration():
    rng=random.Random(20261015);values=toy_values()
    for _ in range(40):
        a=[rng.choice(values) for _ in range(3)];rhs=rng.choice(values)
        lo,hi=sorted(rng.sample(values,2));m,M=min(a),max(a)
        for powers in (False,True):
            feasible=[f for f in values if lo<=f<=hi and
                      (not powers or f.numerator.bit_count()==1) and
                      all(representable(f*z,5,-8,5) for z in [*a,rhs])]
            expected=min(feasible,key=lambda f:(score(f,m,M),-f)) if feasible else None
            assert select(tuple([*a,rhs]),m,M,lo,hi,powers,5,-8,5)==expected


def test_subnormal_and_overflow():
    tiny=Q(float.fromhex('0x0.0000000000001p-1022'))
    largest=Q(float.fromhex('0x1.fffffffffffffp+1023'))
    assert select((tiny,),tiny,tiny,Q(1,2),Q(1,2)) is None
    assert select((largest,),largest,largest,Q(2),Q(2)) is None
    assert select((tiny,),tiny,tiny,Q(1),Q(3))==3
    assert select((Q(3),),Q(3),Q(3),Q(3,4),Q(3,4))==Q(3,4)


def test_full_significand_forces_power_two():
    z=Q(float.fromhex('0x1.0000000000001p+0'))
    assert select((z,),z,z,Q(3,4),Q(3,4)) is None
    assert select((z,),z,z,Q(1,2),Q(2))==1


def test_finite_box_error_and_unbounded_coordinates():
    row=dict(rhs=.1,terms=[[0,.3],[1,1.]])
    vs=[dict(lb=-2.,ub=4.),dict(lb=None,ub=None)]
    alpha=Q(.7);error=defect(row,vs,alpha)
    endpoints=[abs((Q(.3)-Q(.7*.3)/alpha)*Q(x)+Q(.7*.1)/alpha-Q(.1)) for x in [-2.,4.]]
    assert error==max(endpoints)
    vs[0]['ub']=None
    assert defect(row,vs,alpha) is None
    assert defect(row,vs,Q(1,2))==0


def test_export_aware_preserves_real_contract():
    r=dict(rhs=0.,terms=[[0,3.],[1,-1.]])
    vs=[dict(lb=0.,ub=10.,type='C'),dict(lb=0.,ub=1.,type='B')]
    delta=Q(.01);alpha=export_aware(r,vs,delta)
    assert alpha is not None
    assert Q(1e-6)/alpha+Q(1e-9)+defect(r,vs,alpha)<=delta
