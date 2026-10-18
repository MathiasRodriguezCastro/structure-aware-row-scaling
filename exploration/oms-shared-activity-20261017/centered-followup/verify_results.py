"""Replay the frozen design and saved points with no optimizer or selector import."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics
import time

import numpy as np
import deliver

HERE=Path(__file__).resolve().parent
F=Fraction.from_float


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main(partial=False):
    design=json.loads((HERE/'pilot/design.json').read_text())
    for file,digest in design['sources'].items():assert sha(HERE/file)==digest
    for file,digest in design['parent_sources'].items():assert sha(HERE.parent/file)==digest
    models={m['name']:m for m in design['models']};checked_static=0;checked_rows=0
    data={};static=[]
    for v in design['variants']:
        scope=HERE/'pilot/models'/v['name']/v['budget_label'];arm=scope/v['policy']
        for file,key in (('model.lp','export_sha256'),('model.json','model_sha256'),('selection.json','selection_sha256')):assert sha(arm/file)==v[key]
        for file,key in (('original.json','original_sha256'),('base.json','base_sha256')):assert sha(scope/file)==v[key]
        original=json.loads((scope/'original.json').read_text());base=json.loads((scope/'base.json').read_text())
        source=HERE.parent/'pilot/models'/v['name'];item=models[v['name']]
        assert sha(source/'original-model.json')==item['original_sha256']
        assert sha(source/'contracted-model.json')==item['base_sha256']
        for model,file in ((original,'original-model.json'),(base,'contracted-model.json')):
            before=json.loads((source/file).read_text())
            for i in item['gate_rows']:before['rows'][i]['budget']=v['budget']
            assert model==before
        model=json.loads((arm/'model.json').read_text());meta=json.loads((arm/'selection.json').read_text())
        summary=deliver.check_static(base,model,meta);assert summary==v['static']
        checked_static+=1;checked_rows+=summary['source_rows_checked']
        data[(v['name'],v['budget_label'],v['policy'])]=(original,model,meta)
        static.append({'name':v['name'],'budget':v['budget'],'policy':v['policy'],**summary})
    results=[];failures=[];transfers=0;hypotheses=0
    for index,call in enumerate(design['calls']):
        out=HERE/'pilot/runs'/call['name']/call['budget_label']/call['policy']/str(call['seed'])
        if not (out/'completed.json').exists():continue
        completed=json.loads((out/'completed.json').read_text())
        assert completed['index']==index and completed['assignment_sha256']==sha(out/'assignment.json')
        assert json.loads((out/'assignment.json').read_text())==call
        if completed['returncode']:
            failures.append({'index':index,'name':call['name'],'policy':call['policy'],'returncode':completed['returncode']});continue
        record=json.loads((out/'run.json').read_text());saved=json.loads((out/'verification.json').read_text())
        assert all(record[k]==value for k,value in call.items())
        assert record['worker_through_verification_seconds']<=completed['fresh_process_seconds']
        original,model,meta=data[(call['name'],call['budget_label'],call['policy'])]
        assert sha(out/'model.lp')==call['export_sha256']
        row={k:record[k] for k in ('name','budget','budget_label','policy','seed','status','has_point','objective','work','runtime','selection_export_seconds','import_check_seconds')}
        row.update({'fresh_process_seconds':completed['fresh_process_seconds'],'verification_seconds':saved.get('verification_seconds',0.)})
        if record['has_point']:
            with np.load(out/'point.npz',allow_pickle=False) as z:values=z['x']
            verified=deliver.point(original,model,meta,values,design['reference_objectives'][call['name']])
            assert all(saved[key]==value for key,value in verified.items())
            transfers+=verified['valid_conditional_transfers'];hypotheses+=verified['activity_rows_checked']
            row.update({'primal_pass':verified['primal_pass'],'quality_target_met':verified['quality_target_met'],
                        'verified_objective':verified['original']['rounded']['objective'],
                        'objective_exact':verified['original']['rounded']['objective_exact'],
                        'maximum_row_budget_ratio':verified['original']['rounded']['maximum_row_budget_ratio'],
                        'maximum_bound_budget_ratio':verified['original']['rounded']['maximum_bound_budget_ratio'],
                        'activity_hypothesis_failures':len(verified['activity_hypothesis_failures']),
                        'exported_row_hypothesis_failures':verified['exported_row_hypothesis_failures']})
        results.append(row)
    total=len(results)+len(failures)
    if not partial:assert total==len(design['calls'])
    summary={'planned_calls':len(design['calls']),'completed_attempts':total,'successful_processes':len(results),
             'failed_processes':failures,'points_rechecked':sum(r['has_point'] for r in results),
             'static_variants_checked':checked_static,'source_rows_checked':checked_rows,
             'returned_activity_hypotheses_checked':hypotheses,'valid_conditional_transfers':transfers,
             'all_complete':total==len(design['calls']),'new_optimizer_calls':0,
             'native_optimality_claims_certified':0}
    (HERE/'VALIDATION.json').write_text(json.dumps(summary,indent=2)+'\n')
    (HERE/'RESULTS.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    (HERE/'STATIC_VALIDATION.json').write_text(json.dumps(static,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args();main(args.partial)
