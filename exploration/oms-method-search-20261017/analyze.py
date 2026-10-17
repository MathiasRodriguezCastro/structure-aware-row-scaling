"""Aggregate saved calls and matched controls; does not call an optimizer."""
import collections
import csv
import json
from pathlib import Path
import statistics

import numpy as np

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent


def main():
    summaries=[];runs={}
    for campaign in ('activity-scaling','integer-embedding'):
        root=PARENT/f'oms-{campaign}-20261017'
        validation=json.loads((root/'VALIDATION.json').read_text())
        assert validation['all_complete']
        data=json.loads((root/'pilot/RESULTS.json').read_text());groups=collections.defaultdict(list)
        for d in data:groups[(d['name'],d.get('presolve',-1),d['budget'],d['policy'])].append(d)
        runs[campaign]=validation['completed_calls']
        for (name,presolve,budget,policy),rows in sorted(groups.items()):
            assert len(rows)==3
            summaries.append({'campaign':campaign,'instance':name,'presolve':presolve,'budget':budget,'policy':policy,
                              'n':len(rows),'points':sum(d['has_point'] for d in rows),
                              'rounded_primal_pass':sum(d.get('primal_pass',d.get('rounded_primal_pass',False)) for d in rows),
                              'median_work':statistics.median(d['work'] for d in rows),
                              'median_returned_objective':statistics.median(d['objective'] for d in rows if d['has_point']),
                              'maximum_rounded_ratio':max(d['maximum_rounded_ratio'] for d in rows if d['has_point'])})
    with (HERE/'SUMMARY.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    root=PARENT/'oms-integer-embedding-20261017';design=json.loads((root/'pilot/design.json').read_text());pairs=[]
    for c in design['calls']:
        if c['presolve']!=-1 or not c['arm'].startswith('Integer-copy'):continue
        a=root/'pilot/runs'/c['name']/c['arm']/f'p-1-s{c["seed"]}'
        b=root/'pilot/runs'/c['name']/c['arm'].replace('Integer-copy','Continuous-copy')/f'p-1-s{c["seed"]}'
        x=json.loads((a/'run.json').read_text());y=json.loads((b/'run.json').read_text())
        with np.load(a/'point.npz',allow_pickle=False) as ax,np.load(b/'point.npz',allow_pickle=False) as bx:
            same=bool(np.array_equal(ax['x'],bx['x']))
        pairs.append({'name':c['name'],'arm':c['arm'],'seed':c['seed'],'identical_complete_point':same,
                      'identical_objective':x['objective']==y['objective'],'work_ratio_integer_to_continuous':x['work']/y['work']})
    result={'new_native_optimization_calls':sum(runs.values()),'calls_by_campaign':runs,
            'saved_points_reverified':sum(runs.values()),'automatic_presolve_matched_pairs':pairs,
            'all_nine_pairs_have_identical_points':len(pairs)==9 and all(p['identical_complete_point'] for p in pairs),
            'presolve_diagnostic':json.loads((root/'PRESOLVE_DIAGNOSTIC.json').read_text()),
            'scope':'bounded discovery pilots; no original MILP optimality certificates; no manuscript changes'}
    assert result['all_nine_pairs_have_identical_points']
    (HERE/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'optimization_calls':sum(runs.values()),'summary_rows':len(summaries),
                      'identical_point_pairs':len(pairs),'maximum_work_ratio':max(p['work_ratio_integer_to_continuous'] for p in pairs)},indent=2))


if __name__=='__main__':main()
