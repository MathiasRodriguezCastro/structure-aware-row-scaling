from fractions import Fraction as Q
import math

import numpy as np

from preventive import envelope,power2,complete_families,sparse_model_envelope,canonical_system
from dispatch import exact_multipliers,cut_from,export_cut,select,cosine


def test_envelope_covers_complete_dual_family_and_primitive_farkas_ray():
    e,scales,A,cK,rK=envelope([[-1],[1]],[0,Q(1,2)],[[1],[0]],[1],[1,1])
    V,R=complete_families(A,[1]);w=list(map(Q,scales));t=power2(-e['scale_exponent'])
    assert len(V)==1 and len(R)==1
    assert max(sum(abs(x)*y for x,y in zip(pi,w)) for pi in V)<=cK
    assert max(sum(abs(x)*y for x,y in zip(r,w)) for r in R)<=rK
    assert cK*t<=1 and rK*t<=Q(1,2)


def test_integerization_includes_integer_coefficients_and_rhs_denominators():
    _,scales,A,_,_=envelope([[-1],[1]],[Q(1,3),1],[[Q(1,7)],[0]],[1],[1,1])
    assert scales[0]==21 and A[0]==[-21]


def test_sparse_and_dense_bounds_agree_for_fixed_and_integer_variables():
    m={'variables':[{'cost':0.,'integer':True,'lower':0.,'upper':1.},
                    {'cost':1.,'integer':False,'lower':0.,'upper':.5}],
       'rows':[{'terms':{'0':1.,'1':-1.},'sense':'<','rhs':0.}]}
    dense=envelope(*canonical_system(m))[0];assert sparse_model_envelope(m)==dense


def test_exact_projection_and_outward_export_cover_unseen_continuous_masters():
    s={'cost':[1.], 'rows':[{'name':'production','a':{'0':-3.},'b':{'0':1.},'rhs':0.},
                            {'name':'bound:y:lower','a':{'0':-1.},'b':{},'rhs':0.}]}
    mu=exact_multipliers(s,[-1/3,0.],'cost');c=cut_from(s,mu,'cost',1,[1.],[1/3])
    e=export_cut(c,[{'lower':0.,'upper':1.}])
    for u in [Q(0),Q(1,7),Q(1)]:
        y=u/3
        assert Q(e['terms']['0'])*u+Q(e['theta'])*y>=Q(e['rhs'])


def test_equality_projection_exposes_dependence_hidden_by_raw_orthogonality():
    a=np.array([1.,0.]);b=np.array([0.,1.]);P=np.ones((2,2))/2
    assert cosine(a,b)==0 and abs(cosine(P@a,P@b)-1)<1e-12


def test_every_filter_retains_a_violated_anchor_and_original_cuts():
    cuts=[{'t':t,'kind':'cost','role':'production' if t<3 else 'demand','efficacy':10.-t,
           '_raw':np.eye(6)[t], '_projected':np.eye(6)[t]} for t in range(6)]
    for policy in ('Top','RawDiverse','ProjectedDiverse','Physical'):
        chosen=select(cuts,policy);assert len(chosen)==4 and chosen[0] is cuts[0]
        assert all(any(c is d for d in cuts) for c in chosen)
