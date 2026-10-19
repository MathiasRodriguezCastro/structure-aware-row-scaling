#!/usr/bin/env python3
"""Create a small, self-contained validation dossier, separate from submission."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
bundle=HERE/'review-bundle';bundle.mkdir(exist_ok=False)
files=['NOTA_VALIDACION.md','STRUCTURAL_FEASIBILITY_AUDIT.json','STRUCTURAL_CERTIFICATE_REPLAY.json',
    'verify_farkas_bundle.py','FACTOR_PORTABILITY-Haswell-all.json','MATH_PROBE-automatic.json',
    'MATH_PROBE-Haswell.json','REFERENCE_RECOVERY_PLAN.json','REFERENCE_RECOVERY_REPORT.json',
    'CONFIRMATION_ANALYSIS_DRAFT.md']
for name in files:shutil.copyfile(HERE/name,bundle/name)
audit=json.loads((HERE/'STRUCTURAL_FEASIBILITY_AUDIT.json').read_text())
for name in audit['certified_infeasible_instances']:
    target=bundle/'models'/name;target.mkdir(parents=True)
    shutil.copyfile(HERE/'models'/name/'Base.lp',target/'Base.lp')
(bundle/'LEEME.md').write_text('''# Dossier de validación — 19 de octubre de 2026

Este dossier permite reproducir los dos certificados exactos de incompatibilidad
con Python estándar y los dos LP originales incluidos:

```sh
python3 -I verify_farkas_bundle.py
```

El verificador lee directamente las filas y cotas de los LP, comprueba sus
hashes y suma las desigualdades con aritmética racional. Verifica tanto los
datos binario64 como los decimales escritos. No necesita NumPy, HiGHS, Gurobi
ni CPLEX. Ejecutarlo sin las opciones -O/-OO.

La nota explica la causa en el M dependiente del horizonte y sus consecuencias
para la ampliación experimental. Los informes de portabilidad y recuperación
documentan comprobaciones más amplias realizadas en el repositorio. Reproducir
las 192 preparaciones, los 384 exports o las ejecuciones del piloto requiere
sus fuentes y artefactos completos en la rama de investigación; este ZIP permite
verificar directamente los dos certificados y sus datos de entrada.

El manuscrito v1.5.0-orf-submission y su ZIP de envío permanecen sin cambios.
Los hallazgos de este dossier pertenecen a la investigación posterior y todavía
no constituyen una comparación confirmatoria del rendimiento de Budget-L2.
''')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
(bundle/'PROVENANCE.json').write_text(json.dumps(dict(research_commit=commit,
    submission_parent='2fbb5f14',scope='two self-contained exact infeasibility certificates and research validation records',
    no_optimization_calls_required=True),indent=2)+'\n')
manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(bundle))+'\n'
    for p in sorted(bundle.rglob('*')) if p.is_file())
(bundle/'SHA256SUMS.txt').write_text(manifest)
target=Path.home()/'Escritorio/VALIDACION-ORF-20261019.zip';assert not target.exists()
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for p in sorted(bundle.rglob('*')):
        if p.is_file():archive.write(p,p.relative_to(bundle))
with tempfile.TemporaryDirectory(prefix='orf-proof-extraction-') as tmp:
    extracted=Path(tmp)
    with zipfile.ZipFile(target) as archive:archive.extractall(extracted)
    for line in (extracted/'SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256((extracted/name).read_bytes()).hexdigest()==digest
    subprocess.run(['python3','-I',str(extracted/'verify_farkas_bundle.py')],check=True)
    altered=json.loads((extracted/'STRUCTURAL_FEASIBILITY_AUDIT.json').read_text())
    altered['certificates'][0]['contradiction_rhs_exact']='0'
    (extracted/'STRUCTURAL_FEASIBILITY_AUDIT.json').write_text(json.dumps(altered))
    result=subprocess.run(['python3','-I',str(extracted/'verify_farkas_bundle.py')],capture_output=True)
    assert result.returncode!=0,'A false certificate was accepted'
digest=hashlib.sha256(target.read_bytes()).hexdigest()
target.with_suffix(target.suffix+'.sha256').write_text(digest+'  '+target.name+'\n')
record=dict(status='passed',zip_path=str(target),zip_bytes=target.stat().st_size,sha256=digest,
    clean_extraction_hashes_passed=True,standard_library_proof_replay_passed=True,
    altered_certificate_rejected=True,research_commit=commit,scope='validation dossier; not a replacement submission archive')
(HERE/'REVIEW_BUNDLE.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
