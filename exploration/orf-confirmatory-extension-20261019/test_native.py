#!/usr/bin/env python3
"""Two technical MIPs verify import, callback vectors and numerical controls."""
import json
from pathlib import Path
import tempfile
import time
from runner import HERE,ROOT,library,native,save,witness_feasible


def main():
    follow=library(ROOT/'exploration/orf-v15-verified-20261019/study.py','technical_frozen_helpers')
    a,_=follow.old.modules();results=[]
    with tempfile.TemporaryDirectory(prefix='orf-native-test-') as tmp:
        root=Path(tmp);path=root/'tiny.lp'
        path.write_text('Minimize\n obj:\n +1 x\n +2 z\ns.t.\n cover:\n +1 x\n +1 z\n >= 1\nBounds\n 0 <= z <= 2\nBinary\n x\nEnd\n')
        _,lp,matrix=a.campaign.afb.read_lp(path);parsed,_=follow.checker.parse(path)
        for solver,policy in [('gurobi','L2-NF3'),('cplex','L2-NumEmphasis')]:
            folder=root/solver;folder.mkdir()
            job=dict(solver=solver,policy=policy,seed=401,time_limit=2.)
            outcome,points,events,parameters,imported,errors=native(path,folder,job,time.perf_counter(),lp,parsed,follow,matrix)
            assert not errors and outcome['completed'] and outcome['objective']==1.
            assert len(points)==len(events)>0 and events[-1]['kind']=='final'
            from fractions import Fraction as Q
            point={n:Q.from_float(float(v)) for n,v in zip(lp.col_names_,points[-1])}
            assert witness_feasible(follow.checker.canonical(path),point)
            results.append(dict(solver=solver,numerical_control=policy,passed=True,
                objective=outcome['objective'],candidate_vectors=len(points),native_import=imported))
    save(HERE/'NATIVE_TEST.json',dict(status='passed',technical_MIP_calls=2,
        benchmark_observations=0,tests=results))
    print('Both native-import/callback/control tests passed; two technical MIPs, zero benchmark observations.')


if __name__=='__main__':main()
