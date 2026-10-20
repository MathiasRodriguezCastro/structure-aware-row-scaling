#!/usr/bin/env python3
"""Verify recovered witnesses and their cost ceilings with no third-party package."""
import json
from pathlib import Path
import sys
from verify_reference_witnesses_stdlib import Q, read_model, check_point, digest

HERE = Path(__file__).resolve().parent


def main():
    plan = json.loads((HERE/'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json').read_text())
    report = json.loads((HERE/'REFERENCE_FEASIBILITY_RECOVERY_REPORT.json').read_text())
    assert report['status'] == 'completed' and not report['missing_models']
    assert report['additional_MIP_calls'] == 0
    assert {r['instance'] for r in report['records']} == set(plan['models'])
    rows = []
    for result in report['records']:
        name = result['instance']
        item = dict(instance=name,status=result['status'])
        if result['status'] == 'verified_feasible':
            base = HERE/'models'/name/'Base.lp'
            folder = HERE/result['proof_folder']
            assert folder.resolve().is_relative_to(HERE)
            assert digest(base) == result['original_model_sha256']
            assert digest(folder/'exact-witness.json') == result['witness_sha256']
            certificate = json.loads((folder/'independent-certificate.json').read_text())
            assert certificate['original_model_sha256'] == digest(base)
            assert certificate['witness_sha256'] == result['witness_sha256']
            model = read_model(base)
            point = {n:Q(v) for n,v in json.loads((folder/'exact-witness.json').read_text()).items()}
            objective = check_point(model,point)
            assert objective == Q(certificate['objective_exact_fraction']) == Q(result['objective_exact'])
            assert objective <= Q(result['cost_ceiling_exact'])
            attempt = next(r for r in result['attempts'] if r['status']=='verified_feasible')
            baseline = Q(attempt['baseline_candidate_cost_exact'])
            assert Q(result['cost_ceiling_exact']) == baseline + Q.from_float(.001)*max(Q(1),abs(baseline))
            item.update(base_sha256=digest(base),witness_sha256=digest(folder/'exact-witness.json'),
                rows_checked=len(model[0]),variables_checked=len(model[1]),integers_checked=len(model[3]),
                proof_folder=result['proof_folder'],objective_exact=str(objective),cost_ceiling_passed=True)
        else:
            assert result['status']=='unknown'
        rows.append(item)
    out = dict(status='passed',records=rows,optimizer_calls=0,third_party_packages=0,
        recovered_references=sum(r['status']=='verified_feasible' for r in rows),
        recovery_plan_sha256=digest(HERE/'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json'),
        source_sha256=digest(Path(__file__).resolve()),optimality_certified=False)
    (HERE/'REFERENCE_FEASIBILITY_RECOVERY_REPLAY.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Exact recovery replay:',out['recovered_references'],'accepted references; zero solver calls.')


if __name__=='__main__':
    if sys.flags.optimize:raise RuntimeError('Run without -O for integrity checks.')
    if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
    main()
