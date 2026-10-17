#!/usr/bin/env python3
"""Package a focused OMS diagnostic and verify optimizer-free replay."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PREFIX='exploration/oms-root-attribution-20261015/'
ARCHIVE='root-attribution-artifact.zip'


def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(args)+'\n'+p.stdout[-2500:]+'\n'+p.stderr[-2500:])
    return p.stdout


def main():
    files={};excluded={ARCHIVE,'MANIFEST.json','VALIDATION.json'}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name not in excluded and p.suffix not in ('.aux','.out') and not p.name in ('pdf-build.log','root-attribution-note.log','package-validation.log','package-replay.log','analysis.log','independent-check.log') and not any(s in p.parts for s in ('__pycache__','.pytest_cache')):
            files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    files['exploration/OMS_RESEARCH_FILTER.md']=(HERE.parent/'OMS_RESEARCH_FILTER.md').read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    files['README.md']=b'''# Common-incumbent row-scaling diagnostic for OMS

Read exploration/oms-root-attribution-20261015/README.md and its two-page PDF.
36 MILPs compare Base/GM with and without the same independently checked
incumbent, on three known dispatch cases and three fresh seeds. Exact
references, native runs and fixed-pattern LP checks are included. This is
retrospective mechanism attribution, not a new algorithm, predictor or global
optimality certification. Two unknown LP outcomes are retained. The current
OMS frozen release is unchanged. Python/NumPy/pytest suffice for native-solver-
free replay; pdfLaTeX builds the note. Native solver binaries are not included.
'''
    manifest=dict(version='oms-root-attribution-20261015-v1',self_contained_data=True,native_mip_calls=36,
        native_reference_lp_calls=3,native_posthoc_lp_calls=15,principal_new_method_claim=False,
        files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())])
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/ARCHIVE
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):z.writestr(n,b)
        z.writestr('MANIFEST.json',raw)
    validation=dict(version=manifest['version'],archive_sha256=sha(archive.read_bytes()),archive_bytes=archive.stat().st_size,
        inventoried_files=len(files),self_contained_inputs_and_certificates=True,new_native_mip_calls=36,
        new_native_lp_calls=18,optimizer_calls_during_replay=0)
    print('Archive ready; clean extraction replay',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-root-attribution-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for r in manifest['files']:assert sha((folder/r['path']).read_bytes())==r['sha256'],r['path']
        verify()
        harness='''import builtins,runpy,sys,subprocess,os
original=builtins.__import__
def guard(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt','cplex'}:raise RuntimeError('optimizer import during replay')
    return original(name,*args,**kwargs)
builtins.__import__=guard
def blocked(*args,**kwargs):raise RuntimeError('process execution during replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
study=sys.argv[1];sys.path.insert(0,study)
for name in ['analyze.py','independent_check.py','write_report.py']:
    sys.argv=[study+'/'+name];runpy.run_path(study+'/'+name,run_name='__main__')
'''
        out=run(['python3','-c',harness,PREFIX.rstrip('/')],folder);(HERE/'package-replay.log').write_text(out);verify()
        study=folder/PREFIX;v=json.loads((study/'independent-verification.json').read_text())
        assert v['loaded_common_start_pattern_cost_checks']==18 and v['final_pattern_assignments_checked']==36
        assert v['final_pattern_optimum_certified']==13 and v['final_pattern_unknown']==2
        assert v['reference_optimum_certified']==3 and v['candidate_exact_objective_checks']==226
        for name in ['sources-before-reference.json','sources-before-mip.json','metrics-before-mip.json']:
            for n,h in json.loads((study/name).read_text()).items():assert sha((study/n).read_bytes())==h
        tests=run(['python3','-m','pytest','-q',str(study/'test_metrics.py')],folder);assert '4 passed' in tests
        build=folder/'pdf-build';build.mkdir();shutil.copyfile(study/'root-attribution-note.tex',build/'root-attribution-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','root-attribution-note.tex'],build)
        log=(build/'root-attribution-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        one=run(['pdftotext','-layout',str(study/'root-attribution-note.pdf'),'-'],folder)
        two=run(['pdftotext','-layout',str(build/'root-attribution-note.pdf'),'-'],folder);assert one==two
        info=run(['pdfinfo',str(build/'root-attribution-note.pdf')],folder)
        assert any(t.split(':')[1].strip()=='2' for t in info.splitlines() if t.startswith('Pages:'))
        verify()
        validation.update(clean_extraction_hashes_verified=True,all_derived_outputs_identically_regenerated=True,
            optimizer_imports_and_processes_blocked=True,reference_exact_primal_dual_certificates=3,
            final_pattern_exact_optima=13,final_pattern_unknown_preserved=2,
            candidate_exact_objective_checks=226,final_original_row_replays=36,
            loaded_common_start_pattern_cost_checks=18,exact_product_checks=v['exact_product_checks'],
            tests_passed=4,pdf_pages=2,pdf_overfull_boxes=0)
    protected=json.loads((HERE/'protected-files.json').read_text())
    for n,h in protected.items():assert sha(Path(n).read_bytes())==h,n
    validation.update(protected_files_unchanged=len(protected),eleven_previous_research_archives_unchanged=True,
        oms_v1_3_5_delivery_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2),flush=True)


if __name__=='__main__':main()
