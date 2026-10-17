"""Exact projected dual cuts and binary partial-assignment guards."""
from fractions import Fraction
import hashlib
import json
import math

F=Fraction.from_float


def signature(cut):
    values=[Fraction(x) for x in cut['terms'].values()]+[Fraction(cut['rhs'])]
    den=math.lcm(*(x.denominator for x in values));integers=[int(x*den) for x in values]
    div=math.gcd(*(abs(x) for x in integers));assert div
    primitive={'terms':{i:str(int(Fraction(a)*den)//div) for i,a in sorted(cut['terms'].items(),key=lambda x:int(x[0]))},'rhs':str(int(Fraction(cut['rhs'])*den)//div)}
    return hashlib.sha256(json.dumps(primitive,sort_keys=True).encode()).hexdigest(),primitive


def project(model,lp,multipliers,kind,z):
    pi={int(i):Fraction(x) for i,x in multipliers.items()};assert all(v<=0 for v in pi.values())
    continuous=[i for i,v in enumerate(model['variables']) if not v['integer']]
    assert continuous==lp['continuous_original_indices'];stationary=[Fraction(0)]*len(continuous)
    const=Fraction(0);g={}
    for j,row in enumerate(lp['rows']):
        value=pi.get(j,Fraction(0));assert row['source'].keys() & {'row','bound'}
        for i,a in row['terms'].items():stationary[int(i)]+=value*Fraction(a)
        source=row['source']
        if 'row' in source:
            original=model['rows'][source['row']];sign=source['sign'];const+=value*sign*F(float(original['rhs']))
            for i,a in original['terms'].items():
                if model['variables'][int(i)]['integer']:g[i]=g.get(i,Fraction(0))-value*sign*F(float(a))
        else:const+=value*Fraction(row['rhs'])
    expected=[F(float(model['variables'][i]['cost'])) if kind=='cost' else Fraction(0) for i in continuous]
    assert stationary==expected
    g={i:a for i,a in g.items() if a};at_z=const+sum((a*Fraction(z[i]) for i,a in g.items()),Fraction(0))
    terms={str(i):str(F(float(model['variables'][i]['cost']))) for i in continuous if model['variables'][i]['cost']} if kind=='cost' else {}
    for i,a in g.items():terms[i]=str(-a)
    aggregate={'kind':'aggregate-'+kind,'terms':terms,'rhs':str(const),'g_constant':str(const),'g_terms':{i:str(a) for i,a in g.items()},'value_at_pattern':str(at_z)}
    if kind=='ray':
        assert at_z>0
        _,primitive=signature(aggregate);aggregate.update(terms=primitive['terms'],rhs=primitive['rhs'])
    binary={i for i,v in enumerate(model['variables']) if v['integer']}
    assert all(model['variables'][i]['lower']==0 and model['variables'][i]['upper']==1 for i in binary)
    assert all(Fraction(z[str(i)]) in (0,1) for i in binary)
    support={i for i,a in g.items() if a*Fraction(z[i])>min(Fraction(0),a)}
    if kind=='ray':
        margin=at_z
        for i in sorted(support,key=lambda i:(g[i]*Fraction(z[i])-min(Fraction(0),g[i]),int(i))):
            loss=g[i]*Fraction(z[i])-min(Fraction(0),g[i])
            if margin-loss>0:support.remove(i);margin-=loss
        assert margin>0
        guard={'kind':'partial-conflict','terms':{i:str(1 if Fraction(z[i])==0 else -1) for i in sorted(support,key=int)},
               'rhs':str(1-sum(int(z[i]) for i in support)),'partial_margin':str(margin)}
    else:
        lower=Fraction(0)
        for i in continuous:
            v=model['variables'][i];c=F(float(v['cost']));endpoint=v['lower'] if c>0 else v['upper'] if c<0 else 0
            assert endpoint is not None;lower+=c*F(float(endpoint))
        assert at_z>=lower;delta=at_z-lower
        guard_terms={str(i):str(F(float(model['variables'][i]['cost']))) for i in continuous if model['variables'][i]['cost']}
        for i in sorted(support,key=int):guard_terms[i]=str(delta*(1 if Fraction(z[i])==0 else -1))
        guard={'kind':'partial-cost','terms':guard_terms,'rhs':str(at_z-delta*sum(int(z[i]) for i in support)),
               'partial_floor':str(at_z),'global_continuous_lower':str(lower)}
    guard.update(support=sorted(support,key=int),fixed_values={i:int(z[i]) for i in sorted(support,key=int)},
                 g_constant=str(const),g_terms={i:str(a) for i,a in g.items()})
    for cut in (aggregate,guard):
        cut['terms']={i:a for i,a in cut['terms'].items() if Fraction(a)}
        cut['signature']=signature(cut)[0]
    return aggregate,guard


def export(model,cut):
    terms={i:Fraction(x) for i,x in cut['terms'].items()};rhs=Fraction(cut['rhs']);magnitudes=[abs(x) for x in terms.values() if x]
    if not magnitudes:return {'exported':False,'reason':'constant_cut_requires_separate_global_status'}
    budget=Fraction(1,4) if cut['kind'] in ('partial-conflict','aggregate-ray') else Fraction(1)
    lower=max(F(1e-9)/min(magnitudes),F(1e-6)/budget);upper=F(1e9)/max(magnitudes)
    if lower>upper:return {'exported':False,'reason':'incompatible_coefficient_and_residual_interval'}
    alpha=Fraction(1);ideal=1/max(magnitudes)
    while alpha>ideal:alpha/=2
    while 2*alpha<=ideal:alpha*=2
    while alpha<lower:alpha*=2
    while alpha>upper:alpha/=2
    if alpha<lower:return {'exported':False,'reason':'no_dyadic_factor_in_interval'}
    hat={i:float(alpha*a) for i,a in terms.items()}
    if any(not math.isfinite(x) or not F(1e-9)<=abs(F(x))<=F(1e9) for x in hat.values()):return {'exported':False,'reason':'rounded_coefficient_outside_window'}
    support=Fraction(0)
    for i,a in terms.items():
        error=alpha*a-F(hat[i])
        if error:
            v=model['variables'][int(i)];endpoint=v['upper'] if error>0 else v['lower']
            if endpoint is None:return {'exported':False,'reason':'unbounded_required_export_endpoint','variable':i}
            support+=error*F(float(endpoint))
    limit=alpha*rhs-support;hat_rhs=float(limit)
    if F(hat_rhs)>limit:hat_rhs=math.nextafter(hat_rhs,-math.inf)
    assert F(hat_rhs)<=limit
    rounding={i:str(alpha*a-F(hat[i])) for i,a in terms.items() if alpha*a!=F(hat[i])}
    return {'exported':True,'alpha_exact':str(alpha),'terms':hat,'rhs':hat_rhs,'sense':'>',
            'export_support_exact':str(support),'coefficient_errors':rounding,
            'safe_rhs_limit_exact':str(limit),'source_signature':cut['signature'],'unscaled_residual_budget':str(budget)}
