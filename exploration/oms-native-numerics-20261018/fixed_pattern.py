"""Post-hoc exact fixed-integer LP validation, not a new MIP method or global bound."""
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

from fetch import HERE,dump,sha
from native import read_mps

ROOT=HERE.parents[1]
HELPER=ROOT/'exploration/oms-root-attribution-20261015'
sys.path.insert(0,str(HELPER))
from exact_lp import acquire


def convert(model):
    q=lambda v:None if v is None else str(F(v))
    return dict(constant=q(model['objective_offset']),sense=1,
        variables=[dict(name=v['name'],type='I' if v['integer'] else 'C',lb=q(v['lower']),ub=q(v['upper']),obj=q(v['cost']))
            for v in model['variables']],
        rows=[dict(name=r['name'],sense=r['sense'],rhs=q(r['rhs']),
            terms=[[int(j),q(c)] for j,c in r['terms'].items()]) for r in model['rows']])


def main():
    binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    assert binary.exists()
    choices=[]
    for name in ('neos-619167','neos-3762025-ognon'):
        model=read_mps(HERE/'sources'/(name+'.mps.gz'));data=convert(model)
        folder=HERE/'exact-patterns'/name;folder.mkdir(parents=True,exist_ok=True)
        with gzip.open(folder/'source.json.gz','wt') as stream:json.dump(data,stream)
        for stage,policy in [('b','Base'),('b','Base-tight'),('b','Dyadic-L2'),('b','Dyadic-L2-tight'),('b','Dyadic-L2-NumericFocus3'),('c','Budget-L2')]:
            run_folder=HERE/f'stage-{stage}'/name/policy
            point=json.load(gzip.open(run_folder/'point.json.gz','rt'))
            pattern={str(j):str(round(F(value))) for j,value in enumerate(point) if model['variables'][j]['integer']}
            key=sha(json.dumps(pattern,sort_keys=True).encode())[:20]
            target=folder/key
            if not (target/'result.json').exists():
                result=acquire(data,pattern,target,binary,limit=10.)
                print(name,key,policy,result['outcome'],result.get('objective_exact'),flush=True)
            choices.append(dict(instance=name,stage=stage,policy=policy,pattern_key=key,
                source_point_sha256=sha((run_folder/'point.json.gz').read_bytes()),
                result_path=str((target/'result.json').relative_to(HERE)),
                scope='conditional fixed-pattern LP only; no global MILP optimality claim; repair not credited to original solver run'))
    dump(HERE/'exact-pattern-choices.json',choices)


if __name__=='__main__':main()
