#!/usr/bin/env python3
"""Compute-node gate: pinned files, byte-identical generator and exact-LP tool."""
import tempfile
from pathlib import Path
import subprocess
from runner import ROOT,HERE,load,sha,save,generate


def main():
    plan=load(HERE/'PILOT_PLAN.json');data=load(HERE/'MODEL_PREPARATION.json')['models']
    transferred=0
    for line in (HERE/'TRANSFER_CONTENTS.sha256').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha(ROOT/name)==expected,'Transfer hash mismatch: '+name
        transferred+=1
    for n,h in plan['dependencies'].items():assert sha(ROOT/n)==h,n
    chosen=[]
    for family in ['simple','sgtm','completo']:
        n=next(n for n,m in data.items() if m['role']=='pilot' and m['family']==family and m['horizon']==24)
        folder=HERE/'deployment-models'/n;folder.mkdir(parents=True,exist_ok=False)
        generate(n,folder,data[n]);chosen.append(n)
    binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    target=HERE/'deployment-exact-LP';target.mkdir(exist_ok=False)
    model=target/'tiny.lp';settings=target/'exact.set';solution=target/'solution.txt'
    model.write_text('Minimize\n obj: x0\nSubject To\n c: x0 >= 1\nBounds\n x0 >= 0\nEnd\n')
    settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 10\n')
    with (target/'solver.log').open('w') as log:
        r=subprocess.run([str(binary),'--loadset='+str(settings),'-X='+str(solution),str(model)],
            stdout=log,stderr=subprocess.STDOUT,timeout=30)
    assert r.returncode==0
    assert any(line.split()==['x0','1'] for line in solution.read_text().splitlines())
    save(HERE/'DEPLOYMENT_GATE.json',dict(status='passed',
        transferred_files_checked=transferred,
        frozen_dependencies_checked=len(plan['dependencies']),byte_identical_generated_models=chosen,
        exact_LP_tool_passed=True,technical_LP_calls=1,benchmark_MIP_calls=0))
    print('Deployment gate passed: byte-identical exports for all three classes; exact LP tool passed.')


if __name__=='__main__':main()
