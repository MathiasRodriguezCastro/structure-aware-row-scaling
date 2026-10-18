"""Independent original-data and conditional-transfer checks, without selector."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
spec=importlib.util.spec_from_file_location('original_audit',HERE.parent/'verify.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
F=Fraction.from_float


def check_static(base,model,meta):
    source=audit.scaled_source(base,set(),0)
    count=audit.check_static(base,model,meta,source)
    links={g['row']:g for g in meta['links']};protected=0;active=0
    for g in meta['links']:
        if meta['policy'] in ('Centered-individual','Centered-shared','Minimum-shared'):
            assert Fraction(g['bound'])<=F(float(base['rows'][g['row']]['budget']));protected+=1
    for block in meta['groups']:
        if meta['policy'] not in ('Centered-individual','Centered-shared','Minimum-shared','Unconstrained-shared'):continue
        q=[];bounds=[]
        for i in block['rows']:
            g=links[i];row=base['rows'][i];sign=1 if row['sense']=='<' else -1
            terms={j:sign*F(float(c)) for j,c in row['terms'].items() if int(j)!=g['z']}
            M=F(g['M']);q.append(M*M/sum((c*c for c in terms.values()),Fraction(0)))
            if meta['policy']!='Unconstrained-shared':
                b=audit.interval({j:float(c) for j,c in terms.items()},M,F(float(row['budget'])))
                assert b is not None;bounds.append(b)
        r=block['r'];assert F(float(block['radius']))==Fraction(2)**r
        low=max(b[0] for b in bounds) if bounds else -1000
        high=min(b[1] for b in bounds) if bounds else 1000
        assert low<=r<=high
        if bounds:assert (low,high)==(block['lower_r'],block['upper_r'])
        def score(k):return max(max(q)/Fraction(2)**(2*k),Fraction(2)**(2*k)/min(q)),k
        if meta['policy']=='Minimum-shared':assert r==low
        else:
            assert all(score(r)<=score(k) for k in (r-1,r+1) if low<=k<=high)
            if bounds:active+=score(r-1)<score(r) or score(r+1)<score(r)
        for d in block.get('decisions',[]):
            assert F(d['h'])==F(links[d['row']]['h'])
            assert F(d['alpha'])==F(meta['factors'][d['row']])
    return {'source_rows_checked':count,'protected_activity_rows':protected,'center_clipped_blocks':active}


def point(original,model,meta,values,reference):
    p=[F(float(x)) for x in values]
    assert len(p)==len(model['variables'])
    metrics,rounded=audit.point_metrics(original,p)
    failures=[];protected=0
    for g in meta['links']:
        z,y,w=(p[g[k]] for k in ('z','y','w'));i=g['row']
        conditions=(round(z) in (0,1),abs(w+z-1)<=F(1e-6),
                    min(abs(w),abs(y))<=F(meta['gamma']),
                    audit.violation(model['rows'][i],p)*F(meta['factors'][i])<=F(meta['epsilon']),
                    y<=F(g['radius'])+F(1e-6))
        if not all(conditions):failures.append({'row':i,'conditions':list(conditions)})
        else:
            assert audit.violation(original['rows'][i],rounded)<=Fraction(g['bound'])
            protected+=1
    r=metrics['rounded'];reference=F(float(reference))
    return {'original':metrics,'activity_hypothesis_failures':failures,
            'activity_rows_checked':len(meta['links']),'valid_conditional_transfers':protected,
            'exported_row_hypothesis_failures':sum(audit.violation(row,p)*F(float(alpha))>F(meta['epsilon']) for row,alpha in zip(model['rows'],meta['factors'])),
            'primal_pass':r['accepted'],'quality_target_met':r['accepted'] and Fraction(r['objective_exact'])<=reference+abs(reference)/100,
            'original_optimality_certified':False}
