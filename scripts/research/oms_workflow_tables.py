#!/usr/bin/env python3
"""Regenerate the small IF/workflow supplement table from checked records."""
from pathlib import Path
import runpy
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'exploration/oms-if1-workflow-20261015'
runpy.run_path(str(HERE/'write_report.py'),run_name='__main__')
for filename in ('if1-accuracy.tex','workflow-cost.tex'):
    shutil.copyfile(HERE/filename,ROOT/'paper/tables'/filename)
runpy.run_path(str(ROOT/'scripts/research/reconcile_oms_work.py'),run_name='__main__')
