"""Exact infeasibility proof for one fixed integer pattern, never the full MIP."""
from fractions import Fraction

F=Fraction.from_float


def verify(model,delivered,ray):
    y=[F(float(v)) for v in delivered]
    fixed={i:y[i] for i,v in enumerate(model['variables']) if v['integer']}
    assert all(v.denominator==1 for v in fixed.values())
    base={int(i):Fraction(v) for i,v in ray.items()}
    assert all(0<=i<len(model['rows']) for i in base)
    for orientation in (1,-1):
        lhs=Fraction(0);effect=Fraction(0);combined={i:Fraction(0) for i,v in enumerate(model['variables']) if not v['integer']}
        valid=True;numeric_ok=True
        for j,row in enumerate(model['rows']):
            p=orientation*base.get(j,Fraction(0))
            if row['sense']=='<' and p>0 or row['sense']=='>' and p<0:valid=False;break
            rhs=F(float(row['rhs']))-sum((F(float(c))*fixed[int(i)] for i,c in row['terms'].items() if int(i) in fixed),Fraction(0))
            lhs+=p*rhs;effect+=abs(p)*F(float(row['budget']))
            for i,c in row['terms'].items():
                if int(i) in combined:combined[int(i)]+=p*F(float(c))
            signed=sum((F(float(c))*y[int(i)] for i,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
            violation=abs(signed) if row['sense']=='=' else max(Fraction(0),signed if row['sense']=='<' else -signed)
            if violation>F(float(row['budget'])):numeric_ok=False
        if not valid:continue
        support=Fraction(0)
        for i,v in enumerate(model['variables']):
            lo=F(float(v['lower'])) if v['lower'] is not None else None
            hi=F(float(v['upper'])) if v['upper'] is not None else None
            allowance=Fraction(0) if v['integer'] else F(float(v['bound_budget']))
            if lo is not None and y[i]<lo-allowance or hi is not None and y[i]>hi+allowance:numeric_ok=False
            if v['integer']:continue
            c=combined[i];endpoint=hi if c>0 else lo if c<0 else Fraction(0)
            if c and endpoint is None:valid=False;break
            support+=c*endpoint;effect+=abs(c)*allowance
        if valid and lhs>support:
            gap=lhs-support
            if numeric_ok:assert gap<=effect
            return {'fixed_pattern_infeasible_certified':True,'orientation':orientation,
                    'separation_margin_exact':str(gap),'weighted_budget_allowance_exact':str(effect),
                    'numeric_point_meets_budgets':numeric_ok,'budget_compatibility_verified':numeric_ok and gap<=effect,
                    'global_mip_infeasibility_certified':False,'scope':'the delivered integer assignment only'}
    return {'fixed_pattern_infeasible_certified':False,'global_mip_infeasibility_certified':False}
