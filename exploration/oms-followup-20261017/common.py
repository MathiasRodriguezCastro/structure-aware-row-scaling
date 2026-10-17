"""Fixed follow-up utilities; never modify the archived study implementations."""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FRONT=ROOT/'exploration/oms-frontier-20261016'
OLD=ROOT/'exploration/oms-followup-20261014'
sys.path[:0]=[str(OLD),str(ROOT/'scripts/research'),str(ROOT/'scripts')]
F=Fraction.from_float
INSTANCES=['instance001','instance005','instance022','instance027','instance031','instance046']

def load(p):return json.loads(Path(p).read_text())
def dump(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def exact_witness(out,model,solution,limit=10):
    import exact_dispatch_witness as e
    start=time.perf_counter();e.prepare(out,model,solution)
    settings=out/'exact.set'
    settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = '+str(limit)+'\n')
    binary=OLD/'tools/soplex-build/bin/soplex'
    command=[str(binary),'--loadset='+str(settings),'-X='+str(out/'rational-solution.txt'),str(out/'fixed-original-binary64.lp')]
    with (out/'soplex.log').open('w') as log:
        p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=limit+20)
    dump(out/'solver-provenance.json',{'command':command,'returncode':p.returncode,'binary_sha256':sha(binary),
        'fixed_lp_sha256':sha(out/'fixed-original-binary64.lp'),'settings_sha256':sha(settings)})
    assert p.returncode==0
    e.check(out)
    return {'folder':str(out.relative_to(ROOT)),'certificate':load(out/'independent-certificate.json'),
        'seconds':time.perf_counter()-start,'lp_calls':1}

def choose(parsed,lp,budget,gamma=1e-9,details=False):
    import activation_study as a
    integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    boxes={n:max(abs(float(l)),abs(float(u))) for n,l,u in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
    factors={};blocked=[];records=[];reserves=[];active=0
    for name,row in parsed.items():
        spec=a.campaign.physical_spec(name,row['terms'])
        act=a.activation_spec(name,row)
        unit=spec[1] if spec else 'm3' if act else None
        conversion=spec[2] if spec else 1.
        delta=((.01 if unit=='MW' else budget)*conversion) if budget is not None and unit else 1e100
        e=F(gamma)*sum((F(abs(float(v))) for n,v in row['terms'].items() if n in integers),Fraction(0)) if unit and budget is not None else Fraction(0)
        rho=F(2.**-52)*(sum((F(abs(float(v)))*F(boxes[n]) for n,v in row['terms'].items()),Fraction(0))+F(abs(float(row['rhs'])))) if act and budget is not None else Fraction(0)
        reserve=float(e+rho)
        if F(reserve)<e+rho:reserve=math.nextafter(reserve,math.inf)
        decision=a.select_factor(list(row['terms'].values()),delta,kernel='l2',rounding_allowance=reserve)
        if decision.factor is None:blocked.append({'row':name,'reason':decision.reason,'delta':delta,'reserve':reserve})
        else:factors[name]=decision.factor
        active+=decision.reason=='projected'
        if act:reserves.append(float(e))
        if details and unit:
            records.append({'row':name,'unit':unit,'activation':bool(act),'delta':delta,'integer_reserve':float(e),
                'export_reserve':float(rho),'contract_reserve':reserve,'factor':decision.factor,'reason':decision.reason})
    return factors,{'incompatible':blocked,'incompatible_count':len(blocked),'projected_rows':active,
        'max_integer_rounding_reserve_m3':max(reserves,default=0.)},records
