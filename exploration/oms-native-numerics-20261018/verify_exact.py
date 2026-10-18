"""License-free exact source/point and conditional LP dual verification."""
from fractions import Fraction as F
import gzip
import json

from fetch import HERE,dump,sha
from native import read_mps


def main():
    choices=json.loads((HERE/'exact-pattern-choices.json').read_text());seen={};outputs=[]
    for choice in choices:
        path=HERE/choice.get('fallback_result_path',choice['result_path']);key=str(path)
        if key not in seen:
            result=json.loads(path.read_text());folder=path.parent
            record=dict(instance=choice['instance'],pattern_key=choice['pattern_key'],outcome=result['outcome'],
                        global_MILP_optimality_certified=False)
            model=read_mps(HERE/'sources'/(choice['instance']+'.mps.gz'))
            pattern={int(j):F(v) for j,v in result['pattern'].items()}
            assert set(pattern)=={j for j,v in enumerate(model['variables']) if v['integer']}
            assert all(z.denominator==1 for z in pattern.values())
            for j,z in pattern.items():
                var=model['variables'][j]
                assert var['lower'] is None or F(var['lower'])<=z
                assert var['upper'] is None or z<=F(var['upper'])
            continuous=[j for j,v in enumerate(model['variables']) if not v['integer']]
            idx={j:i for i,j in enumerate(continuous)}
            expected=[]
            for row in model['rows']:
                rhs=F(row['rhs'])-sum((F(c)*pattern[int(j)] for j,c in row['terms'].items() if int(j) in pattern),F(0))
                terms={str(idx[int(j)]):F(c) for j,c in row['terms'].items() if int(j) in idx}
                for sign in ([1,-1] if row['sense']=='=' else [1] if row['sense']=='<' else [-1]):
                    expected.append((({j:sign*c for j,c in terms.items()}),sign*rhs))
            for j in continuous:
                v=model['variables'][j]
                for endpoint,sign in ((v['lower'],-1),(v['upper'],1)):
                    if endpoint is not None:expected.append(({str(idx[j]):F(sign)},sign*F(endpoint)))
            with gzip.open(folder/'lp.json.gz','rt') as stream:lp=json.load(stream)
            assert len(lp['rows'])==len(expected)
            for row,(terms,rhs) in zip(lp['rows'],expected):
                assert {j:F(c) for j,c in row['terms'].items()}==terms and F(row['rhs'])==rhs
            assert list(map(F,lp['cost']))==[F(model['variables'][j]['cost']) for j in continuous]
            assert F(lp['offset'])==F(model['objective_offset'])+sum((F(model['variables'][j]['cost'])*z for j,z in pattern.items()),F(0))
            # SoPlex exposes an exact nonpositive dual ray on an infeasible all-<= LP.
            ray={};active=False
            for line in (folder/'dual.txt').read_text().splitlines() if (folder/'dual.txt').exists() else []:
                if 'Dual ray (name, value):' in line:active=True;continue
                parts=line.split()
                if active and len(parts)==2 and parts[0].startswith('r') and parts[0][1:].isdigit():
                    ray[int(parts[0][1:])]=F(parts[1])
            if ray:
                assert all(v<=0 for v in ray.values()) and all(0<=i<len(expected) for i in ray)
                annihilated=[F(0)]*len(continuous);contradiction=F(0)
                for i,multiplier in ray.items():
                    terms,rhs=expected[i];contradiction+=multiplier*rhs
                    for j,c in terms.items():annihilated[int(j)]+=multiplier*c
                assert not any(annihilated) and contradiction>0
                record.update(fixed_pattern_infeasibility_certified=True,farkas_contradiction_exact=str(contradiction),verification_outcome='infeasible_fixed_pattern')
            if (folder/'rational-point.json').exists():
                point=list(map(F,json.loads((folder/'rational-point.json').read_text())))
                assert len(point)==len(model['variables'])
                for v,x in zip(model['variables'],point):
                    assert v['lower'] is None or F(v['lower'])<=x
                    assert v['upper'] is None or x<=F(v['upper'])
                    assert not v['integer'] or x.denominator==1
                for row in model['rows']:
                    residual=sum((F(c)*point[int(j)] for j,c in row['terms'].items()),F(0))-F(row['rhs'])
                    assert residual==0 if row['sense']=='=' else residual<=0 if row['sense']=='<' else residual>=0
                cost=F(model['objective_offset'])+sum((F(v['cost'])*x for v,x in zip(model['variables'],point)),F(0))
                record.update(exact_original_primal_feasible=True,objective_exact=str(cost),verification_outcome='feasible_fixed_pattern')
                # Independent dual reconstruction in the all-<=, free-variable LP.
                dual=json.loads((folder/'dual.json').read_text())
                if dual is not None:
                    pi={int(j):F(v) for j,v in dual.items()};assert all(v<=0 for v in pi.values())
                    reduced=list(map(F,lp['cost']));bound=F(lp['offset'])
                    for i,row in enumerate(lp['rows']):
                        multiplier=pi.get(i,F(0));bound+=multiplier*F(row['rhs'])
                        for j,c in row['terms'].items():reduced[int(j)]-=multiplier*F(c)
                    assert not any(reduced)
                    assert bound<=cost
                    record['fixed_pattern_optimum_certified']=bound==cost
                    record['conditional_dual_exact']=str(bound)
            seen[key]=record
        outputs.append(dict(seen[key],policy=choice['policy']))
    dump(HERE/'verification-exact.json',dict(unique_patterns=len(seen),references=len(choices),
        exact_feasible_patterns=sum(r.get('exact_original_primal_feasible',False) for r in seen.values()),
        fixed_pattern_optima=sum(r.get('fixed_pattern_optimum_certified',False) for r in seen.values()),records=outputs))
    print('Exact patterns',len(seen),'feasible',sum(r.get('exact_original_primal_feasible',False) for r in seen.values()))


if __name__=='__main__':main()
