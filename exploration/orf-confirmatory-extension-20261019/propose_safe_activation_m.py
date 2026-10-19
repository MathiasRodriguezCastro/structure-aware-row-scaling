#!/usr/bin/env python3
"""Isolated formulation repair; never applied to the frozen benchmark or paper."""
from fractions import Fraction as Q
import re
from runner import HERE,ROOT,load,save,sha,library


def main():
    target=HERE/'proposed-formulation-repair';target.mkdir(exist_ok=False)
    checker=library(ROOT/'exploration/orf-confirmatory-20261018/check.py','safe_m_model_reader')
    independent=library(HERE/'replay_pilot.py','safe_m_point_checker')
    parser=library(HERE/'verify_farkas_bundle.py','safe_m_text_parser')
    name='simple-v1_simple_000127-h168';base=HERE/'models'/name/'Base.lp'
    model=checker.canonical(base);changes={}
    for n,row in model[0].items():
        if not re.fullmatch(r'a1_restriccion_varphi1_[12]\(\d+\)',n):continue
        binary=next(j for j in row['terms'] if j in model[3])
        storage=next(j for j in row['terms'] if j not in model[3])
        assert row['sense']=='<=' and row['terms'][storage]==-1
        threshold=row['terms'][binary]-row['rhs']
        new_m=float(threshold);new_rhs=Q.from_float(new_m)-threshold
        assert Q.from_float(float(new_rhs))==new_rhs,'A threshold-preserving binary64 pair was not found'
        lo=model[1][storage][0]
        assert lo is not None and new_m>0 and threshold-Q.from_float(new_m)<=lo
        changes[n]=dict(binary=binary,storage=storage,threshold_exact=str(threshold),
            old_m=str(row['terms'][binary]),old_rhs=str(row['rhs']),
            new_m=new_m,new_rhs=float(new_rhs),off_branch_redundant=True,
            active_threshold_preserved_exactly=True)
    assert len(changes)==336
    lines=[];mode=False;name_now=None
    for line in base.read_text().splitlines(keepends=True):
        stripped=line.strip()
        if stripped=='s.t.':mode=True
        elif stripped.lower() in ['bounds','binary','binaries','generals','end']:mode=False
        if mode and stripped.endswith(':'):name_now=stripped[:-1]
        if mode and name_now in changes:
            change=changes[name_now];term=parser.TERM.fullmatch(stripped);sense=parser.SENSE.fullmatch(stripped)
            if term and term[2]==change['binary']:
                line=f"  {change['new_m']:+.17g} {change['binary']}\n"
            elif sense:line=f"  {sense[1]} {change['new_rhs']:.17g}\n"
        lines.append(line)
    corrected=target/'proposed-safe-M.lp';corrected.write_text(''.join(lines))
    new=checker.canonical(corrected)
    assert new[1:4]==model[1:4] and new[5]==model[5]
    assert new[0].keys()==model[0].keys()
    for n,row in new[0].items():
        if n not in changes:assert row==model[0][n]
        else:
            c=changes[n];assert row['terms'][c['storage']]==-1
            assert row['terms'][c['binary']]-row['rhs']==Q(c['threshold_exact'])
    source=HERE/'references/simple-v1_simple_000127-h360'
    large=HERE/'models/simple-v1_simple_000127-h360/Base.lp'
    certificate=load(source/'independent-certificate.json')
    assert certificate['original_model_sha256']==sha(large)
    assert certificate['witness_sha256']==sha(source/'exact-witness.json')
    point={n:Q(v) for n,v in load(source/'exact-witness.json').items()}
    assert independent.exact_feasible(checker.canonical(large),point)
    restricted={n:point[n] for n in new[1]}
    assert independent.exact_feasible(new,restricted)
    original_violations=sum(independent.row_violation(row,restricted)>0 for row in model[0].values())
    objective,_=independent.candidate_cost(new,restricted)
    save(target/'changes.json',changes)
    save(target/'exact-witness.json',{n:str(v) for n,v in restricted.items()})
    save(HERE/'PROPOSED_FORMULATION_REPAIR.json',dict(status='verified_separate_proposal',
        original_model_sha256=sha(base),corrected_model_sha256=sha(corrected),modified_rows=len(changes),
        objective_bounds_integer_domains_and_all_other_rows_unchanged=True,
        active_thresholds_preserved_exactly=True,off_branches_redundant_from_existing_bounds=True,
        original_prefix_point_violated_rows=original_violations,corrected_point_row_violations=0,
        exact_bound_and_integrality_violations=0,objective_exact=str(objective),
        witness_sha256=sha(target/'exact-witness.json'),source_360_witness_sha256=certificate['witness_sha256'],
        optimizer_calls=0,original_generator_or_benchmark_changed=False,
        interpretation='This changes the malformed formulation. It is not a row scaling or an equivalent transformation of the original infeasible model.',
        limitation='The threshold-sized M is a safe proposal, not a claim of the smallest M or improved computational performance.'))
    print('Separate proposal verified: 336 activation rows, preserved exact on-thresholds, feasible original-parent prefix; zero optimizer calls.')


if __name__=='__main__':main()
