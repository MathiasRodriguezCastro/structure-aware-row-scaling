#!/usr/bin/env python3
"""Find exact two-row infeasibility certificates without any optimization calls."""
from collections import Counter
from fractions import Fraction as Q
from runner import HERE,ROOT,load,save,sha,library


def main():
    checker=library(ROOT/'exploration/orf-confirmatory-20261018/check.py','structural_model_reader')
    models=load(HERE/'MODEL_PREPARATION.json')['models'];certificates=[]
    for name,meta in sorted(models.items()):
        path=HERE/'models'/name/'Base.lp';model=checker.canonical(path)
        assert sha(path)==meta['base_sha256']
        rows,bounds=model[:2]
        # The first-period storage equation and an activation row suffice when
        # a horizon-dependent M incorrectly forces storage above reachable water.
        for activation in ['a1_restriccion_varphi1_1(1)','a1_restriccion_varphi1_2(1)']:
            dynamic='a1_v1h_din(1)'
            if activation not in rows or dynamic not in rows:continue
            a,b=rows[activation],rows[dynamic]
            assert a['sense']=='<=' and b['sense']=='='
            terms={j:a['terms'].get(j,Q(0))+b['terms'].get(j,Q(0))
                for j in a['terms'].keys()|b['terms'].keys()}
            terms={j:v for j,v in terms.items() if v}
            minimum=Q(0);multipliers=[];available=True
            for j,coefficient in sorted(terms.items()):
                lo,hi=bounds[j];endpoint=lo if coefficient>0 else hi
                if endpoint is None:available=False;break
                minimum+=coefficient*endpoint
                multipliers.append(dict(variable=j,bound='lower' if coefficient>0 else 'upper',
                    positive_multiplier=str(abs(coefficient)),value=str(endpoint)))
            rhs=a['rhs']+b['rhs'];contradiction=rhs-minimum
            if available and contradiction<0:
                certificates.append(dict(instance=name,family=meta['family'],role=meta['role'],horizon=meta['horizon'],
                    base_sha256=sha(path),row_multipliers={activation:'1',dynamic:'1'},
                    bound_multipliers=multipliers,contradiction_rhs_exact=str(contradiction),
                    contradiction_gap_float=float(-contradiction),integrality_not_required=True))
        print('Audited structural feasibility:',name,flush=True)
    instances=sorted({r['instance'] for r in certificates})
    report=dict(status='completed_exact_certificates',models_checked=len(models),optimizer_calls=0,
        certified_infeasible_models=len(instances),certified_infeasible_instances=instances,
        certified_by_role=dict(Counter(models[n]['role'] for n in instances)),
        certificates=certificates,
        other_models_status='Not classified by this sufficient two-row test; absence of a certificate does not prove feasibility.',
        selection_or_model_data_changed=False,
        scope='Exact Farkas combinations of original binary64 rows and bounds; infeasibility already holds for the LP relaxation.')
    save(HERE/'STRUCTURAL_FEASIBILITY_AUDIT.json',report)
    print('Certified infeasible models:',len(instances),'of',len(models),'with zero optimizer calls.')


if __name__=='__main__':main()
