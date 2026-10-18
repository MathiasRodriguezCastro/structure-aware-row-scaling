"""Stage A: native matrix/DEC and numerical-risk screening, with no solves."""
from fractions import Fraction as F
import csv
import gzip
import json
import math
from pathlib import Path
import time

from factors import row_spec,select
from fetch import HERE,dump,sha
from native import read_mps,read_dec

BUDGETS=(1e-1,1e-3,1e-5,1e-7)


def csvwrite(path,rows):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'wt',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader();writer.writerows(rows)


def main():
    selection=json.loads((HERE/'selection.json').read_text())
    assert not (HERE/'stage-b-design.json').exists(),'stage A is already frozen'
    summaries=[];contracts=[];accepted=[]
    for item in selection['selected']:
        name=item['name'];started=time.perf_counter()
        try:
            model=read_mps(HERE/'sources'/(name+'.mps.gz'))
            dec=read_dec(HERE/'sources'/(name+'.dec'),model)
            model.update(source_sha256=sha((HERE/'sources'/(name+'.mps.gz')).read_bytes()),group=item['group'],
                         stratum=item['stratum'])
            folder=HERE/'models'/name;folder.mkdir(parents=True,exist_ok=True)
            with gzip.open(folder/'original.json.gz','wt') as stream:json.dump(model,stream,separators=(',',':'),allow_nan=False)
            dump(folder/'structure.json',dec)
            specs=[row_spec(r,model['variables']) for r in model['rows']]
            nonzero=[s for s in specs if s is not None]
            minimum=min(s['m'] for s in nonzero);maximum=max(s['M'] for s in nonzero)
            ratio=maximum/minimum;row_ratio=max(s['M']/s['m'] for s in nonzero)
            record=dict(instance=name,stratum=item['stratum'],group=item['group'],variables=len(model['variables']),
                integer_variables=sum(v['integer'] for v in model['variables']),source_rows=model['original_rows'],
                rows=len(model['rows']),ranged_rows=model['ranged_rows'],nonzeros=model['nonzeros'],
                coefficient_min=float(minimum),coefficient_max=float(maximum),coefficient_range=float(ratio),
                within_row_range=float(row_ratio),declared_blocks=dec['declared_blocks'],
                nontrivial_private_blocks=dec['nontrivial_private_blocks'],private_columns=dec['private_columns'],
                shared_columns=dec['shared_columns'],master_rows=dec['master_rows'],
                genuine_row_coupling_rows=dec['genuine_row_coupling_rows'],role_applicable=dec['full_role_applicable'])
            base=[select(s) for s in specs]
            selected=None;changed_any=False
            for budget in BUDGETS:
                rounded=[select(s,budget) for s in specs];raw=[select(s,budget,False) for s in specs]
                incompatible=sum(s['factor'] is None for s in rounded)
                changed=sum(a['factor'] is not None and b['factor'] is not None and a['factor']!=b['factor'] for a,b in zip(base,rounded))
                changed_any|=bool(changed)
                if not incompatible:selected=budget
                record[f'budget_{budget:g}_incompatible']=incompatible
                record[f'budget_{budget:g}_modified']=changed
                record[f'budget_{budget:g}_raw_incompatible']=sum(s['factor'] is None for s in raw)
                for i,(r,s,plain,constrained) in enumerate(zip(model['rows'],specs,base,rounded)):
                    contracts.append(dict(instance=name,row=i,source_row=r['source_name'],budget=budget,
                        role='coupling' if i in dec['coupling_row_indices'] else 'local' if dec['source_row_blocks'][r['source_name']] else 'master-other',
                        E_exact=str(s['E']) if s else '0',l2_factor=plain['factor'],factor=constrained['factor'],
                        low=constrained['low'],high=constrained['high'],reason=constrained['reason']))
            record['selected_budget']=selected
            risk=ratio>=10**6 or row_ratio>=10**4
            record['numerical_risk_criterion']=risk
            constant_ok=all(r['terms'] or (r['rhs']==0 if r['sense']=='=' else r['rhs']>=0 if r['sense']=='<' else r['rhs']<=0) for r in model['rows'])
            record['accepted']=risk and changed_any and selected is not None and all(x['factor'] is not None for x in base) and constant_ok
            record['reason']='accepted' if record['accepted'] else 'no_feasible_full_contract' if selected is None else 'risk_or_factor_change_absent'
            if record['accepted']:accepted.append(dict(instance=name,budget=selected,role_applicable=dec['full_role_applicable'],
                source_model_sha256=sha((folder/'original.json.gz').read_bytes())))
            record['screen_seconds']=time.perf_counter()-started
            summaries.append(record)
            print(name,'range',record['coefficient_range'],'coupling',record['genuine_row_coupling_rows'],
                'budget',selected,'accepted',record['accepted'],flush=True)
        except (ValueError,AssertionError) as error:
            summaries.append(dict(instance=name,accepted=False,reason=str(error),screen_seconds=time.perf_counter()-started))
            print(name,'adapter abstention',str(error),flush=True)
    csvwrite(HERE/'screen.csv',summaries);csvwrite(HERE/'contracts.csv.gz',contracts)
    dump(HERE/'stage-b-design.json',dict(selection_sha256=sha((HERE/'selection.json').read_bytes()),
        protocol_sha256=sha((HERE/'PROTOCOL.md').read_bytes()),selected=accepted,optimizer_calls_before_freeze=0,
        common=dict(Threads=4,Seed=239,Presolve=-1,ScaleFlag=-1,IntFeasTol=1e-9,MIPGap=.01,
            WorkLimit=1.,TimeLimit=20.,FeasibilityTol=1e-6),
        policies=['Base','Base-tight','Dyadic-L2','Dyadic-L2-tight','Dyadic-L2-NumericFocus3']))


if __name__=='__main__':main()
