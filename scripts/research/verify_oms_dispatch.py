#!/usr/bin/env python3
"""Read-only replay of new OMS exports, saved incumbents and reported aggregates."""
import csv
from fractions import Fraction
import gzip
import json
import math
from pathlib import Path
import tempfile
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import oms_dispatch_validation as campaign
from audit_identifiability_grid import parse
import audit_fixed_basis as afb

out=campaign.OUT
design=json.loads((out/'design.json').read_text())
exports=list(csv.DictReader((out/'exports.csv').open()))
runs=list(csv.DictReader((out/'runs.csv').open()))
assert len(exports)==len(runs)==132
assert len({(r['class'],r['instance'],r['policy']) for r in runs})==132
limits={};physical=[];checked=0
with tempfile.TemporaryDirectory(prefix='oms-independent-') as temp:
    temp=Path(temp)
    for item in design['instances']:
        cls,name=item['class'],item['instance']
        folder=out/'exports'/cls/name
        (temp/'Base.lp').write_bytes(gzip.decompress((folder/'Base.lp.gz').read_bytes()))
        base=afb.read_lp(temp/'Base.lp');parsed,_=parse(temp/'Base.lp')
        if item['ablation']:
            content=lambda p:gzip.decompress((folder/(p+'.lp.gz')).read_bytes())
            assert content('Base')==content('Coupling-only')
            assert content('Role-Hybrid')==content('Local-only')
        limits[cls,name]={n:(min(abs(float(c)) for c in r['terms'].values() if c),max(abs(float(c)) for c in r['terms'].values())) for n,r in parsed.items()}
        for rec in (r for r in exports if r['class']==cls and r['instance']==name):
            policy=rec['policy'];path=temp/(policy+'.lp')
            path.write_bytes(gzip.decompress((folder/(policy+'.lp.gz')).read_bytes()))
            assert campaign.sha(path)==rec['lp_sha256']
            afb.check_scaling(base,afb.read_lp(path),temp/'factors.csv')
            run=next(r for r in runs if (r['class'],r['instance'],r['policy'])==(cls,name,policy))
            assert int(run['completed'])==int(run['status']=='2')
            expected=float(run['total_seconds']) if int(run['completed']) else 1200.
            assert float(run['par10_seconds'])==expected
            assert math.isclose(float(run['total_seconds']),sum(float(run[k]) for k in ('prepare_seconds','load_seconds','optimizer_seconds')),rel_tol=1e-12)
            log=(out/'runs'/cls/name/(policy+'.log')).read_text()
            assert 'TimeLimit to value 120' in log and 'Seed to value 42' in log
            if int(run['sol_count']):
                sol=np.load(out/'runs'/cls/name/(policy+'-solution.npz'))
                values=dict(zip(sol['names'].tolist(),sol['x'].tolist()))
                verified,groups=campaign.verify_point(temp/'Base.lp',path,values,policy,cls,name)
                for key in ('max_absolute_row_residual','max_activity_normalized_residual','max_bound_violation','max_integrality_violation'):
                    assert math.isclose(float(run[key]),verified[key],rel_tol=1e-12,abs_tol=1e-15)
                physical.extend(groups)
            checked+=1
        print('verified exports and points',cls,name,flush=True)
f=Fraction.from_float
count=0;changes=0
with gzip.open(out/'factor-contracts.csv.gz','rt') as fh:
    for row in csv.DictReader(fh):
        minimum,maximum=limits[row['class'],row['instance']][row['row_name']]
        lo=max(f(1e-6)/f(float(row['algebraic_budget'])),f(1e-9)/f(minimum))
        hi=f(1e9)/f(maximum)
        assert f(float(row['lower']))>=lo and f(float(row['upper']))<=hi
        if row['decision']=='incompatible':assert lo>hi or float(row['lower'])>float(row['upper'])
        else:
            applied=f(float(row['applied']))
            assert lo<=applied<=hi
            assert float(row['applied'])==min(max(float(row['proposed']),float(row['lower'])),float(row['upper']))
        changes+=row['decision']!='unchanged';count+=1
stored=list(csv.DictReader((out/'physical-verification.csv').open()))
assert len(stored)==len(physical)
lookup={(r['class'],r['instance'],r['policy'],r['group']):r for r in stored}
for row in physical:
    saved=lookup[row['class'],row['instance'],row['policy'],row['group']]
    for key in ('max_original_physical_residual','max_exported_row_violation','max_pointwise_export_defect_physical'):
        assert math.isclose(float(saved[key]),row[key],rel_tol=1e-12,abs_tol=1e-15)
    assert int(saved['exported_hypothesis_failures'])==row['exported_hypothesis_failures']
summaries=json.loads((out/'summary.json').read_text())
for row in summaries['comparison']:
    cls,policy=row['class'],row['policy']
    members=[r for r in runs if r['class']==cls and r['policy'] in campaign.POLICIES]
    common=[n for n in {r['instance'] for r in members} if all(any(r['instance']==n and r['policy']==p and int(r['completed']) for r in members) for p in campaign.POLICIES)]
    selected=[r for r in members if r['policy']==policy]
    assert row['instances']==15 and row['completed']==sum(int(r['completed']) for r in selected)
    assert row['common_completed']==len(common)
    assert math.isclose(row['mean_par10_seconds'],sum(float(r['par10_seconds']) for r in selected)/15,rel_tol=1e-12)
    baseline={r['instance']:r for r in members if r['policy']=='Base'}
    for key,target in [('work','geomean_work_ratio'),('total_seconds','geomean_total_time_ratio')]:
        expected=math.exp(sum(math.log(float(r[key])/float(baseline[r['instance']][key])) for r in selected if r['instance'] in common)/len(common))
        assert math.isclose(row[target],expected,rel_tol=1e-12)
# Descriptive sensitivity of this same campaign; no new optimization calls.
clean_names={'instance001','instance005','instance022','instance027','instance031','instance046'}
clean_members=[r for r in runs if r['class']=='sgtm' and r['instance'] in clean_names and r['policy'] in campaign.POLICIES]
assert len(clean_members)==24 and all(int(r['completed']) for r in clean_members)
clean_base={r['instance']:r for r in clean_members if r['policy']=='Base'}
clean_summary=[]
for policy in campaign.POLICIES:
    selected=[r for r in clean_members if r['policy']==policy]
    row={'class':'sgtm','policy':policy,'instances':len(selected),'completed':sum(int(r['completed']) for r in selected),
         'instance_names':';'.join(sorted(clean_names))}
    for key,target in [('work','geomean_work_ratio'),('total_seconds','geomean_total_time_ratio')]:
        row[target]=math.exp(sum(math.log(float(r[key])/float(clean_base[r['instance']][key])) for r in selected)/len(selected))
    clean_summary.append(row)
campaign.csvwrite(out/'clean-subset-summary.csv',clean_summary)
campaign.dump(out/'independent-verification.json',{'exports_and_runs':checked,'contract_decisions':count,'modified_or_incompatible':changes,'original_unit_incumbents_rechecked':len({(r['class'],r['instance'],r['policy']) for r in physical}),'settings_logs_checked':True,'reported_comparison_aggregates_recomputed':True,'demand_inversion_free_sensitivity_models':len(clean_names),'clean_subset_aggregates_recomputed':True})
print('OMS saved-result verification passed',checked,count)
