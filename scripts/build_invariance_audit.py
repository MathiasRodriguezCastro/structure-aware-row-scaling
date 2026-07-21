#!/usr/bin/env python3
"""Byte-level invariance audit of the exported model across compiler builds.

The cached-metadata sensitivity splices preprocessing times measured with the
release build onto solver times recorded with the diagnostic build.  That is
legitimate only if compiler optimization changes the COST of preprocessing and
not the TRANSFORMATION it produces.  This script checks that directly: for every
instance, kernel and coverage policy it exports the preprocessed model with both
builds (``preprocesar`` followed by ``grabar``, never solving the MIP) and
compares the two files byte for byte.

Usage:
    python3 scripts/build_invariance_audit.py \
        --diag code/build_diag/SistemaElectrico \
        --release code/build_release/SistemaElectrico \
        --workers 8 --out results-revision/preproc-timing/build_invariance.csv
"""
import argparse
import concurrent.futures
import csv
import filecmp
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validar_preprocesamiento import clean_instance_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# (kernel, policy, preprocessing flags)
VARIANTS = [
    ('Augmented', 'selective', '--local-estructurado'),
    ('Augmented', 'role-blind', '--local-estructurado --plano'),
    ('Matrix-only', 'selective', '--local-matricial'),
    ('Matrix-only', 'role-blind', '--local-matricial --plano'),
]

CLASSES = [
    ('Simple', 'entrada-modelo-simple'),
    ('SG-Ter-Mer', 'entrada-SG-Ter-Mer'),
    ('Full', 'entrada-modelo-completo'),
]


def export_once(exe, instance_text, flags, target, timeout_s=300.0):
    """Preprocess and export the model; returns True if the file was written."""
    script = (
        f"{instance_text}\n\n"
        "configurarSolver --Gurobi --timeout 3600 --mipgap 0.001\n"
        f"preprocesar {flags}\n"
        f"grabar {target}\n"
        "salir\n"
    )
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as fh:
        fh.write(script)
        script_path = fh.name
    try:
        with open(script_path) as stdin:
            subprocess.run([str(exe)], stdin=stdin, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=timeout_s)
        return os.path.exists(target) and os.path.getsize(target) > 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.unlink(script_path)


def compare_one(args):
    diag_exe, release_exe, class_name, instance_path = args
    instance_text = clean_instance_text(Path(instance_path))
    rows = []
    workdir = tempfile.mkdtemp(prefix='inv_')
    try:
        for kernel, policy, flags in VARIANTS:
            a = os.path.join(workdir, 'diag.lp')
            b = os.path.join(workdir, 'release.lp')
            for path in (a, b):
                if os.path.exists(path):
                    os.unlink(path)
            ok_a = export_once(diag_exe, instance_text, flags, a)
            ok_b = export_once(release_exe, instance_text, flags, b)
            if not (ok_a and ok_b):
                verdict = 'missing-export'
            else:
                verdict = 'identical' if filecmp.cmp(a, b, shallow=False) else 'DIFFERENT'
            rows.append({
                'class': class_name,
                'instance': Path(instance_path).name,
                'kernel': kernel,
                'policy': policy,
                'result': verdict,
                'bytes': os.path.getsize(a) if ok_a else 0,
            })
    finally:
        for name in os.listdir(workdir):
            os.unlink(os.path.join(workdir, name))
        os.rmdir(workdir)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--diag', default=str(ROOT / 'code' / 'build_diag' / 'SistemaElectrico'))
    ap.add_argument('--release', default=str(ROOT / 'code' / 'build_release' / 'SistemaElectrico'))
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--classes', nargs='*', default=[c[0] for c in CLASSES])
    ap.add_argument('--out', default=str(
        ROOT / 'results-revision' / 'preproc-timing' / 'build_invariance.csv'))
    args = ap.parse_args()

    jobs = []
    for class_name, folder in CLASSES:
        if class_name not in args.classes:
            continue
        for instance in sorted((ROOT / 'data' / 'entradas' / folder).glob('*.txt')):
            jobs.append((args.diag, args.release, class_name, str(instance)))

    print(f'{len(jobs)} instances x {len(VARIANTS)} variants x 2 builds = '
          f'{len(jobs) * len(VARIANTS) * 2} exports', file=sys.stderr, flush=True)

    all_rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for done, rows in enumerate(pool.map(compare_one, jobs), 1):
            all_rows.extend(rows)
            if done % 25 == 0:
                print(f'  {done}/{len(jobs)} instances', file=sys.stderr, flush=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='') as fh:
        writer = csv.DictWriter(
            fh, fieldnames=['class', 'instance', 'kernel', 'policy', 'result', 'bytes'])
        writer.writeheader()
        writer.writerows(all_rows)

    counts = {}
    for r in all_rows:
        counts[r['result']] = counts.get(r['result'], 0) + 1
    print(f'wrote {len(all_rows)} comparisons to {out_path}', file=sys.stderr)
    for key in sorted(counts):
        print(f'  {key}: {counts[key]}', file=sys.stderr)


if __name__ == '__main__':
    main()
