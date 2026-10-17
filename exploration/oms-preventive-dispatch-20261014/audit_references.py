#!/usr/bin/env python3
"""Three post-experiment rational reference LPs, never fed back to policies."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE/'helpers'))
from build_lp import build,write
from rational_lp import verify
SOPLEX=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'


def dump(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def parse(path,header,prefix):
    values={};active=found=False
    for line in path.read_text().splitlines():
        if header in line:active=found=True;continue
        if active and (line.startswith('All other') or 'Reduced costs' in line):break
        t=line.split()
        if active and len(t)==2 and t[0].startswith(prefix) and t[0][len(prefix):].isdigit():values[str(int(t[0][len(prefix):]))]=str(Fraction(t[1]))
    return values if found else None


def main():
    results=[]
    for path in sorted((HERE/'inputs').glob('*/model.json')):
        model=json.loads(path.read_text());folder=HERE/'exact-references'/model['name'];folder.mkdir(parents=True,exist_ok=True)
        assert not (folder/'result.json').exists(),'do not overwrite exact reference attempts'
        for r in model['rows']:r['budget']=0.
        for v in model['variables']:v['bound_budget']=0.
        lp=build(model,{},'cost');dump(folder/'model.json',lp);write(folder/'model.lp',lp)
        settings=folder/'exact.set';settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 2\n')
        command=[str(SOPLEX),'--loadset='+str(settings),'-X='+str(folder/'primal.txt'),'-Y='+str(folder/'dual.txt'),str(folder/'model.lp')]
        tick=time.perf_counter()
        with (folder/'solver.log').open('w') as stream:
            try:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=4);code=r.returncode
            except subprocess.TimeoutExpired:code=None
        result={'model':model['name'],'seconds':time.perf_counter()-tick,'returncode':code,
                'purpose':'post-experiment exact reference; not used to initialize or select cuts',
                'soplex_sha256':hashlib.sha256(SOPLEX.read_bytes()).hexdigest()}
        p=parse(folder/'primal.txt','Primal solution (name, value):','x') if (folder/'primal.txt').exists() else None
        d=parse(folder/'dual.txt','Dual solution (name, value):','r') if (folder/'dual.txt').exists() else None
        if p is not None and d is not None:
            q=[p.get(str(i),'0') for i in range(len(lp['cost']))];dump(folder/'primal.json',q);dump(folder/'dual.json',d)
            certificate=verify(lp,q,d);dump(folder/'certificate.json',certificate);result.update(certificate)
        dump(folder/'result.json',result);results.append(result);print(model['name'],result.get('optimum_certified'),result.get('primal_value_exact'),flush=True)
    dump(HERE/'exact-reference-summary.json',results)


if __name__=='__main__':main()
