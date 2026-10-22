#!/usr/bin/env python3
"""Freeze only a validated ORF delivery; prepare local portal/deposit copies."""
import json
from pathlib import Path
import shutil
import tempfile
from orf_config import ROOT, OUT, VERSION, sha


def main():
    validation=json.loads((OUT/'VALIDATION.json').read_text())
    assert validation['version']==VERSION
    assert validation['new_optimization_experiments']==1351
    assert validation['logging_confirmation']['complete_native_logs']==360
    assert validation['logging_confirmation']['replication']['assignments']==360
    assert validation['delivery']['sha256']==sha(OUT/'orf-delivery.zip')
    assert validation['canonical_editorial_regeneration_identical']
    assert validation['scenario_cluster_uncertainty']['status']=='passed'
    assert validation['known_parent_deletion_sensitivity']['status']=='passed'
    assert validation['prospective_tables_regenerated_from_audited_data']
    assert validation['verified_followup_replay']['status']=='passed'
    assert validation['verified_followup_tables_regenerated_identically']==5
    assert all(v['passed'] for v in validation['replay']['four_standard_commands'].values())
    files={p.name:p for p in (OUT/'uploads').iterdir() if p.is_file() and p.name!='SHA256SUMS'}
    files.update({'orf-delivery.zip':OUT/'orf-delivery.zip','VALIDATION.json':OUT/'VALIDATION.json',
                  'SNAPSHOT.json':OUT/'SNAPSHOT.json','CITATION.cff':ROOT/'CITATION.cff',
                  'zenodo-metadata.json':ROOT/'.zenodo.json'})
    release=OUT/'releases'/VERSION
    if release.exists():
        assert all(sha(release/n)==sha(p) for n,p in files.items()),'Frozen ORF release differs'
    else:
        release.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.orf-freeze-',dir=release.parent) as tmp:
            staging=Path(tmp)/VERSION;staging.mkdir()
            for n,p in files.items():
                shutil.copyfile(p,staging/n);assert sha(staging/n)==sha(p)
            (staging/'SHA256SUMS').write_text(''.join(f'{sha(staging/n)}  {n}\n' for n in sorted(files)))
            staging.rename(release)
        for p in release.iterdir():p.chmod(0o444)
    # These are local, reviewable preparations. No remote upload or publication.
    portal=OUT/'portal-preparation'/VERSION;portal.mkdir(parents=True,exist_ok=True)
    for n in ('FORM_FIELDS.json','UPLOAD_INSTRUCTIONS.md','ONLINE_RESOURCE_CAPTIONS.txt'):
        shutil.copyfile(release/n,portal/n)
    deposit=OUT/'zenodo-deposit'/VERSION;deposit.mkdir(parents=True,exist_ok=True)
    for n in ('ESM_2.zip','SNAPSHOT.json','CITATION.cff','zenodo-metadata.json','REPRODUCTION-VALIDATION.json'):
        shutil.copyfile(release/n,deposit/n)
    for n in ('LICENSE','DATA_LICENSE.md'):shutil.copyfile(ROOT/n,deposit/n)
    manifest={'version':VERSION,'remote_deposit_performed':False,'reserved_doi':None,
        'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}
                 for p in sorted(deposit.iterdir()) if p.name not in
                 ('SHA256SUMS','DEPOSIT_FILES.json','DEPOSIT_GUIDE.md')],
        'bulk_data_file':'ESM_2.zip','baseline_doi_is_not_current_version':True}
    (deposit/'DEPOSIT_FILES.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    (deposit/'DEPOSIT_GUIDE.md').write_text(f'''# Depósito de {VERSION}

Archivos locales preparados; no se ha creado ni publicado un registro remoto.
Como acordó el autor, el borrador y su DOI reservado se tramitan al final.

1. Crear una nueva versión del registro histórico en Zenodo. Reservar el DOI
   específico de esta versión; no reutilizar el DOI del experimento anterior.
2. Cargar ESM_2.zip y los archivos de identificación, licencias y validación de
   esta carpeta. DEPOSIT_FILES.json da los tamaños y hashes exactos.
3. Revisar título, autor, ORCID, versión y licencias con zenodo-metadata.json.
   El texto y los PDF del artículo mantienen sus propios derechos; MIT se aplica
   al código y CC BY 4.0 a datos/resultados, con las excepciones ya documentadas.
4. Incorporar el DOI reservado a disponibilidad, carta y metadatos; reconstruir
   y verificar el paquete que llevará ese DOI antes de cargar los archivos finales.
5. Tras publicar, comprobar que el archivo descargado coincide con su SHA-256.
   Entonces podrá prepararse para la revista un suplemento reducido con enlaces
   persistentes. Hasta ese momento se conserva el suplemento científico completo.

No hace falta repetir los MIP para completar estos pasos editoriales.
''')
    (deposit/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(deposit.iterdir()) if p.name!='SHA256SUMS'))
    print('Frozen ORF delivery:',release)
    print('Prepared local portal and Zenodo files; no remote changes.')


if __name__=='__main__':main()
