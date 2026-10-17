#!/usr/bin/env python3
"""Close a separate research archive; never include historical ZIPs or credentials."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
TARGET=HERE/'oms-strengthening-artifact.zip'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if TARGET.exists():raise RuntimeError('closed research archive exists; do not overwrite')
    files=set()
    folders=['oms-frontier-20261016','oms-native-selector-20261016','oms-joint-contracts-20261016','oms-global-lp-20261016','oms-strengthening-20261016']
    for folder in folders:
        for p in (ROOT/'exploration'/folder).rglob('*'):
            if not p.is_file() or any(x in p.parts for x in ('__pycache__','.pytest_cache')):continue
            if p.suffix in ('.zip','.o','.d','.pyc','.aux','.out'):continue
            if p.name in ['MANIFEST.json','ARCHIVE_VALIDATION.json','archive-validation.log']:continue
            files.add(p.relative_to(ROOT))
    for folder in ['scripts']:
        files.update(p.relative_to(ROOT) for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts)
    for p in (ROOT/'code').rglob('*'):
        if p.is_file() and p.suffix in ('.cpp','.h','.hpp') and not any(x.startswith('build') for x in p.relative_to(ROOT/'code').parts):files.add(p.relative_to(ROOT))
    for filename in ['LICENSE','DATA_LICENSE.md','code/Makefile','scripts/research/oms_frontier_tables.py']:files.add(Path(filename))
    for folder in folders:
        for name in ['design.json','solve-design.json','ablation-design.json','repair-design.json']:
            p=ROOT/'exploration'/folder/name
            if p.exists():files.update(Path(rel) for rel in json.loads(p.read_text()).get('dependencies',{}))
    for name in ['precision-frontier.tex','native-selection-cost.tex','global-lp-certificates.tex']:
        files.add(Path('paper/tables')/name)
    for n in ['instance001','instance005','instance022','instance027','instance031','instance046']:
        for name in ['Base.lp','input.txt']:files.add(Path('exploration/oms-matched-accuracy-20261016/inputs')/n/name)
    # Programs used to acquire earlier references are pinned as provenance.
    for name in ['common.py','exact_lp.py']:files.add(Path('exploration/oms-root-attribution-20261015')/name)
    first=ROOT/'exploration/oms-native-selector-20261016/first-pass/design.json'
    for rel in json.loads(first.read_text())['dependencies']:
        if not rel.startswith('exploration/oms-native-selector-20261016/'):files.add(Path(rel))
    files=sorted(files)
    for p in files:assert (ROOT/p).is_file(),str(p)
    manifest={'date':'2026-10-16','native_MIP_calls':384,'new_research_LP_calls':56,
        'timed_preparations':336,'primal_repair_outputs':18,'global_one_percent_outputs':9,'exact_optimal_outputs':3,
        'scope':'Separate exploratory joint method and complete new sensitivity/software/reference evidence; no guarantee of publication',
        'files':[{'path':str(p),'bytes':(ROOT/p).stat().st_size,'sha256':sha(ROOT/p)} for p in files]}
    (HERE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in files:archive.write(ROOT/p,str(p))
        archive.write(HERE/'MANIFEST.json',str((HERE/'MANIFEST.json').relative_to(ROOT)))
        archive.writestr('RESEARCH_REPLAY.md',"""# Research archive, 16 October 2026

This is separate from the OMS submission package. It preserves every new native
result, exact point, graph certificate and both complete C++ benchmark passes.
No historical ZIP is required for the following saved numerical replays:

```
python3 exploration/oms-frontier-20261016/independent_check.py --allow-absent-historical
python3 exploration/oms-native-selector-20261016/independent_check.py
python3 exploration/oms-joint-contracts-20261016/independent_check.py --allow-absent-historical
python3 exploration/oms-joint-contracts-20261016/check_solves.py
python3 exploration/oms-joint-contracts-20261016/check_ablation.py
python3 exploration/oms-global-lp-20261016/independent_check.py
python3 exploration/oms-global-lp-20261016/check_repairs.py
python3 scripts/research/oms_frontier_tables.py
```

These commands import no commercial optimizer and invoke no optimization or
external process. They read LPs with HiGHS and compute rational residuals and
certificate identities. The optional historical flag skips absent old frozen
submission packages, not the required inputs or new results. Tests of the graph
also use toy SciPy reference LPs; rebuilding the optional C++ test needs Boost.
The standalone preparation benchmark is not a full-solve speedup. All global
certificates apply to explicitly identified original-Base/refined rational points.
The row/column formulation and graph techniques have classical antecedents; novelty
and external validation of this prototype are not established. No deposit or
journal submission was performed. Preserve the per-study protocols and adverse data.
""")
    (HERE/'SHA256SUMS').write_text(sha(TARGET)+'  '+TARGET.name+'\n')
    print('Closed',TARGET,'files',len(files),'bytes',TARGET.stat().st_size,flush=True)

if __name__=='__main__':main()
