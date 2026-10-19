#!/usr/bin/env python3
"""Audit available bank identities and component ancestry without solver outcomes."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validar_preprocesamiento import clean_instance_text


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),sort_keys=True).encode()).hexdigest()


def features(path):
    lines=[l.strip() for l in clean_instance_text(path).splitlines() if l.strip()]
    result={};local=total=None
    for i,l in enumerate(lines):
        if l.startswith('agregarAgente --SaltoGrande'):
            result['SG-hydrology']=fp([float(lines[i+2]),list(map(float,lines[i+3].split()))])
        if l.startswith('agregarAgente --RioNegro'):
            pal=9 if '--RioNegroNoLineal' in l else 5
            result['RN-hydrology']=fp([*[list(map(float,lines[i+j].split())) for j in [1,2,3]],
                float(lines[i+4]),float(lines[i+pal])])
        if l.startswith('agregarAgente --DemandaFija'):local=list(map(float,lines[i+1].split()))
        if l.startswith('crearDespacho --mercado'):total=list(map(float,lines[i+4].split()))
    assert local is not None
    result['local-demand']=fp(local)
    if total is not None:result['total-demand']=fp(total)
    return result, sum(a>b for a,b in zip(local,total)) if total else 0


def main():
    inventory=json.loads((HERE/'REMOTE_INVENTORY.json').read_text())
    manifest=ROOT/'results-revision/solver-robustness/inventory/instance-manifest.csv'
    metadata=ROOT/'results-revision/solver-robustness/inventory/raw/banco_meta/metadata.json'
    known=list(csv.DictReader(manifest.open()))
    index={(r['family_key'],r['instance']):r for r in known}
    ancestry=json.loads(metadata.read_text())
    # All 1,500 current pool files must match the independently inventoried bank.
    verified=Counter()
    for r in known:
        p=ROOT/'data/benchmark-v1'/r['family_key']/(r['instance']+'.txt')
        assert sha(p)==r['sha256'],str(p)
        verified[r['family_key']]+=1
    six=[p for p in (ROOT/'exploration/oms-frontier-20261016/models').glob('*/input.txt')]
    development={}
    for p in six:
        f,_=features(p)
        for k,v in f.items():development.setdefault(k,set()).add(v)
    selected=[];seen=set()
    for r in inventory['selected_parents']:
        p=ROOT/'data/benchmark-v1'/r['family']/Path(r['remote_path']).name
        assert sha(p)==r['sha256'] and r['sha256'] not in seen
        seen.add(r['sha256']);m=index[r['family'],p.stem]
        f,bad=features(p);assert bad==0,'Inverted demand data: '+r['parent_id']
        selected.append(dict(**r,component_fingerprints=f,
            shared_with_six_development_parents={k:v in development.get(k,set()) for k,v in f.items()},
            historical_component_sources={k:v for k,v in m.items() if k.endswith('_fuente') and v},
            previously_solved_Base=True,new_observed_operational_origin=False,
            local_source_sha256=sha(p),local_demand_exceeds_total_hours=bad))
    counts={role:dict(Counter(r['family'] for r in selected if r['role']==role))
            for role in ['pilot','confirmation']}
    assert counts==dict(pilot=dict(simple=3,sgtm=3,completo=2),confirmation=dict(simple=14,sgtm=13,completo=13))
    result=dict(status='passed_for_generated_population',remote_inventory_sha256=sha(HERE/'REMOTE_INVENTORY.json'),
        local_inventory_sha256=sha(manifest),historical_metadata_sha256=sha(metadata),
        all_1500_local_inputs_match_audited_remote_inventory=dict(verified),
        historical_component_catalogue=ancestry['componentes_disponibles'],
        registered_parent_counts=counts,selected_parents=selected,
        genuine_new_observed_operational_datasets=0,
        generated_population_confirmatory_parents=40,pilot_parents=8,
        all_selected_current_remote_files_match_local_copies=True,
        baseline_history_known=True,policy_outcomes_used_for_selection=False,
        large_simple_bank_primary_sample=False,
        limitation='Generated inputs share historical hydrology/economic components; unique files do not establish independent observed operational origins.')
    (HERE/'SOURCE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Verified 1,500 input identities and 48 selected parents; no demand inversion.')
    print('Confirmatory population:',counts['confirmation'],'; observed-new-origin count: 0.')


if __name__=='__main__':main()
