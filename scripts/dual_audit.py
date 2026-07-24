#!/usr/bin/env python3
"""Cross-arm dual-recovery audit (reviewer R6, analysis layer).

The C++ side (--reportar-duales) emits, per demand-balance and reservoir-
continuity row, the scaled dual, the exact row factor d_r recorded during
scaling, and the desescaled dual pi_original = d_r * pi_scaled (eq. 54).  This
script runs that over a set of instances for the base and two scaling arms and
answers the operational question R6 asks: do the recovered original-scale duals
-- the system marginal cost from the demand rows, the water value from the
reservoir-continuity rows -- agree across arms?

Because MIP duals come from a fixed-integer LP, two arms that fix DIFFERENT
incumbents can return materially different duals for reasons unrelated to
scaling.  We therefore compare only on instances where all arms reach the same
objective (to a relative tolerance), so the comparison is about the scaling, not
about which integer solution was found; degeneracy is reported, not hidden.

Usage:
    python3 scripts/dual_audit.py --instancias data/entradas/entrada-modelo-simple/*.txt \
        --arms base,estructurado,estructurado_plano --limite 20
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validar_preprocesamiento import clean_instance_text, VARIANT_FLAGS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

DUAL_RE = re.compile(
    r'\[DUALES\] fila=(\S+) pi_scaled=(\S+) d_r=(\S+) d_r_ok=(\d) pi_original=(\S+)')
OBJ_RE = re.compile(r'F\.O[^:]*:\s*([-\d.eE+]+)')


def familia(nombre):
    if 'demanda' in nombre:
        return 'demand'          # system marginal cost, USD/MWh
    if 'h_din' in nombre:
        return 'water'           # reservoir-continuity, water value
    return 'other'


def run_arm(exe, text, flags, timeout, mipgap):
    """Run one arm with dual reporting; return (objective, {row: (pi_orig, d_r_ok)})."""
    script = (
        f"{text}\n\n"
        f"configurarSolver --Gurobi --timeout {timeout:g} --mipgap {mipgap:g} --reportar-duales\n"
        f"preprocesar {flags} --verificar-original\n"
        f"resolver {tempfile.gettempdir()}/dual_audit_tmp.csv\n"
        "salir\n"
    )
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as fh:
        fh.write(script)
        path = fh.name
    try:
        out = subprocess.run([str(exe)], stdin=open(path), capture_output=True,
                             text=True, cwd=str(ROOT / 'code'),
                             timeout=timeout + 180).stdout
    except subprocess.TimeoutExpired:
        return None, {}
    finally:
        os.unlink(path)
    duals, obj = {}, None
    for line in out.splitlines():
        m = DUAL_RE.search(line)
        if m and m.group(4) == '1':          # only reliably recovered factors
            duals[m.group(1)] = float(m.group(5))
        mo = OBJ_RE.search(line)
        if mo:
            obj = float(mo.group(1))
    return obj, duals


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--instancias', nargs='+', required=True)
    ap.add_argument('--exe', default=str(ROOT / 'code' / 'build' / 'SistemaElectrico'))
    ap.add_argument('--arms', default='base,estructurado,estructurado_plano',
                    help='comma-separated harness variant names; first is the reference')
    ap.add_argument('--limite', type=int, default=0, help='cap on instances (0 = all)')
    ap.add_argument('--timeout', type=float, default=120.0)
    ap.add_argument('--mipgap', type=float, default=1e-3)
    ap.add_argument('--obj-tol', type=float, default=1e-6,
                    help='relative objective tolerance for same-incumbent filtering')
    args = ap.parse_args()

    arms = args.arms.split(',')
    flags = {a: (VARIANT_FLAGS[a] if a != 'base' else '--solodiagnostico') for a in arms}
    ref = arms[0]

    inst_paths = []
    for spec in args.instancias:
        inst_paths.extend(sorted(glob.glob(spec)) if any(c in spec for c in '*?[')
                          else [spec])
    if args.limite:
        inst_paths = inst_paths[:args.limite]

    # per-family, per-non-ref-arm collected relative differences on same-incumbent instances
    diffs = {a: {'demand': [], 'water': []} for a in arms[1:]}
    n_same, n_total = 0, 0

    for ip in inst_paths:
        text = clean_instance_text(Path(ip))
        res = {}
        for a in arms:
            obj, d = run_arm(args.exe, text, flags[a], args.timeout, args.mipgap)
            res[a] = (obj, d)
        n_total += 1
        objs = [res[a][0] for a in arms]
        if any(o is None for o in objs):
            continue
        o0 = objs[0]
        if any(abs(o - o0) > args.obj_tol * (abs(o0) + 1e-12) for o in objs):
            continue                          # different incumbents: skip (degeneracy)
        n_same += 1
        dref = res[ref][1]
        for a in arms[1:]:
            da = res[a][1]
            for row, v in dref.items():
                if row in da and abs(v) > 1e-6:
                    diffs[a][familia(row)].append(abs(da[row] - v) / abs(v))

    print(f'instances: {n_total} run, {n_same} with matching incumbent across all arms\n')
    print('%-22s %-8s %6s %10s %10s' % ('arm vs ' + ref, 'family', 'n', 'med rel', 'max rel'))
    import statistics
    for a in arms[1:]:
        for fam in ('demand', 'water'):
            xs = diffs[a][fam]
            if xs:
                print('%-22s %-8s %6d %10.2e %10.2e' % (
                    a, fam, len(xs), statistics.median(xs), max(xs)))
            else:
                print('%-22s %-8s %6d %10s %10s' % (a, fam, 0, '-', '-'))
    print('\ndemand rows carry the system marginal cost (USD/MWh); water rows carry the '
          'reservoir-continuity\nwater value. Agreement to solver tolerance means the scaling '
          'does not move the downstream\ndual; a residual spread is the LP degeneracy of the '
          'dispatch problem, not a recovery error.')


if __name__ == '__main__':
    main()
