"""Global cut proofs from original rows; independent of the cut constructor."""
from fractions import Fraction
import math

F=Fraction.from_float


def check(model,lp,z,multipliers,kind,cut,exported):
    binary={i:v for i,v in enumerate(model['variables']) if v['integer']}
    continuous=[i for i,v in enumerate(model['variables']) if not v['integer']]
    assert all(v['lower']==0 and v['upper']==1 for v in binary.values())
    assert {int(i) for i in z}==set(binary)
    index={i:j for j,i in enumerate(continuous)};pi={int(j):Fraction(v) for j,v in multipliers.items()}
    assert all(v<=0 for v in pi.values()) and all(0<=i<len(lp['rows']) for i in pi)
    g0=Fraction(0);g={};stationary=[Fraction(0)]*len(continuous);seen=set()
    for j,row in enumerate(lp['rows']):
        s=row['source'];p=pi.get(j,Fraction(0))
        if 'row' in s:
            original=model['rows'][s['row']];sign=s['sign'];assert sign in (1,-1)
            assert original['sense']=='=' or (original['sense']=='<' and sign==1) or (original['sense']=='>' and sign==-1)
            key=('row',s['row'],sign);rhs=sign*F(float(original['rhs']))
            terms={str(index[int(i)]):sign*F(float(a)) for i,a in original['terms'].items() if int(i) in index and a}
            for i,a in original['terms'].items():
                if int(i) in binary:
                    rhs-=sign*F(float(a))*Fraction(z[i]);g[i]=g.get(i,Fraction(0))-p*sign*F(float(a))
            g0+=p*sign*F(float(original['rhs']))
        else:
            i=s['bound'];endpoint=s['endpoint'];v=model['variables'][i];assert i in index and endpoint in ('lower','upper') and v[endpoint] is not None
            sign=-1 if endpoint=='lower' else 1;key=('bound',i,endpoint);rhs=sign*F(float(v[endpoint]));terms={str(index[i]):Fraction(sign)};g0+=p*rhs
        assert key not in seen;seen.add(key)
        assert Fraction(row['rhs'])==rhs and {i:Fraction(a) for i,a in row['terms'].items()}==terms
        for i,a in terms.items():stationary[int(i)]+=p*a
    expected_rows=sum(2 if r['sense']=='=' else 1 for r in model['rows'])+sum(v[e] is not None for i,v in enumerate(model['variables']) if i in index for e in ('lower','upper'))
    assert len(seen)==expected_rows
    costs=[F(float(model['variables'][i]['cost'])) for i in continuous]
    assert stationary==(costs if kind=='cost' else [Fraction(0)]*len(costs))
    g={i:a for i,a in g.items() if a};assert Fraction(cut['g_constant'])==g0 and {i:Fraction(a) for i,a in cut['g_terms'].items()}==g
    terms={i:Fraction(a) for i,a in cut['terms'].items()};rhs=Fraction(cut['rhs'])
    if cut['kind'].startswith('aggregate'):
        expected={str(i):costs[j] for j,i in enumerate(continuous) if costs[j]} if kind=='cost' else {}
        expected.update({i:-a for i,a in g.items()});factor=next(terms[i]/a for i,a in expected.items() if a)
        assert factor>0 and terms=={i:a*factor for i,a in expected.items() if a} and rhs==g0*factor
    else:
        support=list(cut['support']);fixed=cut['fixed_values'];assert set(support)==set(fixed) and all(fixed[i]==int(z[i]) for i in support)
        lower=g0+sum((a*Fraction(fixed[i]) if i in fixed else min(Fraction(0),a) for i,a in g.items()),Fraction(0))
        if kind=='ray':
            assert cut['kind']=='partial-conflict' and lower==Fraction(cut['partial_margin']) and lower>0
            assert terms=={i:Fraction(1 if fixed[i]==0 else -1) for i in support} and rhs==1-sum(fixed.values())
        else:
            floor=Fraction(cut['partial_floor']);global_lower=Fraction(0)
            for i,c in zip(continuous,costs):
                endpoint=model['variables'][i]['lower'] if c>0 else model['variables'][i]['upper'] if c<0 else 0
                assert endpoint is not None;global_lower+=c*F(float(endpoint))
            assert lower>=floor>=global_lower and global_lower==Fraction(cut['global_continuous_lower'])
            delta=floor-global_lower;expected={str(i):c for i,c in zip(continuous,costs) if c}
            expected.update({i:delta*(1 if fixed[i]==0 else -1) for i in support if delta})
            assert terms==expected and rhs==floor-delta*sum(fixed.values())
    result={'globally_valid_for_original_mip':True,'proof':'dual cone and original binary box, not finite pattern enumeration','kind':cut['kind']}
    if exported['exported']:
        alpha=Fraction(exported['alpha_exact']);assert alpha>0 and alpha.denominator & (alpha.denominator-1)==0
        assert set(exported['terms'])==set(terms);support=Fraction(0)
        for i,a in terms.items():
            value=F(float(exported['terms'][i]));assert F(1e-9)<=abs(value)<=F(1e9)
            err=alpha*a-value
            if err:
                v=model['variables'][int(i)];endpoint=v['upper'] if err>0 else v['lower'];assert endpoint is not None
                support+=err*F(float(endpoint))
        assert support==Fraction(exported['export_support_exact'])
        assert F(float(exported['rhs']))<=alpha*rhs-support==Fraction(exported['safe_rhs_limit_exact'])
        assert F(1e-6)/alpha<=Fraction(exported['unscaled_residual_budget'])
        result['outward_export_valid']=True
        bounds={}
        for name,gamma in (('gurobi',F(1e-5)),('highs',F(1e-6))):
            loss=alpha*rhs-F(float(exported['rhs']))+F(1e-6)
            for i,a in terms.items():
                error=alpha*a-F(float(exported['terms'][i]));v=model['variables'][int(i)]
                if error:
                    allowance=gamma if v['integer'] else F(float(v['bound_budget']));endpoint=v['lower'] if error>0 else v['upper'];assert endpoint is not None
                    endpoint=F(float(endpoint))+(-allowance if error>0 else allowance);loss-=error*endpoint
            bound=loss/alpha+gamma*sum((abs(a) for i,a in terms.items() if int(i) in binary),Fraction(0))
            bounds[name]={'conditional_rounded_violation_bound':float(bound),'exact':str(bound)}
            if cut['kind']=='partial-conflict':bounds[name]['excludes_matching_rounded_assignment_if_premises_hold']=bound<1
            elif cut['kind']=='partial-cost':bounds[name]['below_one_percent_of_floor']=bound<=abs(Fraction(cut['partial_floor']))/100
        result['nominal_transfer_bounds']=bounds
    return result
