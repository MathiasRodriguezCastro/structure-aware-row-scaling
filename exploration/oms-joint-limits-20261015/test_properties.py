from fractions import Fraction as Q
import joint_limits as j


def test_boxed_identity_obstruction():
    a=[[Q(1),Q(0)],[Q(0),Q(1)]]
    result=j.boxed(a,[Q(1),Q(1,16)],[Q(10**9),Q(1,8)])
    assert result['minimum']==8 and result['skeel']==1
    assert result['alpha']==[1,Q(1,8)]


def test_joint_criterion_farkas_and_relaxed_feasibility():
    a=[[Q(1),Q(-1)],[Q(0),Q(1)]];low=[Q(1)]*2;high=[Q(1),Q(128)]
    lp=j.joint_lp(a,low,high,Q(10),Q(1),[Q(2),Q(1,128)])
    cert=j.farkas(lp,{'row_norm_1':Q(129),'kappa_0':Q(1),'max_factor_0':Q(1),'forward_1':Q(128)})
    assert cert['combined_rhs']==-119
    relaxed=j.joint_lp(a,low,high,Q(129),Q(1),[Q(2),Q(1,128)])
    assert j.lp_point(relaxed,[Q(128),Q(1),Q(128)])


def test_skeel_invariance_under_exact_row_scaling():
    a=[[Q(1),Q(1)],[Q(1),Q(1)+Q(1,2**20)]]
    original=j.boxed(a,[Q(1,1000)]*2,[Q(1000)]*2)['skeel']
    scaled=[[x*Q(2**20) for x in a[0]],[x*Q(1,2**20) for x in a[1]]]
    other=j.boxed(scaled,[Q(1,2**40)]*2,[Q(2**40)]*2)['skeel']
    assert original==other==4194307


def test_analytical_storage_inverse_and_optimum():
    n=8;a=[[Q(int(i==k)-int(i==k+1)) for k in range(n)] for i in range(n)]
    inv=j.inverse(a)
    assert inv==[[Q(k<=i) for k in range(n)] for i in range(n)]
    alpha=[Q(1)]+[Q(1,2)]*(n-1)
    assert j.condition(a,inv,alpha)==2*n-1
    assert j.boxed(a,[Q(1,1000)]*n,[Q(1000)]*n)['minimum']==2*n-1
