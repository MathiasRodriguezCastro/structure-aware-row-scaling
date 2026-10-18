"""Compact, retrospectively selected diagnostic from preserved points; no solves."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np
import deliver

HERE=Path(__file__).resolve().parent
F=Fraction.from_float


def main():
    cases=[]
    for budget in ('1e-04','1e-06','1e-08'):
        scope=HERE/'pilot/models/neos-3421095-cinca'/budget
        arm=scope/'Centered-shared';out=HERE/'pilot/runs/neos-3421095-cinca'/budget/'Centered-shared/199'
        original=json.loads((scope/'original.json').read_text());meta=json.loads((arm/'selection.json').read_text())
        model=json.loads((arm/'model.json').read_text())
        with np.load(out/'point.npz',allow_pickle=False) as z:point=[F(float(x)) for x in z['x']]
        rounded=[Fraction(round(x)) if v['integer'] else x for x,v in zip(point,original['variables'])]
        candidates=[(deliver.audit.violation(original['rows'][i],rounded),i) for i in meta['all_gate_rows']]
        error,i=max(candidates);row=original['rows'][i];link=next(g for g in meta['links'] if g['row']==i)
        sparse={j:float(point[int(j)]) for j in row['terms']}
        sparse_rounded={j:round(v) if original['variables'][int(j)]['integer'] else v for j,v in sparse.items()}
        independently=sum((F(float(c))*F(float(sparse_rounded[j])) for j,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
        independently=max(Fraction(0),independently if row['sense']=='<' else -independently)
        assert independently==error
        y,w=(point[link[k]] for k in ('y','w'));support=min(abs(y),abs(w));alpha=meta['factors'][i]
        cases.append({'budget':budget,'seed':199,'policy':'Centered-shared','row_index':i,'row':row,
                      'integer_indices':[j for j in row['terms'] if original['variables'][int(j)]['integer']],
                      'raw_sparse_values':sparse,'rounded_sparse_values':sparse_rounded,
                      'rounded_violation_exact':str(error),'rounded_violation':float(error),
                      'maximum_activation_budget_ratio':float(error/F(float(row['budget']))),
                      'radius':link['radius'],'h':link['h'],'alpha':alpha,'contracted_M':link['M'],
                      'epsilon':meta['epsilon'],'gamma_SOS':meta['gamma'],'tau':1e-6,
                      'exported_link_budget_bound_exact':link['bound'],
                      'auxiliary_y':float(y),'complement_w':float(w),
                      'SOS_support_violation_exact':str(support),'SOS_hypothesis_met':support<=F(meta['gamma']),
                      'exported_link_residual':float(deliver.audit.violation(model['rows'][i],point)*F(alpha)),
                      'point_sha256':hashlib.sha256((out/'point.npz').read_bytes()).hexdigest()})
    assert cases[0]['maximum_activation_budget_ratio']<=1 and cases[1]['maximum_activation_budget_ratio']>1 and cases[2]['maximum_activation_budget_ratio']<=1
    result={'selection':'Retrospective diagnostic, fixed to cinca/Centered-shared/seed199; not an independent confirmation.',
            'causality':'Changing budget changes exported representation and search; this is not a complete internal-mechanism explanation.',
            'cases':cases,'new_optimizer_calls':0,'original_optimality_claim':False}
    (HERE/'NONMONOTONICITY_CASE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:c[k] for k in ('budget','row_index','rounded_violation','maximum_activation_budget_ratio','SOS_hypothesis_met')} for c in cases],indent=2))


if __name__=='__main__':main()
