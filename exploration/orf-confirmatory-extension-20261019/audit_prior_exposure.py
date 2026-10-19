#!/usr/bin/env python3
"""Separate exact input reuse from documented prior noncontract policy exposure."""
from collections import defaultdict
import csv
import hashlib
from runner import ROOT,HERE,load,save,sha
from validar_preprocesamiento import clean_instance_text


def cleaned_hash(path):
    text='\n'.join(' '.join(line.split()) for line in clean_instance_text(path).splitlines() if line.strip())
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    previous=defaultdict(list)
    for p in (ROOT/'exploration').rglob('input.txt'):
        if HERE not in p.parents:previous[cleaned_hash(p)].append(str(p.relative_to(ROOT)))
    models=load(HERE/'MODEL_PREPARATION.json')['models'];collisions=[]
    for name in models:
        old=previous.get(cleaned_hash(HERE/'models'/name/'input.txt'))
        if old:collisions.append(dict(instance=name,previous_inputs=sorted(old)))
    save(HERE/'HELD_OUT_AUDIT.json',dict(status='passed' if not collisions else 'failed_holdout_overlap',
        previous_input_files_checked=sum(map(len,previous.values())),prepared_inputs_checked=len(models),
        criterion='Canonical cleaned command text, blank lines removed and whitespace collapsed; shared historical components remain acknowledged.',
        exact_cleaned_input_collisions=collisions,solver_outcomes_used=False,benchmark_calls_started=0))
    assert not collisions
    path=ROOT/'results-revision/solver-robustness/analysis/runs.csv';index=defaultdict(list)
    for row in csv.DictReader(path.open()):
        index[row['instance_sha256']].append({k:row[k] for k in
            ['run_id','instance','policy','solver','gap','seed','threads']})
    records=[]
    for p in load(HERE/'SOURCE_AUDIT.json')['selected_parents']:
        prior=index.get(p['sha256'],[])
        records.append(dict(parent_id=p['parent_id'],role=p['role'],family=p['family'],input_sha256=p['sha256'],
            historical_recorded_assignments=len(prior),historical_policies=sorted({v['policy'] for v in prior}),
            nonBase_exposure=any(v['policy']!='Base' for v in prior),
            historical_run_identifiers=[v['run_id'] for v in prior]))
    save(HERE/'PRIOR_POLICY_EXPOSURE.json',dict(status='exposure_recorded_no_reselection',
        prior_campaign='solver-robustness-v1',previous_source_table=str(path.relative_to(ROOT)),
        previous_source_sha256=sha(path),source_table_is_partial_snapshot=True,
        recorded_historical_rows=sum(map(len,index.values())),
        selected_parents_with_recorded_nonBase_exposure=sum(r['nonBase_exposure'] for r in records),
        missing_record_is_not_proof_of_no_exposure=True,parents=records,selection_unchanged=True,
        new_budget_policy_outcomes_used_for_selection=False,
        limitation='This bank was exposed to earlier noncontract scaling experiments. This study cannot be described as data wholly unseen by scaling research; new contracts, horizons and numerical settings are registered before these runs.'))
    print('No exact cleaned-input collisions with archived explorations;',
        sum(r['nonBase_exposure'] for r in records),'of 48 parents have documented prior nonBase exposure.')


if __name__=='__main__':main()
