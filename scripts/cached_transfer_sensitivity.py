#!/usr/bin/env python3
"""Cached-metadata endpoint under policy-specific hardware-transfer factors.

The cached endpoint splices preprocessing medians measured on the timing
workstation onto solver times measured on ClusterUY, so it is a cross-protocol
counterfactual.  A single common factor lambda rescales both policies equally,
which assumes the hardware change is a common multiplier.  That assumption is
not guaranteed: the selective and role-blind rules execute different code, so
we additionally sweep the RATIO rho = lambda_SA / lambda_Flat:

    T_SA   = T_solver,SA   + lambda_SA   * T^cached_preproc,SA
    T_Flat = T_solver,Flat + lambda_Flat * T^cached_preproc,Flat

The grid is finite and explicit; results are reported per contrast.
"""
import argparse, csv, collections, math, statistics
from scipy.stats import wilcoxon, rankdata

TMAX = 3600.0
KER = {'Augmented': ('estructurado', 'estructurado_plano'),
       'Matrix-only': ('estructurado_matricial', 'matricial_plano')}
SCEN = [('1%', {'Simple': 'simple-gurobi-1pct', 'SG-Ter-Mer': 'sgtm-gurobi-1pct',
                'Full': 'full-gurobi-1pct'}),
        ('0.1%', {'Simple': 'simple-gurobi-01pct', 'SG-Ter-Mer': 'sgtm-gurobi-01pct',
                  'Full': 'full-gurobi-01pct'})]


def num(row, key):
    try:
        v = float(row[key])
        return v if math.isfinite(v) else None
    except (KeyError, TypeError, ValueError):
        return None


def status(row):
    if not row:
        return 'abort'
    if row.get('status_solver') == 'TIME_LIMIT':
        return 'timeout'
    if (row.get('rc') == '0' and row.get('status') != 'ERROR'
            and row.get('status_solver') == 'OPTIMAL'
            and num(row, 'tiempo_solver_s') is not None):
        return 'ok'
    return 'abort'


def bh(pvals):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    out = [0.0] * n
    running = 1.0
    for rank, i in reversed(list(enumerate(order, 1))):
        running = min(running, pvals[i] * n / rank)
        out[i] = running
    return out


def rank_biserial(d):
    nz = [x for x in d if x != 0.0]
    rk = rankdata([abs(x) for x in nz])
    return (sum(r for r, x in zip(rk, nz) if x > 0)
            - sum(r for r, x in zip(rk, nz) if x < 0)) / sum(rk)


def contrasts(cached, lam_sa, lam_flat, root='.'):
    res, med, eff, ns = {}, {}, {}, {}
    for gap, batches in SCEN:
        for cls, folder in batches.items():
            path = f'{root}/results-revision/plano-control/{folder}/resumen.csv'
            by = collections.defaultdict(dict)
            for r in csv.DictReader(open(path)):
                by[r['instancia']][r['variante']] = r
            for kern, (sa, fl) in KER.items():
                d = []
                for inst, cells in by.items():
                    a, b = cells.get(sa), cells.get(fl)
                    if not a or not b:
                        continue
                    sa_st, fl_st = status(a), status(b)
                    if sa_st != 'ok' and fl_st != 'ok':
                        continue
                    key = (cls, kern, inst)
                    if key not in cached:
                        continue
                    c_sa, c_fl = cached[key]
                    t_sa = (num(a, 'tiempo_solver_s') if sa_st == 'ok' else TMAX) + lam_sa * c_sa
                    t_fl = (num(b, 'tiempo_solver_s') if fl_st == 'ok' else TMAX) + lam_flat * c_fl
                    if t_sa > 0 and t_fl > 0:
                        d.append(math.log(t_fl / t_sa))
                if len(d) < 5:
                    continue
                k = (gap, cls, kern)
                res[k] = wilcoxon(d, alternative='two-sided')[1]
                med[k] = math.exp(-statistics.median(d))
                eff[k] = rank_biserial(d)
                ns[k] = len(d)
    q6 = {}
    for gap in ('1%', '0.1%'):
        ks = [k for k in res if k[0] == gap]
        for k, q in zip(ks, bh([res[k] for k in ks])):
            q6[k] = q
    ks = list(res)
    q12 = dict(zip(ks, bh([res[k] for k in ks])))
    return res, med, eff, q6, q12, ns


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cached-csv',
                    default='results-revision/preproc-timing/replicated_pinned.csv')
    ap.add_argument('--root', default='.')
    args = ap.parse_args()
    cached = {}
    for r in csv.DictReader(open(args.cached_csv)):
        if r.get('cached_sa_s') and r.get('cached_flat_s'):
            cached[(r['class'], r['kernel'], r['instance'])] = (
                float(r['cached_sa_s']), float(r['cached_flat_s']))

    common = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    print('== Common transfer factor (lambda_SA = lambda_Flat) ==')
    print('lambda  fast-class contrasts with q6<0.05   med SA/Flat (S-Mat 1%, S-Aug .1%, SG-Aug .1%)')
    for lam in common:
        res, med, eff, q6, q12, ns = contrasts(cached, lam, lam, args.root)
        fast = [k for k in q6 if k[1] in ('Simple', 'SG-Ter-Mer')]
        sig = sorted(k for k in fast if q6[k] < 0.05)
        print('%6.2f  %d/8  %-46s %.4f %.4f %.4f' % (
            lam, len(sig), ','.join(f'{k[1][:4]}/{k[2][:3]} {k[0]}' for k in sig),
            med[('1%', 'Simple', 'Matrix-only')], med[('0.1%', 'Simple', 'Augmented')],
            med[('0.1%', 'SG-Ter-Mer', 'Augmented')]))

    print()
    print('== Policy-specific ratio rho = lambda_SA / lambda_Flat (lambda_Flat = 1) ==')
    print('rho     fast-class contrasts with q6<0.05   med SA/Flat (S-Mat 1%, S-Aug .1%, SG-Aug .1%)')
    for rho in (0.25, 0.5, 1.0, 2.0, 4.0):
        res, med, eff, q6, q12, ns = contrasts(cached, rho, 1.0, args.root)
        fast = [k for k in q6 if k[1] in ('Simple', 'SG-Ter-Mer')]
        sig = sorted(k for k in fast if q6[k] < 0.05)
        print('%6.2f  %d/8  %-46s %.4f %.4f %.4f' % (
            rho, len(sig), ','.join(f'{k[1][:4]}/{k[2][:3]} {k[0]}' for k in sig),
            med[('1%', 'Simple', 'Matrix-only')], med[('0.1%', 'Simple', 'Augmented')],
            med[('0.1%', 'SG-Ter-Mer', 'Augmented')]))

    print()
    print('== Per-contrast detail at lambda = 1 ==')
    res, med, eff, q6, q12, ns = contrasts(cached, 1.0, 1.0, args.root)
    for k in sorted(res, key=lambda x: (x[0], x[1], x[2])):
        print('%-4s %-11s %-12s n=%3d med=%.4f r_rb=%+.3f q6=%.4f q12=%.4f'
              % (k[0], k[1], k[2], ns[k], med[k], eff[k], q6[k], q12[k]))


if __name__ == '__main__':
    main()
