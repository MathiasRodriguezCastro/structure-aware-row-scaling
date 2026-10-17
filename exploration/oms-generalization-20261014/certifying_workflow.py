#!/usr/bin/env python3
"""Finite solve/check/retry/abstain prototype; acceptance certifies primal budgets.

The callback may invoke a solver or replay an archived attempt. No solver status
is accepted as a feasibility or optimality certificate. Return the checked,
integer-rounded assignment rather than the unverified raw point.
"""
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
from generalization_study import HERE, sha, dump, verify_point


def decision_loop(model, policies, solve_attempt):
    events=[]
    for policy in policies:
        try:
            attempt=solve_attempt(policy)
            if attempt.get('import_matches_original_exactly') is not True:
                events.append({'policy':policy,'state':'no_verified_import','outcome':attempt.get('outcome')})
                continue
            point=attempt.get('point')
            if point is None:
                events.append({'policy':policy,'state':'no_candidate_point','outcome':attempt.get('outcome')})
                continue
            verification=verify_point(model,point)
            if not verification['primal_accepted']:
                events.append({'policy':policy,'state':'primal_check_failed',
                    'maximum_budget_ratio':verification['integer_rounded']['maximum_row_budget_ratio']})
                continue
            returned=[float(round(float(x))) if v['integer'] else float(x)
                      for x,v in zip(point,model['variables'])]
            domain_failure=any(v['integer'] and (
                v['lower'] is not None and Fraction.from_float(x)<Fraction.from_float(v['lower']) or
                v['upper'] is not None and Fraction.from_float(x)>Fraction.from_float(v['upper']))
                for x,v in zip(returned,model['variables']))
            if domain_failure:
                events.append({'policy':policy,'state':'exact_integer_domain_failed'})
                continue
            assert verify_point(model,returned)['primal_accepted']
            exact_objective=sum((Fraction.from_float(v['cost'])*Fraction.from_float(x)
                                 for v,x in zip(model['variables'],returned)),Fraction(0))
            events.append({'policy':policy,'state':'primal_budget_verified'})
            return {'state':'primal_budget_verified','selected_policy':policy,'point':returned,
                'objective':float(exact_objective),'exact_objective':str(exact_objective),
                'optimality_status':'unverified','attempts':events,
                'certificate_scope':'original binary64 row and bound numerical budgets; exact integer assignment'}
        except (AssertionError,ValueError,TypeError,KeyError) as error:
            events.append({'policy':policy,'state':'verification_or_candidate_error',
                           'error_type':type(error).__name__,'error':str(error)})
    return {'state':'abstained','point':None,'optimality_status':'unverified','attempts':events}


def replay():
    design=json.loads((HERE/'pilot/design.json').read_text())
    folder=HERE/'workflow-replay';folder.mkdir(exist_ok=True)
    summaries=[]
    for item in design['models']:
        model_path=HERE/'pilot/models'/item['name']/'original-model.json'
        model=json.loads(model_path.read_text())
        for solver in design['solvers']:
            policies=['Base','Dyadic-L2','Budget-dyadic-L2','Dyadic-L2-tight']
            if solver=='gurobi':policies.append('Dyadic-L2-NumericFocus3')
            def callback(policy):
                run_dir=HERE/'pilot/runs'/item['name']/f'{solver}-{policy}'
                run=json.loads((run_dir/'run.json').read_text())
                if run['has_point']:
                    with np.load(run_dir/'solution.npz',allow_pickle=False) as saved:
                        run['point']=saved['x'].tolist()
                return run
            result=decision_loop(model,policies,callback)
            destination=folder/f'{item["name"]}-{solver}.json'
            result.update(model=item['name'],solver=solver,original_model_sha256=sha(model_path),
                          execution_kind='replay of fixed-arm pilot; not a prospective adaptive experiment')
            dump(destination,result)
            summaries.append({'model':item['name'],'solver':solver,'state':result['state'],
                'selected_policy':result.get('selected_policy'),'attempts':len(result['attempts'])})
    dump(folder/'summary.json',{'results':summaries,'optimizer_calls':0,
        'scope':'checked primal acceptance and abstention; no global optimality certificates'})
    print('Decision loop replayed',len(summaries),'model/solver pairs')


if __name__=='__main__':replay()
