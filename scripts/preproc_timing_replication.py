#!/usr/bin/env python3
"""Replicated, order-randomized timing of the preprocessing call alone.

The direct SA-Flat batches timed each preprocessing call exactly once, in the
batch's fixed execution order.  Because the end-to-end (preprocessing-plus-solver)
margin in the fast classes is dominated by that call, a single unrandomized
measurement cannot separate the policy effect from systematic order effects
(cache warming, allocator state, branch prediction, machine state).

This harness re-times the preprocessing call ONLY -- the MIP is never solved --
so it is cheap enough to replicate.  For every instance and every kernel
contrast it runs R repetitions; within each repetition the order of the two
policies is drawn from a seeded RNG, and each call runs in a FRESH process, so
no repetition inherits warmed state from its counterpart.  The per-instance
statistic is the median over repetitions.

Usage:
    python3 scripts/preproc_timing_replication.py --reps 20 --workers 8 \
        --out results-revision/preproc-timing/replicated.csv
"""
import argparse
import concurrent.futures
import csv
import os
import random
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validar_preprocesamiento import clean_instance_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PREPROC_RE = re.compile(r"\[PREPROC TIME\] variante=(\S+)\s+tiempo_s=([0-9.eE+\-]+)")

# Kernel-matched contrasts: (label, selective flags, role-blind flags)
CONTRASTS = [
    ('Augmented', '--local-estructurado', '--local-estructurado --plano'),
    ('Matrix-only', '--local-matricial', '--local-matricial --plano'),
]

CLASSES = [
    ('Simple', 'entrada-modelo-simple'),
    ('SG-Ter-Mer', 'entrada-SG-Ter-Mer'),
    ('Full', 'entrada-modelo-completo'),
]


def run_once(exe, instance_text, flags, timeout_s=120.0):
    """One fresh-process preprocessing call; returns measured seconds or None."""
    script = (
        f"{instance_text}\n\n"
        "configurarSolver --Gurobi --timeout 3600 --mipgap 0.001\n"
        f"preprocesar {flags}\n"
        "salir\n"
    )
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as fh:
        fh.write(script)
        path = fh.name
    try:
        with open(path) as stdin:
            proc = subprocess.run(
                [str(exe)], stdin=stdin, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=timeout_s, text=True)
        match = PREPROC_RE.search(proc.stdout)
        return float(match.group(2)) if match else None
    except (subprocess.TimeoutExpired, ValueError):
        return None
    finally:
        os.unlink(path)


def measure_instance(args):
    exe, class_name, instance_path, reps, seed = args
    instance_text = clean_instance_text(Path(instance_path))
    rng = random.Random(seed)
    rows = []
    for kernel, sa_flags, flat_flags in CONTRASTS:
        samples = {'SA': [], 'Flat': []}
        for _ in range(reps):
            # Randomized within-repetition order: neither policy is always first.
            order = [('SA', sa_flags), ('Flat', flat_flags)]
            if rng.random() < 0.5:
                order.reverse()
            for policy, flags in order:
                value = run_once(exe, instance_text, flags)
                if value is not None:
                    samples[policy].append(value)
        if not samples['SA'] or not samples['Flat']:
            continue
        median_sa = statistics.median(samples['SA'])
        median_flat = statistics.median(samples['Flat'])
        rows.append({
            'class': class_name,
            'instance': Path(instance_path).name,
            'kernel': kernel,
            'reps_sa': len(samples['SA']),
            'reps_flat': len(samples['Flat']),
            'median_sa_s': f'{median_sa:.6f}',
            'median_flat_s': f'{median_flat:.6f}',
            'median_diff_s': f'{median_sa - median_flat:.6f}',
            'min_sa_s': f'{min(samples["SA"]):.6f}',
            'min_flat_s': f'{min(samples["Flat"]):.6f}',
            'cv_sa': f'{statistics.pstdev(samples["SA"]) / median_sa:.4f}'
                     if median_sa > 0 else '',
            'cv_flat': f'{statistics.pstdev(samples["Flat"]) / median_flat:.4f}'
                       if median_flat > 0 else '',
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', default=str(ROOT / 'code' / 'build' / 'SistemaElectrico'))
    parser.add_argument('--reps', type=int, default=20)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--seed', type=int, default=20260720)
    parser.add_argument('--classes', nargs='*', default=[c[0] for c in CLASSES])
    parser.add_argument('--out', default=str(
        ROOT / 'results-revision' / 'preproc-timing' / 'replicated.csv'))
    args = parser.parse_args()

    jobs = []
    seed_counter = args.seed
    for class_name, folder in CLASSES:
        if class_name not in args.classes:
            continue
        for instance in sorted((ROOT / 'data' / 'entradas' / folder).glob('*.txt')):
            jobs.append((args.exe, class_name, str(instance), args.reps, seed_counter))
            seed_counter += 1

    print(f'{len(jobs)} instances x {len(CONTRASTS)} contrasts x {args.reps} reps '
          f'x 2 policies = {len(jobs) * len(CONTRASTS) * args.reps * 2} calls',
          file=sys.stderr, flush=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for done, rows in enumerate(pool.map(measure_instance, jobs), 1):
            all_rows.extend(rows)
            if done % 20 == 0:
                print(f'  {done}/{len(jobs)} instances done',
                      file=sys.stderr, flush=True)

    fields = ['class', 'instance', 'kernel', 'reps_sa', 'reps_flat',
              'median_sa_s', 'median_flat_s', 'median_diff_s',
              'min_sa_s', 'min_flat_s', 'cv_sa', 'cv_flat']
    with open(out_path, 'w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f'wrote {len(all_rows)} rows to {out_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
