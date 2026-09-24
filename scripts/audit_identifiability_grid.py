#!/usr/bin/env python3
"""Fresh, solver-free C++ replication of coverage/kernel/ownership controls.

Archives every LP and its SHA-256, parses row and column names, compares all
coefficients/RHS/objective/bounds/domains, and evaluates spectra at a common rank.
Export-equivalence checks account explicitly for LP decimal serialization.
"""
import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ['Base', 'SA-Mat', 'Flat-GM', 'Flat-L2', 'Role-Hybrid', 'SA-Mat-permB']
SLUG = {v: re.sub('[^A-Za-z0-9]', '', v) for v in VARIANTS}
TERM = re.compile(r'^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s+(\S+)$')
SENSE = re.compile(r'^(<=|>=|=)\s+([+-]?[\d.eE+-]+)$')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(path):
    rows, section, row, other = {}, 'objective', None, []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == 's.t.':
            section = 'rows'; continue
        if line.lower() in ('bounds', 'binaries', 'binary', 'generals', 'end'):
            section = 'other'; other.append(line); continue
        if section != 'rows':
            other.append(line); continue
        if line.endswith(':'):
            name = line[:-1]
            if name in rows:
                raise ValueError(f'duplicate row {name}')
            row = dict(terms={}, sense=None, rhs=None)
            rows[name] = row
        elif match := TERM.fullmatch(line):
            value, name = match.groups()
            row['terms'][name] = row['terms'].get(name, Decimal(0)) + Decimal(value)
        elif match := SENSE.fullmatch(line):
            row['sense'], rhs = match.groups(); row['rhs'] = Decimal(rhs)
        else:
            raise ValueError(f'unparsed LP line in {path}: {line}')
    if not rows or any(v['rhs'] is None for v in rows.values()):
        raise ValueError(f'incomplete rows in {path}')
    return rows, other


def canonical(parsed):
    rows, other = parsed
    data = dict(rows={name: dict(terms={col: str(value.normalize())
                                      for col, value in sorted(row['terms'].items())},
                               rhs=str(row['rhs'].normalize()), sense=row['sense'])
                      for name, row in sorted(rows.items())}, other=other)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def matrix(parsed):
    rows = parsed[0]
    cols = sorted({c for r in rows.values() for c in r['terms']})
    return np.array([[float(rows[r]['terms'].get(c, 0)) for c in cols]
                     for r in sorted(rows)])


def comparison(first, second):
    a, rest_a = first; b, rest_b = second
    names_equal = set(a) == set(b)
    support = names_equal
    senses = names_equal
    exact_coef = exact_rhs = 0
    total_coef = total_rhs = 0
    relmax = rhsmax = 0.0
    for rowname in sorted(set(a) & set(b)):
        ar, br = a[rowname], b[rowname]
        support &= set(ar['terms']) == set(br['terms'])
        senses &= ar['sense'] == br['sense']
        for col in set(ar['terms']) | set(br['terms']):
            av, bv = ar['terms'].get(col, Decimal(0)), br['terms'].get(col, Decimal(0))
            total_coef += 1; exact_coef += av == bv
            den = max(abs(av), abs(bv), Decimal('1e-300'))
            relmax = max(relmax, float(abs(av-bv)/den))
        total_rhs += 1; exact_rhs += ar['rhs'] == br['rhs']
        rhsmax = max(rhsmax, float(abs(ar['rhs']-br['rhs'])))
    return dict(row_names_equal=int(names_equal), support_equal=int(support),
                row_senses_equal=int(senses), other_lp_sections_equal=int(rest_a == rest_b),
                coefficients_equal=exact_coef, coefficients_total=total_coef,
                rhs_equal=exact_rhs, rhs_total=total_rhs,
                coefficient_max_relative_difference=relmax,
                rhs_max_absolute_difference=rhsmax,
                exact_named_model_equal=int(names_equal and support and senses and rest_a == rest_b
                                             and exact_coef == total_coef and exact_rhs == total_rhs))


