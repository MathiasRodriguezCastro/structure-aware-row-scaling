#!/usr/bin/env python3
"""Replay a frozen ORF delivery in isolation, leaving every input file unchanged."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile

import package_orf
import validate_orf
from orf_config import VERSION, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    release,output=args.release.resolve(),args.output.resolve()
    assert release.is_dir() and not output.exists()
    source_hash=sha(Path(__file__))
    record=release/'VALIDATION.json'
    if record.exists():
        frozen=json.loads(record.read_text())
    else:
        # The distributable delivery has this nested validation record.
        wrapper=json.loads((release/'REPRODUCTION-VALIDATION.json').read_text())
        assert wrapper['status']=='passed'
        frozen=wrapper['validation']
    assert frozen['version']==VERSION
    validate_orf.run(['sha256sum','--quiet','-c','SHA256SUMS'],release)
    expected={n:sha(release/n) for n in package_orf.FILES}
    assert all(expected[n]==frozen['archives'][n]['sha256'] for n in expected)
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='orf-frozen-audit-',dir='/tmp') as temp:
        isolated=Path(temp);uploads=isolated/'uploads';uploads.mkdir()
        for name in package_orf.FILES:(uploads/name).symlink_to(release/name)
        for name in package_orf.EXTRAS:shutil.copyfile(release/name,uploads/name)
        parent_record=isolated/'PARENT_REPLAY_VALIDATION.json'
        parent_record.write_text(json.dumps(frozen)+'\n')
        package_orf.OUT=isolated
        validate_orf.OUT=isolated
        sys.argv=['validate_orf.py','--reuse-parent-replay',str(parent_record)]
        validate_orf.main()
        validation=json.loads((isolated/'VALIDATION.json').read_text())
        assert all(sha(release/n)==digest for n,digest in expected.items())
        shutil.copyfile(isolated/'VALIDATION.json',output/'FULL_VALIDATION.json')
    proof=dict(status='passed',version=VERSION,audited_at_utc=datetime.now(timezone.utc).isoformat(),
        audit_script_sha256=source_hash,input_release_unchanged=True,new_MIP_experiments=0,
        source_files={n:dict(bytes=(release/n).stat().st_size,sha256=h) for n,h in expected.items()},
        resource_2_coverage=validation['resource_2_coverage'],
        replay_report_sha256=sha(output/'FULL_VALIDATION.json'),temporary_audit_wrapper_discarded=True,
        parent_replay='Only the byte-identical historical parent reuses its sealed four-command audit; all current saved-result checks run again from clean extraction.')
    (output/'AUDIT.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
    (output/'AUDITORIA.md').write_text(f'''# Auditoría inmutable de {VERSION}

**PASÓ**, sin modificar archivos de entrada ni ejecutar nuevos MIP.
Se reconstruyeron los 43.335 archivos del tar; se comprobó la presencia de
3.840 resultados, archivos de candidatos, logs nativos y relojes completos,
y 480 informes por bloque. Los archivos de candidatos de los diagnósticos
infactibles pueden estar vacíos. Se comprobó el complemento de auxiliares de
clúster, sus dependencias y la coincidencia con el registro de instalación.

Se reprodujeron 48 comparaciones y 80 intervalos de la confirmación, los
verificadores prospectivos y los seis del seguimiento, y 13.387 comprobaciones
de dominio desde los vectores. Las fuentes editables recompilaron y las tablas
actuales se regeneraron idénticas. La auditoría histórica idéntica se reutiliza;
las comprobaciones actuales se ejecutaron desde extracción limpia.

AUDIT.json identifica los archivos congelados mediante SHA-256.
FULL_VALIDATION.json registra la copia temporal de auditoría, cuyo ZIP se
descarta; sus hashes de entrada identifican los mismos seis archivos de carga.
El registro no afirma que se haya realizado el envío o un depósito público.
''')
    print('Immutable release audit passed:',output,flush=True)


if __name__=='__main__':
    if sys.flags.optimize:raise RuntimeError('Run without -O.')
    main()
