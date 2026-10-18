"""Native-data structural and factor screen. No optimization or Gurobi imports."""
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tarfile
import zipfile

import numpy as np
from scipy.linalg import svdvals

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/research'))
from budget_scaling import select_factor

POLICIES = ('Base', 'Ruiz-R4', 'Flat-L2', 'Role-Hybrid', 'Coupling-only')
BUDGETS = (1e-3, 1e-5, 1e-7)


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def csvwrite(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def native_models():
    models = []
    with tarfile.open(HERE / 'sources/R.tgz') as archive:
        for cls in range(1, 7):
            name = min(m.name for m in archive.getmembers()
                       if m.isfile() and re.fullmatch(fr'r{cls:02d}\.\d+\.dow', m.name))
            content = archive.extractfile(name).read()
            lines = [s.split() for s in content.decode().splitlines()[1:] if s.strip()]
            n, m, k = map(int, lines[0])
            assert len(lines) == 1 + m + k
            arcs = []
            for line in lines[1:1+m]:
                assert len(line) == 7
                u, v, cost, capacity, fixed, _, _ = map(float, line)
                assert u.is_integer() and v.is_integer() and 1 <= u <= n and 1 <= v <= n
                assert capacity > 0 and cost >= 0 and fixed >= 0 and u != v
                arcs.append(dict(u=int(u)-1, v=int(v)-1, cost=cost,
                                 capacity=capacity, fixed=fixed))
            demands = []
            for line in lines[1+m:]:
                u, v, d = map(float, line)
                assert u.is_integer() and v.is_integer() and 1 <= u <= n and 1 <= v <= n
                assert d > 0 and u != v
                demands.append(dict(u=int(u)-1, v=int(v)-1, amount=d))
            models.append(dict(name=name.removesuffix('.dow'), family='R-fixed-charge',
                nodes=n, arcs=arcs, demands=demands, archive='R.tgz',
                members=[dict(name=name, sha256=digest(content))],
                capacity_model='directed fixed-charge binary design'))
    with tarfile.open(HERE / 'sources/gunluk.tar.gz') as archive:
        for group, prefix in [('at_cep1', 'cep1'), ('nor_sun', 'sun'), ('ny_cep2', 'cep2')]:
            edge_name = f'{group}/{prefix}.edge'
            content = archive.extractfile(edge_name).read()
            lines = [s.split() for s in content.decode().splitlines() if s.strip()]
            m, n, capacity, _, _ = map(int, lines[0])
            assert len(lines) == m+1 and capacity > 1
            arcs = []
            for i, line in enumerate(lines[1:]):
                assert len(line) == 10 and int(line[0]) == i+1
                _, u, v, _, _, _, small_cost, large_cost, cost, existing = map(float, line)
                assert u.is_integer() and v.is_integer() and 1 <= u <= n and 1 <= v <= n
                assert existing >= 0 and min(small_cost, large_cost, cost) >= 0 and u != v
                arcs.append(dict(u=int(u)-1, v=int(v)-1, cost=cost, existing=existing,
                                 small_cost=small_cost, large_cost=large_cost))
            traffic_names = sorted(x.name for x in archive.getmembers() if x.isfile()
                and x.name.startswith(group+'/') and '.traf' in x.name)[:2]
            assert len(traffic_names) == 2
            for name in traffic_names:
                traffic = archive.extractfile(name).read()
                demands = []
                for line in traffic.decode().splitlines()[1:]:
                    if not line.strip():
                        continue
                    u, v, d = map(float, line.split())
                    assert u.is_integer() and v.is_integer() and 1 <= u <= n and 1 <= v <= n
                    assert d >= 0 and u != v
                    # Zero OD demands are retained as zero-demand commodity blocks.
                    demands.append(dict(u=int(u)-1, v=int(v)-1, amount=d))
                assert len({(r['u'],r['v']) for r in demands}) == len(demands)
                models.append(dict(name=name.replace('/', '__'), family='Gunluk-expansion',
                    nodes=n, arcs=arcs, demands=demands, large_capacity=capacity,
                    archive='gunluk.tar.gz', members=[dict(name=edge_name, sha256=digest(content)),
                    dict(name=name, sha256=digest(traffic))],
                    capacity_model='bidirected: each direction bounded by the same installed capacity',
                    formulation_source='https://arxiv.org/html/1711.10147 (sections 1 and 3)'))
    return models


def blocks(model):
    """A=[diag_k(B),0; I,...,I,D]. Identical local incidence per commodity."""
    n, e = model['nodes'], len(model['arcs'])
    expansion = model['family'] == 'Gunluk-expansion'
    q = 2*e if expansion else e
    b = np.zeros((n, q))
    for j, arc in enumerate(model['arcs']):
        b[arc['u'], j] = 1.
        b[arc['v'], j] = -1.
    if expansion:
        b[:, e:] = -b[:, :e]
        small = -np.eye(e)
        d = np.block([[small, model['large_capacity']*small],
                      [small, model['large_capacity']*small]])
    else:
        d = -np.diag([arc['capacity'] for arc in model['arcs']])
    return b, d


def guard(candidate, minimum, maximum):
    if .5 <= candidate <= 2.:
        return 1., 'identity_band'
    if minimum*candidate < 1e-9 or maximum*candidate > 1e9:
        return 1., 'coefficient_veto'
    return candidate, 'applied'


def factor_rows(model, policy, budget=None):
    b, d = blocks(model)
    k = len(model['demands'])
    records = []
    for role, matrix in [('local', b), ('coupling', d)]:
        for i, row in enumerate(matrix):
            a = np.abs(row[row != 0])
            assert len(a)
            coefficients = list(row[row != 0]) if role == 'local' else [1.]*k + list(row[row != 0])
            amin, amax = min(abs(x) for x in coefficients), max(abs(x) for x in coefficients)
            l2 = 1./math.sqrt(math.fsum(x*x for x in coefficients))
            if policy == 'Base' or policy == 'Coupling-only' and role == 'local':
                candidate = 1.
            elif policy == 'Ruiz-R4':
                candidate = amax**(-15/16)
            elif policy == 'Role-Hybrid' and role == 'local':
                candidate = 1./math.sqrt(amin*amax)
            else:
                candidate = l2
            factor, reason = guard(candidate, amin, amax)
            allowance_exact = (sum((Fraction.from_float(float(x)) for x in a), Fraction(0))
                               * Fraction.from_float(1e-9) if role == 'coupling' else Fraction(0))
            allowance = float(allowance_exact)
            if Fraction.from_float(allowance) < allowance_exact:
                allowance = math.nextafter(allowance, math.inf)
            rec = dict(role=role, index=i, candidate=candidate, factor=factor, reason=reason,
                       minimum=amin, maximum=amax, l2_unconstrained=l2,
                       allowance_exact=str(allowance_exact), allowance_outward=allowance)
            if budget is not None:
                decision = select_factor(coefficients, budget, rounding_allowance=allowance, kernel='l2')
                rec.update(lower=decision.lower if math.isfinite(decision.lower) else None,
                           upper=decision.upper, compatible=decision.factor is not None,
                           contract_reason=decision.reason)
                rec['proposed_factor'] = factor
                rec['factor'] = (min(max(factor, decision.lower), decision.upper)
                                 if decision.factor is not None else None)
                rec['modified'] = rec['factor'] is not None and rec['factor'] != factor
                rec['baseline_admissible'] = (decision.factor is not None and
                    decision.lower <= factor <= decision.upper)
            records.append(rec)
    return records


def equivariant_equilibrate(b, c, d, passes):
    """Exactly the declared iterative surrogate on the repeated full matrix."""
    b, c, d = b.copy(), c.copy(), d.copy()
    half = lambda x: np.exp2(-np.round(np.log2(np.where(x > 0, x, 1.))/2.))
    for _ in range(passes):
        rb = half(abs(b).max(axis=1))
        rc = half(np.maximum(abs(c), abs(d).max(axis=1)))
        b *= rb[:, None]
        c *= rc
        d *= rc[:, None]
        cf = half(np.maximum(abs(b).max(axis=0), abs(c)))
        cd = half(abs(d).max(axis=0))
        b *= cf[None, :]
        c *= cf
        d *= cd[None, :]
    return b, c, d


def condition(b, c, d, k):
    """Positive singular values by orthogonal commodity splitting, no local whitening.

    K-1 contrast modes give B. The mean mode gives [B,0;sqrt(K)diag(c),D].
    This is an analysis identity, never a transformation of optimization variables.
    """
    center = np.block([[b, np.zeros((b.shape[0], d.shape[1]))],
                       [math.sqrt(k)*np.diag(c), d]])
    sb, sc = svdvals(b), svdvals(center)
    tol_b = np.finfo(float).eps*max(b.shape)*sb[0]
    tol_c = np.finfo(float).eps*max(center.shape)*sc[0]
    pos_b, pos_c = sb[sb > tol_b], sc[sc > tol_c]
    sigma_max = float(max(pos_b[0], pos_c[0]))
    sigma_min = float(min(pos_b[-1], pos_c[-1]))
    return dict(kappa_positive=sigma_max/sigma_min,
                sigma_max=sigma_max, sigma_min_positive=sigma_min,
                numerical_rank=(k-1)*len(pos_b)+len(pos_c),
                local_rank=len(pos_b), center_rank=len(pos_c),
                reduced_svd_absolute_threshold=float(tol_c))


def sslp_screen():
    result = []
    with zipfile.ZipFile(HERE / 'sources/sslp.zip') as archive:
        for name in sorted(x for x in archive.namelist() if x.endswith('.cor')):
            stem = name[:-4]
            tim = archive.read(stem+'.tim').decode()
            stages = [s.split() for s in tim.splitlines() if 'STAGE-' in s]
            assert len(stages) == 2
            first_second_column = stages[1][0]
            first_second_row = stages[1][1]
            section, row_names, row_columns, columns = None, [], {}, []
            for line in archive.read(name).decode().splitlines():
                t = line.split()
                if not t or line.startswith('*'):
                    continue
                if not line[0].isspace():
                    section = t[0]
                    continue
                if section == 'ROWS' and t[0] != 'N':
                    row_names.append(t[1]); row_columns[t[1]] = set()
                elif section == 'COLUMNS' and "'MARKER'" not in t:
                    if t[0] not in columns:
                        columns.append(t[0])
                    for j in range(1, len(t), 2):
                        if t[j] in row_columns and float(t[j+1]) != 0:
                            row_columns[t[j]].add(t[0])
            boundary = columns.index(first_second_column)
            shared = set(columns[:boundary])
            boundary_row = row_names.index(first_second_row)
            sto = archive.read(stem+'.sto').decode().splitlines()
            scenarios = [s.split() for s in sto if s.split() and s.split()[0] == 'SC']
            assert all(s[2].strip("'\"") == 'ROOT' for s in scenarios)
            assert all(not s.strip() or s.split()[0] in ('STOCH','SCENARIOS','SC','RHS','ENDATA') for s in sto)
            recourse_rows = row_names[boundary_row:]
            assert all(row_columns[r] & (set(columns)-shared) for r in recourse_rows)
            result.append(dict(instance=Path(stem).name, scenarios=len(scenarios),
                first_stage_columns=boundary, recourse_columns_per_scenario=len(columns)-boundary,
                first_stage_rows=boundary_row, recourse_rows_per_scenario=len(recourse_rows),
                shared_first_stage_linking_rows_per_scenario=sum(bool(row_columns[r]&shared) for r in recourse_rows),
                rows_touching_two_distinct_recourse_blocks=0,
                accepted_for_row_coupling_mechanism=False,
                reason='native deterministic equivalent has shared columns, not cross-scenario recourse rows'))
    return result


def main():
    models = native_models()
    assert len(models) == 12
    dump(HERE/'models.json', models)
    summaries, conditions, decisions = [], [], []
    for model in models:
        b, d = blocks(model)
        k, n, q = len(model['demands']), *b.shape
        original = np.r_[np.abs(b[b != 0]), np.ones(k), np.abs(d[d != 0])]
        record = dict(instance=model['name'], family=model['family'], nodes=n,
            commodities=k, local_rows=k*n, coupling_rows=q, variables=k*q+d.shape[1],
            integer_variables=d.shape[1], coefficient_range=float(original.max()/original.min()),
            local_rank=int(np.linalg.matrix_rank(b)), exact_triangular_theorem_applicable=False)
        for policy in POLICIES:
            factors = factor_rows(model, policy)
            local = np.array([r['factor'] for r in factors if r['role'] == 'local'])
            coupling = np.array([r['factor'] for r in factors if r['role'] == 'coupling'])
            record[policy+'_local_changed'] = k*int(sum(local != 1))
            record[policy+'_coupling_changed'] = int(sum(coupling != 1))
            for passes in (0, 10):
                bb, cc, dd = equivariant_equilibrate(local[:,None]*b, coupling, coupling[:,None]*d, passes)
                conditions.append(dict(instance=model['name'], policy=policy, equilibration_passes=passes,
                                       **condition(bb,cc,dd,k)))
        for budget in BUDGETS:
            factors = factor_rows(model, 'Flat-L2', budget)
            for r in factors:
                decisions.append(dict(instance=model['name'], budget=budget,
                                      multiplicity=k if r['role']=='local' else 1, **r))
            for role in ('local','coupling'):
                selected = [r for r in factors if r['role']==role]
                count = k if role == 'local' else 1
                label = f'budget_{budget:g}_{role}'
                record[label+'_modified'] = count*sum(r['modified'] for r in selected)
                record[label+'_incompatible'] = count*sum(not r['compatible'] for r in selected)
            if all(r['factor'] is not None for r in factors):
                local = np.array([r['factor'] for r in factors if r['role']=='local'])
                coupling = np.array([r['factor'] for r in factors if r['role']=='coupling'])
                for passes in (0,10):
                    bb,cc,dd = equivariant_equilibrate(local[:,None]*b,coupling,coupling[:,None]*d,passes)
                    conditions.append(dict(instance=model['name'],policy=f'Budget-L2-{budget:g}',
                        equilibration_passes=passes,**condition(bb,cc,dd,k)))
        summaries.append(record)
        print(model['name'], model['family'], k, record['coefficient_range'],
              'coupling', record['Role-Hybrid_coupling_changed'], '/', q,
              'budget1e-5', record['budget_1e-05_coupling_modified'],
              'incompatible1e-7', record['budget_1e-07_coupling_incompatible'], flush=True)
    csvwrite(HERE/'structure.csv', summaries)
    csvwrite(HERE/'conditioning.csv', conditions)
    csvwrite(HERE/'contracts.csv', decisions)
    csvwrite(HERE/'sslp-screen.csv', sslp_screen())
    dump(HERE/'screen-metadata.json', dict(selection_before_solver=True, optimizer_calls=0,
        protocol_sha256=digest((HERE/'PROTOCOL.md').read_bytes()),
        models_sha256=digest((HERE/'models.json').read_bytes()),
        condition_scope='full original constraint matrix; positive singular values; redundant conservation retained',
        equilibration_scope='declared surrogate, not proprietary internal solver scaling',
        tolerance_scope='conditional exported residual and uniform rounding hypothesis, not an observed solver promise'))


if __name__ == '__main__':
    main()
