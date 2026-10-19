#!/usr/bin/env python3
"""Construct nested horizons from admitted generated parents without optimizing."""
import argparse
from collections import Counter
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'scripts/research'),
             str(ROOT/'exploration/oms-followup-20261014')]
from validar_preprocesamiento import clean_instance_text


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')


def nested(text,horizon):
    """Retain initial state; use unmodified prefixes and a fixed terminal function.

    No change of time units, interpolation, cyclic rotation or mid-window start.
    Full models keep the same mathematical Bellman continuation function; this
    dimension sensitivity is not an operationally recalibrated planning forecast.
    """
    if horizon not in [24,72,168,360]:raise ValueError('unregistered horizon')
    lines=text.splitlines();series=[];local=total=None
    for i,line in enumerate(lines):
        if line.startswith('inicializar '):
            if not re.search(r'--t\s+360\b',line):raise ValueError('parent must have 360 hourly periods')
            lines[i]=re.sub(r'(--t\s+)360\b',lambda m:m[1]+str(horizon),line)
        if line.startswith('agregarAgente --RioNegro'):series.extend([i+1,i+2,i+3])
        if line.startswith('agregarAgente --SaltoGrande'):series.append(i+3)
        if line.startswith('agregarAgente --DemandaFija'):local=i+1;series.append(local)
        if line.startswith('crearDespacho --mercado'):
            if '--conDemandaTotal' not in line:raise ValueError('market input lacks explicit total demand')
            total=i+4;series.append(total)
    if local is None or not series:raise ValueError('missing temporal data')
    vectors={i:[float(x) for x in lines[i].split()] for i in series}
    for i,v in vectors.items():
        if len(v)!=360 or not all(math.isfinite(x) and x>=0 for x in v):
            raise ValueError(f'invalid hourly series at line {i+1}')
    if total is not None and any(a>b for a,b in zip(vectors[local],vectors[total])):
        raise ValueError('local demand exceeds total demand; no automatic correction')
    # Preserve original decimal tokens; no binary64 rewrite of input data.
    for i in series:lines[i]=' '.join(lines[i].split()[:horizon])
    return '\n'.join(lines)+'\n',dict(series=len(series),demand_coherent=True,
        same_initial_state=True,window_start=0,temporal_interpolation=False,
        terminal_function='fixed original continuation function across horizons')


def outside_rows(text):
    parts=[];inside=False
    for line in text.splitlines(keepends=True):
        if line.strip()=='s.t.':inside=True;parts.append(line)
        elif line.strip().lower() in ['bounds','binary','binaries','generals','end']:
            inside=False;parts.append(line)
        elif not inside:parts.append(line)
    return ''.join(parts)


