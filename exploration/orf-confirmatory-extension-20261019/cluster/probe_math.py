#!/usr/bin/env python3
"""Diagnose floating-point stages of the frozen L2 kernel, without solvers."""
import json
import math
import os
from pathlib import Path
import platform
import sys
import numpy as np
try:
    from threadpoolctl import threadpool_info
except ImportError:
    def threadpool_info():return []

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from runner import ROOT,library,save

check=library(ROOT/'exploration/orf-confirmatory-20261018/check.py','math_probe_reader')
rows,_=check.parse(HERE/'models/simple-v1_simple_000039-h360/Base.lp')
a=np.abs([float(v) for v in rows['a1_bonete_tangente_1(1)']['terms'].values()])
hi=float(a.max());norm=float(np.linalg.norm(a/hi));target=-math.log(hi)-math.log(norm)
report=dict(OPENBLAS_CORETYPE=os.environ.get('OPENBLAS_CORETYPE'),libc=platform.libc_ver(),
    stages={k:v.hex() for k,v in dict(hi=hi,norm=norm,log_hi=math.log(hi),
        log_norm=math.log(norm),target=target,exp=math.exp(target)).items()},
    libraries=threadpool_info(),optimizer_calls=0)
save(HERE/('MATH_PROBE-'+sys.argv[1]+'.json'),report)
print(json.dumps(report,indent=2))
