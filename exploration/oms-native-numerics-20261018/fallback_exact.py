"""One retained certificate-acquisition fallback for every SoPlex looping error.

No altered MIP/point, no performance credit, no repeated parameter search.
"""
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from fetch import HERE,dump,sha
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'exploration/oms-root-attribution-20261015'))
from exact_lp import parse,verify


def main():
    choices=json.loads((HERE/'exact-pattern-choices.json').read_text());attempts={}
    binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    for choice in choices:
        primary=HERE/choice['result_path'];result=json.loads(primary.read_text())
        if result['outcome']!='unknown' or 'Abort solving due to looping' not in (primary.parent/'solver.log').read_text():continue
        target=primary.parent/'fallback-geometric';destination=target/'result.json'
        if not destination.exists():
            target.mkdir(exist_ok=True)
            shutil.copyfile(primary.parent/'lp.json.gz',target/'lp.json.gz')
            shutil.copyfile(primary.parent/'fixed.lp',target/'fixed.lp')
            settings='int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 10\nint:simplifier = 0\nint:scaler = 3\n'
            (target/'exact.set').write_text(settings)
            # A previous wrapper stopped after its native solve while hashing a Path.
            # Preserve and parse those completed outputs; do not repeat the solve.
            recovered=(target/'solver.log').exists() and (target/'solver.log').stat().st_size>0
            if recovered:
                assert 'SoPlex status' in (target/'solver.log').read_text()
                rc=None;elapsed=None
            else:
                started=time.perf_counter()
                with (target/'solver.log').open('w') as stream:
                    try:
                        p=subprocess.run([str(binary),'--loadset='+str(target/'exact.set'),'-X='+str(target/'primal.txt'),
                            '-Y='+str(target/'dual.txt'),str(target/'fixed.lp')],stdout=stream,stderr=subprocess.STDOUT,timeout=13.)
                        rc=p.returncode
                    except subprocess.TimeoutExpired:rc=None
                elapsed=time.perf_counter()-started
            followup=dict(pattern=result['pattern'],outcome='unknown',returncode=rc,solver_seconds=elapsed,
                recovered_native_outputs_without_resolve=recovered,
                primary_result=str(primary.relative_to(HERE)),solver_sha256=sha(binary.read_bytes()),
                setting='one fallback: simplifier off, geometric scaling; same exact LP')
            primal=parse(target/'primal.txt','Primal solution (name, value):','x')
            dual=parse(target/'dual.txt','Dual solution (name, value):','r')
            if primal is not None:
                with gzip.open(target/'lp.json.gz','rt') as stream:lp=json.load(stream)
                q=[primal.get(str(j),'0') for j in range(len(lp['cost']))]
                check=verify(lp,q,dual)
                dump(target/'certificate.json',check);dump(target/'primal.json',q);dump(target/'dual.json',dual)
                if check['primal_feasible']:
                    total=len(lp['continuous_indices'])+len(result['pattern'])
                    point=[None]*total
                    for j,z in result['pattern'].items():point[int(j)]=str(F(z))
                    for i,j in enumerate(lp['continuous_indices']):point[j]=q[i]
                    assert all(x is not None for x in point)
                    dump(target/'rational-point.json',point)
                    followup['outcome']='optimum_certified' if check['optimum_certified'] else 'exact_primal_only'
            dump(destination,followup)
            print(choice['instance'],choice['pattern_key'],followup['outcome'],flush=True)
        choice['fallback_result_path']=str(destination.relative_to(HERE))
        attempts[str(primary.relative_to(HERE))]=str(destination.relative_to(HERE))
    dump(HERE/'exact-pattern-choices.json',choices)
    dump(HERE/'exact-fallbacks.json',attempts)


if __name__=='__main__':main()
