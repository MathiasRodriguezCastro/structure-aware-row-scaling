#!/usr/bin/env python3
"""Bundle all new evidence with its exact parent and replay from clean extraction."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT=ROOT/'paper/submission/orf/releases/v1.4.2-orf-submission'
DESKTOP=Path('/home/mathiasr/Escritorio')


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def run(cmd,cwd):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(cmd)+'\n'+p.stdout[-4000:]+p.stderr[-2500:])
    return p.stdout
def unpack(path,out,member=None):
    with zipfile.ZipFile(path) as z:
        if member is not None:
            with z.open(member) as source,(out/member).open('wb') as dest:shutil.copyfileobj(source,dest)
        else:
            assert all((out/n).resolve().is_relative_to(out.resolve()) for n in z.namelist())
            z.extractall(out)


def main():
    for name in ['VALIDATION.json','STATISTICS_VALIDATION.json','SELECTOR_VALIDATION.json','SELECTOR_BENCHMARK.json','PRECISION_RESULTS.json']:
        assert load(HERE/name)['status']=='passed',name
    log=(HERE/'research-note.log').read_text()
    assert 'Overfull' not in log and 'undefined' not in log.lower()
    old=load(PARENT/'VALIDATION.json')
    assert sha(PARENT/'orf-delivery.zip')==old['delivery']['sha256']
    excluded={'__pycache__','captured-exports'};suffixes={'.zip','.aux','.out','.pyc','.toc'}
    files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and not excluded.intersection(p.parts)
        and p.suffix not in suffixes and p.name not in ['PACKAGE_VALIDATION.json','EVIDENCE_MANIFEST.json','research-note.log']]
    manifest={p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in files}
    save(HERE/'EVIDENCE_MANIFEST.json',dict(scientific_files=manifest,
        omitted_duplicates='captured-exports duplicates the canonical exports in models; no unique native input omitted.',
        parent='v1.4.2-orf-submission',manuscript_modified=False))
    files.append(HERE/'EVIDENCE_MANIFEST.json')
    evidence=HERE/'research-evidence.zip'
    with zipfile.ZipFile(evidence,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
        sums=''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in files)
        z.writestr('FOLLOWUP_CONTENTS.sha256',sums)
    print('Built research evidence:',len(files),'files',evidence.stat().st_size,'bytes',flush=True)
    commands=['check.py','check_selector.py','precision.py','analyze.py','check_statistics.py','projection_sensitivity.py']
    with tempfile.TemporaryDirectory(prefix='orf-v15-clean-replay-') as tmp:
        space=Path(tmp);wrapper=space/'parent-wrapper';wrapper.mkdir();science=space/'science';science.mkdir()
        parent_archive=PARENT/'ESM_2.zip'
        for member in ['scientific-evidence-oms-v1.3.17.zip','prospective-scenarios-orf-20261018.zip']:
            unpack(parent_archive,wrapper,member);unpack(wrapper/member,science)
        unpack(evidence,science)
        run(['sha256sum','--quiet','-c','FOLLOWUP_CONTENTS.sha256'],science)
        output=[]
        for script in commands:
            print('Clean replay:',script,flush=True)
            result=run(['python3','exploration/orf-v15-verified-20261019/'+script],science)
            output.append(dict(command=script,passed=True,stdout_sha256=hashlib.sha256(result.encode()).hexdigest()))
        copied=science/'exploration/orf-v15-verified-20261019'
        for filename in ['VALIDATION.json','STATISTICS_VALIDATION.json','PRECISION_RESULTS.json','COMPUTATIONAL_RESULTS.json','PROJECTION_SENSITIVITY.json']:
            assert (HERE/filename).read_bytes()==(copied/filename).read_bytes(),filename
        validation=dict(status='passed',clean_extraction=True,commands=output,
            research_evidence_sha256=sha(evidence),parent_ESM_2_sha256=sha(parent_archive),
            full_candidate_replay_identical=True,grouped_statistics_identical=True,
            additional_optimizer_calls=0,frozen_manuscript_version='v1.4.2-orf-submission',
            frozen_manuscript_delivery_sha256=sha(PARENT/'orf-delivery.zip'),
            new_optimization_assignments=630,additional_technical_repetitions=1,new_independent_scenarios=0)
        save(HERE/'PACKAGE_VALIDATION.json',validation)
    guide='''# Investigación para una posible v1.5: paquete completo

El manuscrito de envío permanece en v1.4.2. Leer research-note.pdf y RESULTADOS.md.
No se presenta esta investigación como una nueva versión enviada ni una mejora
de rendimiento ya establecida frente a L2.

1. Verificar SHA256SUMS en esta carpeta.
2. Extraer ORF-v1.4.2-ESM_2.zip. De su contenido, extraer primero
   scientific-evidence-oms-v1.3.17.zip en una raíz vacía y después
   prospective-scenarios-orf-20261018.zip en la misma raíz.
3. Superponer research-evidence.zip en esa raíz; verificar
   sha256sum -c FOLLOWUP_CONTENTS.sha256. Los nombres OMS identifican la
   procedencia del archivo científico heredado, no el destino actual del paper.
4. Instalar las dependencias abiertas de environment/research-requirements.txt
   y ejecutar los comandos de README.md del seguimiento. No necesitan Gurobi
   ni CPLEX. La repetición de las resoluciones sí requiere licencias y generador.

PACKAGE_VALIDATION.json documenta el replay limpio de este ZIP de evidencia,
incluidos todos los puntos y estadísticas. Se conservan resultados adversos,
la enmienda técnica, todas las semillas y los archivos realmente exportados.
La proyección a cotas es una sensibilidad posterior; no modifica el criterio
primario ni atribuye disponibilidad en línea a la reparación.

DOI y envío editorial permanecen pendientes; no se realizaron acciones remotas.
'''
    target=DESKTOP/'ORF-investigacion-v15-20261019.zip'
    with zipfile.ZipFile(target,'w') as z:
        content={'research-note.pdf':HERE/'research-note.pdf','RESULTADOS.md':HERE/'RESULTADOS.md',
            'MATH_NOTE.md':HERE/'MATH_NOTE.md','research-evidence.zip':evidence,
            'ORF-v1.4.2-ESM_2.zip':PARENT/'ESM_2.zip','main_v1.4.2.pdf':PARENT/'main_orf.pdf',
            'PACKAGE_VALIDATION.json':HERE/'PACKAGE_VALIDATION.json'}
        for n,p in content.items():z.write(p,n,compress_type=zipfile.ZIP_STORED)
        z.writestr('LEEME.md',guide)
        sums=''.join(f'{sha(p)}  {n}\n' for n,p in sorted(content.items()))
        sums+=f'{hashlib.sha256(guide.encode()).hexdigest()}  LEEME.md\n'
        z.writestr('SHA256SUMS',sums)
    # Verify the deliverable itself, not just its source directory.
    with tempfile.TemporaryDirectory(prefix='orf-v15-delivery-') as tmp:
        dest=Path(tmp);unpack(target,dest);run(['sha256sum','--quiet','-c','SHA256SUMS'],dest)
        assert sha(dest/'research-evidence.zip')==validation['research_evidence_sha256']
    target.with_suffix('.zip.sha256').write_text(f'{sha(target)}  {target.name}\n')
    print('Validated full research delivery:',target,'bytes',target.stat().st_size,'SHA256',sha(target),flush=True)


if __name__=='__main__':main()
