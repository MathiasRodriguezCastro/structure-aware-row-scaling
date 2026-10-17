#!/usr/bin/env python3
"""Reconcile both independent stress audits against the three-solver assignment."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'results-revision/research-audit'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    records=[];solvers=[];models=None
    for name in ('budget-final','budget-final-cplex'):
        folder=AUDIT/name
        protocol=json.loads((folder/'protocol.json').read_text())
        verified=json.loads((folder/'verification.json').read_text())
        assert verified['checker_sha256']==sha(ROOT/'scripts/research/verify_saved_experiment.py')
        assert verified['runs_sha256']==sha(folder/'runs.csv')
        current={p.name:sha(p) for p in (folder/'models').glob('*.npz')}
        assert len(current)==96
        if models is None:models=current
        else:assert current==models,'CPLEX must use identical original models'
        assert verified['configurations_audited']==1728*len(protocol['solvers'])
        assert verified['abstentions_verified']==144*len(protocol['solvers'])
        assert verified['exact_dyadic_exports_checked']==384*len(protocol['solvers'])
        solvers+=protocol['solvers']
        records.append({'root':str(folder.relative_to(ROOT)),'solvers':protocol['solvers'],**verified})
    assert sorted(solvers)==['cplex','gurobi','highs']
    total=sum(r['configurations_audited'] for r in records)
    abstain=sum(r['abstentions_verified'] for r in records)
    result={'unique_shared_models':96,'solvers':solvers,'planned_configurations_checked':total,
        'abstentions_checked':abstain,'actual_optimizer_calls_in_saved_campaign':total-abstain,
        'exact_dyadic_exports_checked':sum(r['exact_dyadic_exports_checked'] for r in records),
        'cplex_models_byte_identical':True,'audits':records,'new_optimizer_calls':0}
    assert (total,abstain,total-abstain,result['exact_dyadic_exports_checked'])==(5184,432,4752,1152)
    (ROOT/'paper/validation/oms-stress-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