def audit_export(base,export,factors,original,parse):
    assert outside_rows(base.read_text())==outside_rows(export.read_text()),'objective/bounds/domains text changed'
    actual,_=parse(export);assert actual.keys()==original.keys()
    max_relative=Q(0);checks=0
    for name,row in original.items():
        got=actual[name];alpha=Q.from_float(factors[name]);assert alpha>0
        assert got['sense']==row['sense'] and got['terms'].keys()==row['terms'].keys()
        for v,w in [(row['rhs'],got['rhs']),*[(a,got['terms'][j]) for j,a in row['terms'].items()]]:
            a=Q.from_float(float(v));b=Q.from_float(float(w));expected=float(float(v)*factors[name])
            assert Q.from_float(expected)==b,'written product differs from the frozen serializer'
            if a:max_relative=max(max_relative,abs(b-alpha*a)/abs(alpha*a))
            checks+=1
    return dict(positive_row_factors=True,ideal_whole_row_equivalence=True,
        actual_binary64_products_checked=checks,max_relative_product_error=float(max_relative),
        exact_proportionality_asserted=False,objective_bounds_integer_domains_byte_identical=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int)
    ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
    inventory=json.loads((HERE/'REMOTE_INVENTORY.json').read_text())
    frozen=json.loads((HERE/'FROZEN_POLICIES.json').read_text())
    for n,h in frozen['policy_source_sha256'].items():assert sha(ROOT/n)==h,n
    import activation_study as a
    spec=importlib.util.spec_from_file_location('fixed_frontier',ROOT/'exploration/oms-frontier-20261016/study.py')
    front=importlib.util.module_from_spec(spec);spec.loader.exec_module(front)
    summary={};errors=[]
    root=HERE/'models';root.mkdir(exist_ok=True)
    parents=inventory['selected_parents'][:args.limit] if args.limit else inventory['selected_parents']
    if args.smoke:
        parents=[next(p for p in parents if p['family']==f) for f in ['simple','sgtm','completo']]
    for parent in parents:
        source=ROOT/'data/benchmark-v1'/parent['family']/Path(parent['remote_path']).name
        assert source.is_file() and sha(source)==parent['sha256'],'local/remote input identity failed'
        for horizon in [24,72,168,360]:
            name=f"{parent['parent_id']}-h{horizon:03d}";folder=root/name
            if (folder/'metadata.json').exists():
                item=json.loads((folder/'metadata.json').read_text());summary[name]=item;continue
            if folder.exists() and any(folder.iterdir()):
                raise RuntimeError('Unfinished/failed preparation retained; record an amendment before retrying: '+name)
            folder.mkdir(exist_ok=True);started=time.perf_counter()
            try:
                text,temporal=nested(clean_instance_text(source),horizon)
                (folder/'input.txt').write_text(text)
                base=folder/'Base.lp'
                commands=text+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'+f'grabar {base} --noConstante\nsalir\n'
                (folder/'generator-commands.txt').write_text(commands)
                with (folder/'generator.log').open('w') as log:
                    p=subprocess.run([str(ROOT/'code/build-audit/SistemaElectrico')],input=commands,text=True,
                        cwd=ROOT/'code',stdout=log,stderr=subprocess.STDOUT,timeout=120)
                assert p.returncode==0 and base.is_file(),'generator export failed'
                parsed,physical=a.original_rows(base);_,lp,_=a.campaign.afb.read_lp(base)
                nint=sum(str(t)!='HighsVarType.kContinuous' for t in lp.integrality_)
                assert nint>0,'integrality was lost'
                info={};plain=None
                for policy,budget in [('L2',None),('Budget-L2',100)]:
                    factors,decision=front.choose(parsed,lp,budget)
                    write(folder/(policy+'-factors.json'),factors)
                    item=dict(**decision)
                    if plain is None:plain=factors
                    item['changed_from_L2']=sum(f!=plain.get(n) for n,f in factors.items())
                    if not decision['incompatible_count']:
                        export=folder/(policy+'.lp');a.export_scaled(base,export,factors)
                        item['export_sha256']=sha(export)
                        item['equivalence']=audit_export(base,export,factors,parsed,a.parse)
                    info[policy]=item
                item=dict(parent_id=parent['parent_id'],family=parent['family'],role=parent['role'],
                    horizon=horizon,parent_sha256=parent['sha256'],input_sha256=sha(folder/'input.txt'),
                    base_sha256=sha(base),rows=len(parsed),columns=lp.num_col_,integer_columns=nint,
                    physical_rows=len(physical),physical_groups=dict(Counter(r['group'] for r in physical.values())),
                    temporal=temporal,policies=info,preparation_seconds=time.perf_counter()-started,
                    no_optimization_calls=True)
                write(folder/'metadata.json',item);summary[name]=item
                print(name,'prepared; rows',len(parsed),'integers',nint,'changed',info['Budget-L2']['changed_from_L2'],flush=True)
            except Exception as e:
                error=dict(instance=name,error=type(e).__name__+': '+str(e),retained_attempt=True)
                errors.append(error);write(folder/'preparation-error.json',error)
                print(name,error['error'],flush=True)
            write(HERE/'MODEL_PREPARATION.json',dict(status=('complete' if len(summary)==192 else 'partial') if not errors else 'has_failures',
                models=summary,failures=errors,optimization_calls=0,
                total_registered_models=192,
                observed_operational_independence=False,model_population='historical-component recombinations'))
    if errors:raise RuntimeError(f'{len(errors)} preparation failures retained; no pilot may start')


if __name__=='__main__':main()
