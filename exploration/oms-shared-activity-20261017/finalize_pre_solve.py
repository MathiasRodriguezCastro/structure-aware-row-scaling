"""Record the closed-form implementation amendment before any optimization."""
import copy
import hashlib
import json
from pathlib import Path
import time

import activity
import mps_check
import study

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'pilot/runs').exists(),'amendments must precede all solves'
    path=HERE/'pilot/design.json';design=json.loads(path.read_text());old=copy.deepcopy(design)
    saved=HERE/'pilot/design-before-closed-form.json'
    if saved.exists():raise RuntimeError('amendment already recorded')
    study.dump(saved,old)
    rebuilt=0;source_checks=[]
    for item in design['models']:
        folder=HERE/'pilot/models'/item['name'];base=json.loads((folder/'contracted-model.json').read_text())
        if item['name'] in ('beasleyC3','k16x240b'):
            original=json.loads((folder/'original-model.json').read_text())
            source_checks.append({'name':item['name'],**mps_check.check(HERE/'sources'/(item['name']+'.mps.gz'),original)})
        for assignment in design['assignments']:
            if assignment['name']!=item['name'] or assignment['policy']!='Shared-budget':continue
            arm=folder/assignment['arm'];k=assignment['unit_exponent']
            started=time.perf_counter();units=study.change_units(base,item['gate_rows'],k);_,groups=study.target_groups(units)
            model,meta=study.build(units,groups,'Shared-budget');assert model is not None
            assert model==json.loads((arm/'model.json').read_text())
            previous=json.loads((arm/'selection.json').read_text())
            assert all(meta[key]==previous[key] for key in ('factors','links','sos','selected_rows'))
            meta['unit_exponent']=k;meta['all_gate_rows']=item['gate_rows']
            study.dump(arm/'selection.json',meta)
            # The numeric exports are preserved; only certificates are added.
            assert study.sha(arm/'model.lp')==assignment['export_sha256']
            elapsed=time.perf_counter()-started;assignment['closed_form_reconstruction_seconds']=elapsed
            for call in design['calls']:
                if (call['name'],call['arm'])==(assignment['name'],assignment['arm']):call['closed_form_reconstruction_seconds']=elapsed
            rebuilt+=1
    design['activity_sha256']=study.sha(HERE/'activity.py')
    design['pre_solve_amendment']='closed-form interval selector; all prior numeric exports independently matched'
    study.dump(path,design)
    record={'before_first_optimize':True,'previous_activity_sha256':old['activity_sha256'],
            'current_activity_sha256':design['activity_sha256'],'previous_design_sha256':study.sha(saved),
            'all_rebuilt_numeric_exports_unchanged':True,'shared_variants_rebuilt':rebuilt,'independent_mps_checks':source_checks,
            'source_code_before_closed_form':'activity-before-closed-form.py','new_optimizer_calls':0,
            'timing_scope':'prototype stages recorded separately; common source acquisition/preparation outside per-run time; no fresh-process total-time claim'}
    study.dump(HERE/'PRE_SOLVE_AMENDMENT.json',record);print(json.dumps(record,indent=2))


if __name__=='__main__':main()
