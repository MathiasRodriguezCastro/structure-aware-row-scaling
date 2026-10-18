"""Frozen prospective design, sequential fresh-process calls and durable recovery."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import study as parent
import method
import deliver

POLICIES=('Coefficient-SOS','Tight-coefficient-SOS','Unconstrained-shared',
          'Centered-individual','Centered-shared','Minimum-shared','Indicator-budget','Tight-raw')
BUDGETS=(1e-4,1e-6,1e-8)
SEEDS=(197,199,211)
FILES=('PROTOCOL.md','THEORY.md','method.py','campaign.py','worker.py','deliver.py','test_method.py')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def changed(model,scope,budget):
    model=copy.deepcopy(model)
    for i in scope:model['rows'][i]['budget']=budget
    return model


def prepare():
    output=HERE/'pilot'
    if output.exists():raise RuntimeError('preserve existing design')
    output.mkdir()
    primary=json.loads((HERE.parent/'pilot/design.json').read_text())
    design={'version':1,'sources':{f:sha(HERE/f) for f in FILES},
            'parent_sources':{f:sha(HERE.parent/f) for f in ('study.py','activity.py','verify.py','mps_check.py')},
            'primary_design_sha256':sha(HERE.parent/'pilot/design.json'),
            'reference_objectives':primary['reference_objectives'],'models':[],
            'variants':[],'calls':[],'abstentions':[],'machine':platform.uname()._asdict(),
            'sequential_fresh_process':True,'timing_scope':'cycle from preserved JSON, excluding common FBBT and original generator'}
    for item in primary['models']:
        source=HERE.parent/'pilot/models'/item['name'];folder=output/'models'/item['name'];folder.mkdir(parents=True)
        original=json.loads((source/'original-model.json').read_text());base=json.loads((source/'contracted-model.json').read_text())
        model_record={'name':item['name'],'original_sha256':sha(source/'original-model.json'),
                      'base_sha256':sha(source/'contracted-model.json'),'gate_rows':item['gate_rows']}
        design['models'].append(model_record)
        for budget in BUDGETS:
            label=format(budget,'.0e');scope=folder/label;scope.mkdir()
            orig=changed(original,item['gate_rows'],budget);data=changed(base,item['gate_rows'],budget)
            dump(scope/'original.json',orig);dump(scope/'base.json',data)
            for policy in POLICIES:
                arm=scope/policy;arm.mkdir();started=time.perf_counter()
                model,meta=method.compile_model(data,policy,parent)
                if model is None:
                    abstention={'name':item['name'],'budget':budget,'policy':policy,**meta}
                    dump(arm/'abstention.json',abstention);design['abstentions'].append(abstention);continue
                static=deliver.check_static(data,model,meta)
                parent.write_lp(arm/'model.lp',model,meta);dump(arm/'model.json',model);dump(arm/'selection.json',meta)
                epsilon,gamma=meta['epsilon'],meta['gamma']
                parameters={'Threads':4,'TimeLimit':30.,'WorkLimit':5.,'MIPGap':.01,'FeasibilityTol':epsilon,
                            'IntFeasTol':gamma,'Presolve':-1,'PreSOS1BigM':0,'NumericFocus':0}
                variant={'name':item['name'],'budget':budget,'budget_label':label,'policy':policy,
                         'export_sha256':sha(arm/'model.lp'),'model_sha256':sha(arm/'model.json'),
                         'selection_sha256':sha(arm/'selection.json'),'original_sha256':sha(scope/'original.json'),
                         'base_sha256':sha(scope/'base.json'),'parameters':parameters,
                         'static':static,'selection_export_static_seconds':time.perf_counter()-started,
                         'groups':len(meta['groups']),'activity_rows':len(meta['links']),
                         'activity_contract_over_budget_rows':sum(method.Fraction(g['bound'])>method.F(float(data['rows'][g['row']]['budget'])) for g in meta['links'])}
                design['variants'].append(variant)
                for seed in SEEDS:design['calls'].append({**variant,'seed':seed})
        print(json.dumps({'prepared':item['name'],'calls':len(design['calls']),'abstentions':len(design['abstentions'])}),flush=True)
    random.Random(1710197).shuffle(design['calls']);dump(output/'design.json',design)
    print(json.dumps({'calls':len(design['calls']),'variants':len(design['variants']),'abstentions':len(design['abstentions'])}),flush=True)


def check_design(design):
    for file,digest in design['sources'].items():assert sha(HERE/file)==digest,file
    for file,digest in design['parent_sources'].items():assert sha(HERE.parent/file)==digest,file
    assert design['primary_design_sha256']==sha(HERE.parent/'pilot/design.json')


def solve():
    design=json.loads((HERE/'pilot/design.json').read_text());check_design(design)
    for index,call in enumerate(design['calls']):
        out=HERE/'pilot/runs'/call['name']/call['budget_label']/call['policy']/str(call['seed'])
        if (out/'completed.json').exists():continue
        if out.exists() and any(out.iterdir()):
            archive=HERE/'pilot/interrupted-attempts'/f'{time.time_ns()}'/call['name']/call['budget_label']/call['policy']/str(call['seed'])
            archive.parent.mkdir(parents=True,exist_ok=True);out.rename(archive)
        out.mkdir(parents=True,exist_ok=True);dump(out/'assignment.json',call)
        load_before=list(os.getloadavg());started=time.perf_counter()
        with (out/'process.log').open('w') as log:
            result=subprocess.run([sys.executable,str(HERE/'worker.py'),str(index),str(out)],stdout=log,stderr=subprocess.STDOUT)
        elapsed=time.perf_counter()-started
        record={'index':index,'returncode':result.returncode,'fresh_process_seconds':elapsed,
                'load_before':load_before,'load_after':list(os.getloadavg()),'assignment_sha256':sha(out/'assignment.json')}
        dump(out/'completed.json',record)
        observed=json.loads((out/'run.json').read_text()) if (out/'run.json').exists() else {}
        verified=json.loads((out/'verification.json').read_text()) if (out/'verification.json').exists() else {}
        print(json.dumps({'completed':index+1,'of':len(design['calls']),'name':call['name'],'budget':call['budget'],
                          'policy':call['policy'],'seed':call['seed'],'returncode':result.returncode,
                          'primal_pass':verified.get('primal_pass'),'quality_target_met':verified.get('quality_target_met'),
                          'work':observed.get('work'),'objective':observed.get('objective'),'cycle_seconds':elapsed}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','solve'));args=parser.parse_args()
    prepare() if args.action=='prepare' else solve()
