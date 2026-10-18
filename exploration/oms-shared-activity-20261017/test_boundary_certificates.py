"""Representation floors and incompatible common-radius certificates."""
from fractions import Fraction
import json
import math
from pathlib import Path

import activity as a

F=Fraction.from_float
g1={'row':0,'z':0,'M':1e-9,'delta':2e-6,'g':{'1':1e9}}
g2={'row':1,'z':0,'M':1e9,'delta':1e-6,'g':{'1':1e-9}}
one=a.select_shared([g1]);two=a.select_shared([g2]);together=a.select_shared([g1,g2])
assert one['compatible'] and two['compatible'] and not together['compatible']
assert one['upper_r']<two['lower_r']
assert together['lower_r']>together['upper_r']
assert together['reason']=='shared_radius_intersection_empty'

simple={'row':2,'z':0,'M':1.,'delta':1.,'g':{'1':1.}}
certificate=a.row_radius_interval(simple)
P=Fraction(certificate['P']);at_floor={**simple,'delta':float(P)}
assert F(at_floor['delta'])==P and not a.select_shared([at_floor])['compatible']
subnormal={**simple,'g':{'1':math.ulp(0.)}}
assert not a.select_shared([subnormal])['compatible']
wide_window={**simple,'g':{'1':1e-10,'2':1e10}}
assert not a.select_shared([wide_window])['compatible']
non_dyadic={**simple,'M':1.3,'g':{'1':.1,'2':-.3},'delta':1e-8}
choice=a.select_shared([non_dyadic]);assert choice['compatible']
for d in choice['decisions']:
    assert F(d['h'])*F(choice['radius'])==F(non_dyadic['M'])
    assert Fraction(d['bound'])<=F(non_dyadic['delta'])
extreme={**simple,'M':1e308,'delta':1e308,'g':{'1':1e308}}
converted={**extreme,'M':math.ldexp(extreme['M'],-1000),'delta':math.ldexp(extreme['delta'],-1000),
           'g':{'1':math.ldexp(1e308,-1000)}}
before=a.select_shared([extreme]);after=a.select_shared([converted])
assert before['compatible'] and after['compatible'] and before['r']==0 and after['r']==-16
# The former optimum remains valid after conversion, but new smaller radii
# become representable. This disproves an unqualified global selector invariance.
for g in (extreme,converted):
    h=a.exact(F(g['M']));assert h is not None
    assert a.factor([*g['g'].values(),-h],delta=F(g['delta']),reserve=F(h)*F(1e-5)) is not None
result={'individually_compatible_but_shared_incompatible':{'first':[one['lower_r'],one['upper_r']],
         'second':[two['lower_r'],two['upper_r']]},'precision_floor_rejected':True,
        'subnormal_factor_obstruction_rejected':True,'empty_coefficient_window_rejected':True,
        'non_dyadic_M_exact_links_checked':True,
        'finite_representation_counterexample_to_global_covariance':{'source_r':before['r'],'converted_r':after['r'],'unit_exponent':-1000},
        'optimizer_calls':0}
(Path(__file__).parent/'BOUNDARY_TESTS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
