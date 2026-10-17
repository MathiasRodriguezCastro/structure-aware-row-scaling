#!/usr/bin/env python3
"""Separate prospective crossover, using frozen functions from the main study."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import time

import numpy as np

import study as fixed
from controller import accept,best,cost,model_digest,screen_bound
from repair import repair,exact_check,delivery_check,dump,sha

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARMS={'Cold-Base-IF1':(None,'Base'),'Cold-L2-IF1':(None,'Dyadic-L2'),
      'Cold-Budget-IF1':(None,'Budget-dyadic-L2'),
      'Warm-L2-to-L2':('Dyadic-L2','Dyadic-L2'),
      'Warm-L2-to-Budget':('Dyadic-L2','Budget-dyadic-L2'),
      'Warm-Budget-to-L2':('Budget-dyadic-L2','Dyadic-L2'),
      'Warm-Budget-to-Budget':('Budget-dyadic-L2','Budget-dyadic-L2')}


def prepare():
    began=time.perf_counter();out=HERE/'ablation'
    assert not (out/'design.json').exists()
    folder=out/'model';folder.mkdir(parents=True)
    main=json.loads((HERE/'confirmation/design.json').read_text())
    item=next(x for x in main['models'] if x['name']=='control30-3-2-3')
    for name in ('original-model.json','factors.json','Base.lp','Dyadic-L2.lp','Budget-dyadic-L2.lp'):
        shutil.copy2(HERE/'confirmation/models/control30-3-2-3'/name,folder/name)
    model=json.loads((folder/'original-model.json').read_text())
    q=json.loads((HERE/'confirmation/runs/control30-3-2-3/Cold-IF1-s31/final-exact-audit/rational-point.json').read_text())
    assert exact_check(model,q)['exact_feasible']
    witness={'model_digest':model_digest(model),'point':q,'label':'control-main-study-seed31-exact-witness'}
    dump(folder/'prior-witness.json',witness)
    queue=[{'seed':s,'arm':a} for s in (59,71) for a in ARMS]
    rng=np.random.default_rng(20261017);queue=[queue[i] for i in rng.permutation(len(queue))]
    design={'assigned_treatments':14,'queue':queue,'arms':ARMS,'model':item,
            'prior_witness_sha256':sha(folder/'prior-witness.json'),
            'stage':'post-observation mechanism study, not generalization confirmation',
            'shared_preparation_seconds':time.perf_counter()-began,
            'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),HERE/'ABLATION_PROTOCOL.md',HERE/'study.py',HERE/'controller.py',fixed.PREVIOUS/'repair.py',fixed.PILOT/'generalization_study.py',ROOT/'scripts/research/budget_scaling.py')}}
    dump(out/'design.json',design);shutil.copy2(Path(__file__),out/'source-snapshot.py')
    print('Frozen 14 crossover assignments before their MILP calls',flush=True)


def solve():
    import gurobipy as gp
    out=HERE/'ablation';design=json.loads((out/'design.json').read_text())
    for path,digest in design['source_hashes'].items():assert sha(ROOT/path)==digest,path
    assert sha(out/'model/original-model.json')==design['model']['model_sha256']
    assert sha(out/'model/prior-witness.json')==design['prior_witness_sha256']
    model=json.loads((out/'model/original-model.json').read_text())
    factors=json.loads((out/'model/factors.json').read_text());prior=json.loads((out/'model/prior-witness.json').read_text())
    env=gp.Env(params={'OutputFlag':0})
    for task in design['queue']:
        folder=out/'runs'/f"{task['arm']}-s{task['seed']}"
        if (folder/'run.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True);began=time.perf_counter();deadline=began+20.
        record={**task,'phases':[],'repairs':[],'candidate_labels':[],'new_exact_witnesses':[],'optimality_status':'unverified'}
        candidates=[]
        def consider(point,label):
            if point is None:return
            converted=accept(model,point)
            if converted is not None:
                candidates.append((label,converted));fixed.save_point(folder/(label+'.npz'),converted);return
            for mode,cap in (('floating',.5),('exact',1.)):
                remaining=deadline-time.perf_counter()-.25
                if remaining<=0:break
                rf=folder/(label+'-repair-'+mode);result,converted=repair(model,point,rf,mode,min(cap,remaining))
                record['repairs'].append({'folder':rf.name,'source_label':label,**result})
                if result['exact_feasible']:record['new_exact_witnesses'].append(rf.name+'/rational-point.json')
                if converted is not None:
                    candidates.append((rf.name,converted));fixed.save_point(folder/(rf.name+'.npz'),converted);break
        try:
            initial,final=design['arms'][task['arm']]
            specs=[(initial,1.,'ordinary'),(final,14.,'IF1')] if initial else [(final,15.,'IF1')]
            for j,(representation,cap,robust) in enumerate(specs):
                remaining=deadline-time.perf_counter()-1.5
                if remaining<=.01:break
                label,start=best(model,candidates);before=time.perf_counter()
                result,point=fixed.phase(model,factors[representation],representation,design['model'],folder/f'phase-{j}',env,
                                          task['seed'],min(cap,remaining),robust,-1,start if initial and j==1 else None)
                result['start_candidate_label']=label if result['start_supplied'] else None
                verify=time.perf_counter();consider(point,f'phase-{j}-checked');result['check_and_repair_seconds']=time.perf_counter()-verify
                verify=time.perf_counter();result['prior_witness_screen']=screen_bound(model,result['bound'],prior);result['bound_screen_seconds']=time.perf_counter()-verify
                result['total_phase_seconds']=time.perf_counter()-before
                record['phases'].append(result);dump(folder/f'phase-{j}/phase.json',result)
            label,point=best(model,candidates)
            if point is not None:
                before=time.perf_counter();q=[Fraction.from_float(float(x)) for x in point];check=exact_check(model,q)
                dump(folder/'best-pre-audit-exact-check.json',check)
                if check['exact_feasible']:
                    dump(folder/'best-pre-audit-exact-point.json',[str(x) for x in q]);record['new_exact_witnesses'].append('best-pre-audit-exact-point.json')
                elif deadline-time.perf_counter()>.25:
                    result,converted=repair(model,point,folder/'final-exact-audit','exact',min(1.,deadline-time.perf_counter()-.25))
                    record['final_exact_audit']=result;record['final_audit_source_label']=label
                    if result['exact_feasible']:record['new_exact_witnesses'].append('final-exact-audit/rational-point.json')
                    if converted is not None:
                        candidates.append(('final-exact-audit',converted));fixed.save_point(folder/'final-exact-audit.npz',converted)
                record['exact_audit_seconds']=time.perf_counter()-before
        except Exception as error:record.update(execution_error_type=type(error).__name__,execution_error=str(error))
        label,point=best(model,candidates)
        record.update(candidate_labels=[x for x,p in candidates],selected_candidate=label,delivered=point is not None,
                      online_bound_contradictions=sum(p['prior_witness_screen']['bound_contradicted'] for p in record['phases']))
        if point is not None:
            record.update(delivered_objective=float(cost(model,point)),delivered_objective_exact=str(cost(model,point)))
            fixed.save_point(folder/'delivered-point.npz',point)
        record.update(total_seconds=time.perf_counter()-began,outcome='verified_delivery' if point is not None else 'no_verified_delivery')
        dump(folder/'run.json',record)
        print(task['seed'],task['arm'],'cost',record.get('delivered_objective'),'seconds',round(record['total_seconds'],3),'vetoes',record['online_bound_contradictions'],flush=True)
    env.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','solve'));globals()[p.parse_args().stage]()
