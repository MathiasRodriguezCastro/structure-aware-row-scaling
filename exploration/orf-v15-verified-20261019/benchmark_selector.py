#!/usr/bin/env python3
"""Fresh-process selection benchmark; reuse solves only after exact export equality."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import study as s


def worker(name,contract):
    import export_selector
    from export_selector_fast import choose
    export_selector.choose=choose
    a,front=s.old.modules();base=s.PARENT/'models'/name/'Base.lp'
    parsed,_=a.original_rows(base);_,lp,_=a.campaign.afb.read_lp(base)
    started=time.perf_counter();factors,info=s.select(parsed,lp,s.CONTRACTS[contract],True)
    elapsed=time.perf_counter()-started
    assert not info['incompatible_count']
    with tempfile.TemporaryDirectory(prefix='orf-selector-') as tmp:
        path=Path(tmp)/'model.lp';a.export_scaled(base,path,factors);h=s.sha(path)
    exhaustive=HERE/'models'/name/'Export-Budget-L2'/contract/'model.lp'
    assert s.sha(exhaustive)==h
    observed=[]
    for j in s.load(HERE/'design.json')['jobs']:
        if j['instance']==name and j['policy']=='Export-Budget-L2' and j['contract']==contract:
            observed.append(s.load(HERE/'runs'/j['id']/'result.json')['stages_seconds']['selection'])
    s.dump(HERE/'selector-benchmarks'/f'{name}-{contract}.json',dict(instance=name,contract=contract,
        ranked_selection_seconds=elapsed,recorded_exhaustive_selection_seconds=observed,
        exhaustive_median_seconds=statistics.median(observed),same_full_export_sha256=h,
        full_export_identical_to_all_recorded_solver_inputs=True,
        candidates_tested=sum(d.get('candidates_tested',0) for d in info['decisions']),
        additional_optimizer_calls=0,paired_end_to_end_rerun=False))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',nargs=2);args=ap.parse_args()
    if args.worker:worker(*args.worker);return
    d=s.load(HERE/'design.json');subset=[n for n in d['models'] if n.endswith(('-01','-08'))]
    for name in subset:
        for c in d['contracts']:
            subprocess.run([sys.executable,str(Path(__file__)),'--worker',name,c],check=True,
                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
            print('Benchmarked',name,c,flush=True)
    rows=[s.load(p) for p in sorted((HERE/'selector-benchmarks').glob('*.json'))]
    s.dump(HERE/'SELECTOR_BENCHMARK.json',dict(status='passed',models=6,configurations=len(rows),
        all_full_exports_identical=True,additional_optimizer_calls=0,
        median_ranked_selection_seconds=statistics.median(r['ranked_selection_seconds'] for r in rows),
        median_exhaustive_selection_seconds=statistics.median(r['exhaustive_median_seconds'] for r in rows),
        geometric_selection_time_ratio=math_geomean([r['ranked_selection_seconds']/r['exhaustive_median_seconds'] for r in rows]),
        caution='Compilation-only benchmark; original complete-process times are not retroactively replaced.',results=rows))


def math_geomean(values):
    import math
    return math.exp(statistics.mean(math.log(v) for v in values))


if __name__=='__main__':main()