def row_scaling_audit(base, scaled, roundtrip=False):
    rows, other = base; transformed, transformed_other = scaled
    structural = set(rows) == set(transformed) and other == transformed_other
    coef_pass = rhs_pass = 0
    max_coef_rel = max_rhs_error = max_rhs_allowance_ratio = 0.0
    for name, row in rows.items():
        sr = transformed[name]
        if set(row['terms']) != set(sr['terms']) or row['sense'] != sr['sense']:
            structural = False; continue
        pivot = max(row['terms'], key=lambda c: abs(row['terms'][c]))
        factor = sr['terms'][pivot] / row['terms'][pivot]
        if factor <= 0:
            structural = False; continue
        c_ok = True
        for col, coeff in row['terms'].items():
            discrepancy = abs(sr['terms'][col]-factor*coeff)
            # LP emits coefficients with 17 digits after the decimal point.
            allowance = (Decimal(0) if roundtrip else Decimal('1.02e-17')*(1+abs(factor))) + Decimal('1e-13')*abs(factor*coeff)
            c_ok &= discrepancy <= allowance
            max_coef_rel = max(max_coef_rel, float(discrepancy/max(abs(factor*coeff),Decimal('1e-300'))))
        coef_pass += c_ok
        rhs_error = abs(sr['rhs']-factor*row['rhs'])
        # RHS is emitted with six decimal places in the existing C++ exporter.
        rhs_allowance = (Decimal(0) if roundtrip else Decimal('5.01e-7')*(1+abs(factor))) + Decimal('1e-13')*abs(factor*row['rhs'])
        rhs_pass += rhs_error <= rhs_allowance
        max_rhs_error = max(max_rhs_error, float(rhs_error))
        max_rhs_allowance_ratio = max(max_rhs_allowance_ratio, float(rhs_error/rhs_allowance) if rhs_allowance else (0. if not rhs_error else float('inf')))
    return dict(structure_preserved=int(structural), row_count=len(rows),
                coefficient_rows_pass=coef_pass, rhs_rows_pass=rhs_pass,
                max_coefficient_row_factor_relative_error=max_coef_rel,
                max_rhs_scaling_error=max_rhs_error,
                max_rhs_error_over_serialization_allowance=max_rhs_allowance_ratio,
                row_scaling_with_serialization_verified=int(structural and coef_pass == len(rows)
                                                           and rhs_pass == len(rows)))


