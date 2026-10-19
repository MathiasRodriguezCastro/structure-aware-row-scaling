#!/usr/bin/env python3
"""Independent admission checks on every stored model and representation."""
from collections import Counter
import json
from pathlib import Path
import sys
from runner import HERE,ROOT,load,sha,save


def main():
    sys.path.insert(0,str(ROOT/'scripts/research'))
    from audit_fixed_basis import read_lp
    data=load(HERE/'MODEL_PREPARATION.json');assert data['status']=='complete' and not data['failures']
    assert len(data['models'])==192
    counts=Counter();products=0;active=Counter();parent_roles={};dependencies={}
    for name,m in data['models'].items():
        folder=HERE/'models'/name;h=m['horizon'];family=m['family']
        expected={'simple':(40*h,30*h,6*h),'sgtm':(28*h,17*h,4*h),'completo':(66*h+3,46*h+1,10*h)}[family]
        _,lp,_=read_lp(folder/'Base.lp')
        actual=(lp.num_row_,lp.num_col_,sum(str(t)!='HighsVarType.kContinuous' for t in lp.integrality_))
        assert actual==expected==(m['rows'],m['columns'],m['integer_columns']),name
        for filename,digest in [('Base.lp',m['base_sha256']),('input.txt',m['input_sha256'])]:
            assert sha(folder/filename)==digest,name+'/'+filename
            dependencies[str((folder/filename).relative_to(ROOT))]=digest
        for policy in ['L2','Budget-L2']:
            r=m['policies'][policy]
            if r['incompatible_count']:continue
            assert sha(folder/(policy+'.lp'))==r['export_sha256']
            assert r['equivalence']['objective_bounds_integer_domains_byte_identical']
            assert r['equivalence']['positive_row_factors'] and not r['equivalence']['exact_proportionality_asserted']
            products+=r['equivalence']['actual_binary64_products_checked']
        assert m['temporal']['demand_coherent'] and m['temporal']['same_initial_state']
        assert not m['temporal']['temporal_interpolation'] and m['temporal']['window_start']==0
        active[family]+=m['policies']['Budget-L2']['changed_from_L2']
        counts[family,m['role']]+=1
        parent_roles.setdefault(m['parent_id'],set()).add(m['role'])
    assert all(len(r)==1 for r in parent_roles.values()) and len(parent_roles)==48
    save(HERE/'DATA_GATE.json',dict(status='passed_for_generated_population',models=192,
        pilot_models=32,confirmatory_models=160,disjoint_parents=48,original_integrality_preserved=True,
        independently_rechecked_dimension_sets=True,stored_written_product_checks=products,
        changed_Budget_L2_factors_by_class=dict(active),frozen_model_input_hashes=dependencies,
        new_observed_operational_datasets=0,optimization_calls=0))
    print('Data gate passed: 192 models, 48 disjoint parent IDs, preserved integer domains.')
    print('Written-product checks:',products,'; active contract factors:',dict(active))


if __name__=='__main__':main()
