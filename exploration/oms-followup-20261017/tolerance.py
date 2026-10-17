"""Prespecified paired IntFeasTol follow-up; old gamma arms remain archived."""
import argparse
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from common import HERE,ROOT,FRONT,OLD,INSTANCES,load,dump,sha,module,choose,exact_witness

OUT=HERE/'tolerance';GAMMA=2.**-28

def prepare():
    import activation_study as a
    assert not (OUT/'design.json').exists()
    OUT.mkdir(exist_ok=True)
    inputs={};models={}
    for instance in INSTANCES:
        folder=OUT/'models'/instance;folder.mkdir(parents=True)
        for filename in ['Base.lp','input.txt']:(folder/filename).write_bytes((FRONT/'models'/instance/filename).read_bytes())
        parsed,_=a.original_rows(folder/'Base.lp');_,lp,_=a.campaign.afb.read_lp(folder/'Base.lp')
        inputs[instance]={'base_sha256':sha(folder/'Base.lp'),'input_sha256':sha(folder/'input.txt')}
        for budget in [None,30,100]:
            key='L2' if budget is None else 'B'+str(budget)
            factors,info,_=choose(parsed,lp,budget,GAMMA)
            record={**info,'budget':budget,'model':None,'export_sha256':None}
            if not info['incompatible_count']:
                path=folder/(key+'.lp');a.export_scaled(folder/'Base.lp',path,factors)
                record.update(model=str(path.relative_to(ROOT)),export_sha256=sha(path))
            models[instance+'/'+key]=record
        print(instance,'compatible:',[k for k in ['L2','B30','B100'] if models[instance+'/'+k]['model']],flush=True)
    jobs=[{'instance':n,'presolve':-1,'seed':s,'policy':p,'budget':b,'key':'L2' if b is None else 'B'+str(b),
        'id':f'{n}-P-1-s{s}-{p}'+('' if b is None else str(b))}
        for n in INSTANCES for s in [59,71,89] for p,b in [('L2-NF3',None),('Budget-L2',30),('Budget-L2',100)]]
    random.Random(2026101701).shuffle(jobs)
    old=load(FRONT/'design.json')
    dump(OUT/'design.json',{'date':'2026-10-17','jobs':jobs,'inputs':inputs,'models':models,
        'parameters':{**old['parameters'],'IntFeasTol':GAMMA},'source_of_borrowed_1e9_arms':str(FRONT.relative_to(ROOT)),
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),HERE/'common.py',HERE/'PROTOCOL.md',FRONT/'study.py']},
        'borrowed_low_gamma_assignments':54,'new_high_gamma_assignments':54,
        'planned_abstentions':sum(bool(models[j['instance']+'/'+j['key']]['incompatible_count']) for j in jobs)})

def witnesses():
    d=load(OUT/'design.json');known={}
    for folder in [FRONT/'witnesses',OLD/'exact-witnesses',OLD/'exact-witness-reference']:
        for p in folder.rglob('independent-certificate.json'):
            c=load(p);known[c['original_model_sha256']]={'folder':str(p.parent.relative_to(ROOT)),'certificate':c,'borrowed':True,'lp_calls':0}
    index={}
    for key,rec in d['models'].items():
        if rec['model'] is None:continue
        if rec['export_sha256'] in known:index[key]=known[rec['export_sha256']]
        else:
            instance=key.split('/')[0]
            source=ROOT/load(OLD/'exact-witnesses'/instance/'Budget-L2/mapping.json')['saved_solution']
            try:index[key]=exact_witness(OUT/'witnesses'/key,ROOT/rec['model'],source,10)
            except Exception as ex:index[key]={'error':str(ex),'lp_calls':int((OUT/'witnesses'/key/'solver-provenance.json').exists())}
        dump(OUT/'witness-index.json',index)
    print('Witnesses:',len(index),'new LPs:',sum(r['lp_calls'] for r in index.values()),flush=True)

def worker(job_id,start):
    m=module(FRONT/'study.py','frozen_frontier_tolerance_worker')
    m.HERE=OUT
    m.choose=lambda parsed,lp,budget:choose(parsed,lp,budget,GAMMA)[:2]
    m.worker(job_id,start)

def run():
    d=load(OUT/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    assert not (OUT/'parent-timing.json').exists()
    records=[]
    for i,j in enumerate(d['jobs']):
        abstain=bool(d['models'][j['instance']+'/'+j['key']]['incompatible_count'])
        start=time.perf_counter();rc=0
        if not abstain:
            with (OUT/(j['id']+'-execution.log')).open('w') as log:
                p=subprocess.run([sys.executable,str(Path(__file__)),'worker',j['id']],cwd=ROOT,
                    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=240)
            rc=p.returncode
        records.append({'job':j,'abstained':abstain,'returncode':rc,'total_fresh_process_seconds':time.perf_counter()-start})
        dump(OUT/'parent-timing.json',records)
        print(i+1,'/54',j['id'],'abstain' if abstain else 'seconds '+str(round(records[-1]['total_fresh_process_seconds'],3)),flush=True)
        assert rc==0,'Failed attempt retained; no automatic retry'

if __name__=='__main__':
    start=time.perf_counter();p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','witnesses','run','worker']);p.add_argument('job',nargs='?');args=p.parse_args()
    if args.stage=='worker':worker(args.job,start)
    else:globals()[args.stage]()
