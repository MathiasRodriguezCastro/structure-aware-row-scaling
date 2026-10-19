#!/usr/bin/env python3
"""Preserve completed written exports while the solver uses them; no solver calls."""
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'captured-exports';out.mkdir(exist_ok=True);seen=set();records={}
    design=json.loads((HERE/'design.json').read_text());jobs={j['id']:j for j in design['jobs']}
    while True:
        for p in (HERE/'runs').glob('II-*/scaled.lp'):
            if p.parent.name in seen or not (p.parent/'solver.log').exists():continue
            try:data=p.read_bytes()
            except FileNotFoundError:continue
            h=hashlib.sha256(data).hexdigest();target=out/(h+'.lp')
            if not target.exists():target.write_bytes(data)
            seen.add(p.parent.name);records[p.parent.name]=dict(sha256=h,job=jobs[p.parent.name])
        timing=json.loads((HERE/'timing.json').read_text())
        if len(timing)==len(jobs) or timing[-1]['returncode']!=0:break
        time.sleep(.5)
    (HERE/'CAPTURED_EXPORTS.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Preserved',len(list(out.glob('*.lp'))),'unique exports from',len(records),'assignments')


if __name__=='__main__':main()