def write_csv(path, records):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0].keys())
        writer.writeheader(); writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=ROOT/'code/build/SistemaElectrico')
    parser.add_argument('--out', type=Path, default=ROOT/'results-revision/research-audit/identifiability-confirmatory')
    parser.add_argument('--seeds', type=int, default=10)
    parser.add_argument('--seed-base', type=int, default=20260909)
    parser.add_argument('--roundtrip-export', action='store_true', help='Use relative floating-point checks for corrected max_digits10 exporter')
    args = parser.parse_args()
    args.exe, args.out = args.exe.resolve(), args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), solver='DummyLp',
                    solve_performed=False, executable=str(args.exe), executable_sha256=sha(args.exe),
                    script_sha256=sha(Path(__file__)), variants=VARIANTS, seed_base=args.seed_base,
                    seeds=args.seeds, ranges=[1,2,3], severities=[3,6],
                    patterns=['coupling','coupling_uniform','mixed'],
                    spectral_rank='reference rank from row-L2-normalized Base at relative tolerance 1e-12',
                    rhs_serialization=('max_digits10 round-trip precision' if args.roundtrip_export else 'legacy six decimal places'))
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    all_exports, all_pairs, all_equivalence = [], [], []
    for block_range, severity, pattern in itertools.product([1,2,3],[3,6],['coupling','coupling_uniform','mixed']):
        tag = f'R{block_range}_S{severity}_{pattern}'
        cell = args.out/tag; lpdir = cell/'lp'; lpdir.mkdir(parents=True, exist_ok=True)
        command = (f'benchmarkSintetico --coef-family block_heterogeneous --volcar-lp {lpdir}\n'
                   f'DummyLp\n{args.seed_base}\n{args.seeds}\n4\n6 2\n8 3\n{pattern}\n{severity}\n'
                   f'{",".join(VARIANTS)}\n{cell}/metrics.csv\nsalir\n')
        (cell/'input.txt').write_text(command)
        env = dict(os.environ, SYNTH_BLOCK_RANGE=str(block_range))
        # Ambient perturbation controls must not alter the declared experiment.
        env.pop('SPRE_PERM_INDEX', None)
        result = subprocess.run([str(args.exe)], input=command, text=True, cwd=ROOT/'code',
                                env=env, capture_output=True, timeout=120, check=True)
        (cell/'stdout.log').write_text(result.stdout); (cell/'stderr.log').write_text(result.stderr)
        files = sorted(lpdir.glob('*.lp'))
        if len(files) != args.seeds*len(VARIANTS):
            raise RuntimeError(f'{tag}: expected {args.seeds*len(VARIANTS)} LPs, found {len(files)}')
        for seed in range(args.seed_base, args.seed_base+args.seeds):
            prefix = f'{pattern}_S{severity}_seed{seed}'
            paths = {v: lpdir/f'{prefix}_{SLUG[v]}.lp' for v in VARIANTS}
            parsed = {v: parse(path) for v,path in paths.items()}
            a_base = matrix(parsed['Base'])
            rownorms = np.linalg.norm(a_base,axis=1)
            if np.any(rownorms == 0):
                raise ValueError('unexpected zero base row')
            ref_s = np.linalg.svd(a_base/rownorms[:,None],compute_uv=False)
            reference_rank = int(np.sum(ref_s > ref_s[0]*1e-12))
            labels = dict(block_range=block_range,severity=severity,pattern=pattern,seed=seed)
            for variant in VARIANTS:
                values = np.linalg.svd(matrix(parsed[variant]),compute_uv=False)
                sv_nonzero = values[reference_rank-1]
                all_exports.append(dict(**labels, variant=variant,
                                        file=str(paths[variant].relative_to(args.out)),
                                        sha256=sha(paths[variant]), named_model_sha256=canonical(parsed[variant]),
                                        reference_rank=reference_rank,
                                        variant_relative_rank=int(np.sum(values > values[0]*1e-12)),
                                        sigma_max=float(values[0]),sigma_at_reference_rank=float(sv_nonzero),
                                        kappa2_common_rank=float(values[0]/sv_nonzero)))
                all_equivalence.append(dict(**labels,variant=variant,
                                             **row_scaling_audit(parsed['Base'],parsed[variant],args.roundtrip_export)))
            for first,second in [('SA-Mat','Role-Hybrid'),('SA-Mat','SA-Mat-permB'),
                                  ('SA-Mat','Flat-GM'),('Role-Hybrid','Flat-L2')]:
                all_pairs.append(dict(**labels,first=first,second=second,
                                      byte_equal=int(paths[first].read_bytes()==paths[second].read_bytes()),
                                      **comparison(parsed[first],parsed[second])))
        print(f'{tag}: {len(files)} LPs, named comparisons complete',flush=True)
    write_csv(args.out/'exports.csv',all_exports)
    write_csv(args.out/'named_comparisons.csv',all_pairs)
    write_csv(args.out/'row_scaling_audit.csv',all_equivalence)
    with (args.out/'checksums.sha256').open('w') as stream:
        for row in all_exports:
            stream.write(f"{row['sha256']}  {row['file']}\n")
    for pair in [('SA-Mat','Role-Hybrid'),('SA-Mat','SA-Mat-permB')]:
        records=[r for r in all_pairs if (r['first'],r['second'])==pair]
        print(pair,'byte_equal',sum(r['byte_equal'] for r in records),'/',len(records),
              'named_equal',sum(r['exact_named_model_equal'] for r in records),
              'max_rel',max(r['coefficient_max_relative_difference'] for r in records))
    print('Export-equivalence verified:',sum(r['row_scaling_with_serialization_verified'] for r in all_equivalence),
          '/',len(all_equivalence))


if __name__ == '__main__':
    with localcontext() as context:
        context.prec=60
        main()
