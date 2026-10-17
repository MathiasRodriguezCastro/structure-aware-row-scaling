import itertools
import math
import random
from fractions import Fraction
import pytest
import joint

def test_extreme_binary64_shift_intervals():
    for value in [math.ulp(0.),3*math.ulp(0.),1.,math.nextafter(1.,2.),float.fromhex('0x1.fffffffffffffp1023'),-2.**-1000]:
        lo,hi=joint.shift_range(value)
        for k in [lo,hi]:assert Fraction(math.ldexp(value,k))==Fraction(value)*joint.power(k)
        with pytest.raises((OverflowError,AssertionError)):
            assert math.isfinite(math.ldexp(value,hi+1))
        assert Fraction(math.ldexp(value,lo-1))!=Fraction(value)*joint.power(lo-1)

def test_graph_against_exhaustive_integer_potentials():
    rng=random.Random(20261016)
    for _ in range(100):
        graph=joint.Graph(['zero','a','b','c'])
        for node in [1,2,3]:graph.box(node,-2,2,'box')
        for _ in range(10):graph.edge(rng.randrange(4),rng.randrange(4),rng.randrange(-3,4),'random')
        points=([0,*p] for p in itertools.product(range(-2,3),repeat=3))
        feasible=any(all(p[b]-p[a]<=c for a,b,c,_ in graph.edges) for p in points)
        result=graph.solve();assert ('potential' in result)==feasible;assert graph.check(result)

def test_joint_recovers_row_incompatibility_without_scaling_integer():
    model={'rows':{'on':{'terms':{'z':2.**30,'x':-1.},'rhs':0.}},
        'columns':['z','x'],'integers':{'z'},'delta':{},'E':{},'costs':{'z':0.,'x':3.},'bounds':{'z':(0.,1.),'x':(0.,2.**30)}}
    rows=joint.construct(model,10,False,window=(2.**-10,2.**10)).solve()
    assert 'negative_cycle' in rows
    graph=joint.construct(model,10,True,window=(2.**-10,2.**10));result=graph.solve()
    assert 'potential' in result;graph.check(result)
    p=dict(zip(graph.labels,result['potential']));assert p['col:z']==0

def test_rounding_incompatibility_persists_with_free_continuous_columns():
    model={'rows':{'on':{'terms':{'z':2.**30,'x':-1.},'rhs':0.}},
        'columns':['z','x'],'integers':{'z'},'delta':{'on':Fraction(1)},'E':{'on':Fraction(2)},
        'costs':{'z':0.,'x':0.},'bounds':{'z':(0.,1.),'x':(0.,math.inf)}}
    for columns in [False,True]:assert 'negative_cycle' in joint.construct(model,40,columns).solve()

def test_integer_graph_against_independent_continuous_lp():
    import numpy as np
    from scipy.optimize import linprog
    rng=random.Random(2026101605)
    for _ in range(100):
        graph=joint.Graph(['zero','a','b','c','d'])
        for node in range(1,5):graph.box(node,-5,5,'box')
        for _ in range(12):graph.edge(rng.randrange(5),rng.randrange(5),rng.randrange(-5,6),'random')
        A=np.zeros((len(graph.edges),5));b=[]
        for i,(a,c,d,_) in enumerate(graph.edges):A[i,c]+=1;A[i,a]-=1;b.append(d)
        lp=linprog(np.zeros(5),A_ub=A,b_ub=b,bounds=[(0,0),*[(None,None)]*4],method='highs')
        assert lp.status in [0,2]
        assert ('potential' in graph.solve())==(lp.status==0)
