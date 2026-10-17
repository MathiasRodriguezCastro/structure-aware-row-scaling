"""Independent exact checker for <= rational LPs whose variables are free."""
from fractions import Fraction


def verify(lp,primal,dual):
    q=[Fraction(x) for x in primal];c=list(map(Fraction,lp['cost']))
    assert len(q)==len(c)
    pi={int(i):Fraction(v) for i,v in dual.items()}
    assert all(0<=i<len(lp['rows']) for i in pi)
    reduced=c[:];lower=Fraction(lp['offset']);primal_ok=True;sign_ok=True
    for i,row in enumerate(lp['rows']):
        p=pi.get(i,Fraction(0));sign_ok &= p<=0
        activity=sum((Fraction(a)*q[int(j)] for j,a in row['terms'].items()),Fraction(0))
        primal_ok &= activity<=Fraction(row['rhs'])
        lower+=p*Fraction(row['rhs'])
        for j,a in row['terms'].items():reduced[int(j)]-=p*Fraction(a)
    cost=Fraction(lp['offset'])+sum((a*x for a,x in zip(c,q)),Fraction(0))
    dual_ok=sign_ok and all(x==0 for x in reduced)
    if primal_ok and dual_ok:assert cost>=lower
    return {'primal_feasible':primal_ok,'dual_feasible':dual_ok,
            'optimum_certified':primal_ok and dual_ok and cost==lower,
            'primal_value_exact':str(cost),'dual_value_exact':str(lower),
            'scope':'this fixed-pattern rational LP only'}


def verify_ray(lp,ray):
    base={int(i):Fraction(v) for i,v in ray.items()}
    assert all(0<=i<len(lp['rows']) for i in base)
    for orient in (1,-1):
        combined=[Fraction(0)]*len(lp['cost']);rhs=Fraction(0);sign_ok=True
        for i,row in enumerate(lp['rows']):
            p=orient*base.get(i,Fraction(0));sign_ok &= p<=0
            rhs+=p*Fraction(row['rhs'])
            for j,a in row['terms'].items():combined[int(j)]+=p*Fraction(a)
        if sign_ok and not any(combined) and rhs>0:
            return {'infeasibility_certified':True,'orientation':orient,
                    'separation_exact':str(rhs),'scope':'this fixed-pattern rational LP only'}
    return {'infeasibility_certified':False}
