#!/usr/bin/env python3
"""Compare loader environments on saved inputs; never run a benchmark MIP."""
import argparse
import ctypes
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

from runner import HERE, ROOT, library, load, save, sha


def main(label):
    report = dict(label=label, hostname=os.uname().nodename,
                  slurm_job=os.environ.get('SLURM_JOB_ID'), benchmark_MIP_calls=0,
                  technical_license_LP_calls=0, LD_PRELOAD=os.environ.get('LD_PRELOAD'),
                  LD_LIBRARY_PATH=os.environ.get('LD_LIBRARY_PATH'),
                  OPENBLAS_CORETYPE=os.environ.get('OPENBLAS_CORETYPE'),
                  exports=[], stages=[])
    follow = library(ROOT / 'exploration/orf-v15-verified-20261019/study.py',
                     'export_runtime_probe_helpers')
    a, front = follow.old.modules()
    metadata = load(HERE / 'MODEL_PREPARATION.json')['models']
    output = HERE / 'export-runtime-diagnosis' / label
    output.mkdir(parents=True, exist_ok=False)
    examples = [('completo-v1_completo_000119-h024', 'a1_restriccion_varphi1_1(1)'),
                ('sgtm-v1_sgtm_000154-h168', 'a1_cota_altura_7(1)')]
    for name, row_name in examples:
        base = HERE / 'models' / name / 'Base.lp'
        assert sha(base) == metadata[name]['base_sha256']
        rows, _ = a.original_rows(base)
        _, lp, _ = a.campaign.afb.read_lp(base)
        nz = np.abs(np.array(list(rows[row_name]['terms'].values()), dtype=float))
        nz = nz[nz != 0]
        hi = float(nz.max())
        norm = float(np.linalg.norm(nz / hi))
        target = -math.log(hi) - math.log(norm)
        report['stages'].append(dict(instance=name, row=row_name,
            coefficients=[v.hex() for v in nz],
            binary64={k: v.hex() for k, v in dict(hi=hi, norm=norm,
                log_hi=math.log(hi), log_norm=math.log(norm), target=target,
                exp=math.exp(target)).items()}))
        for policy, budget in [('L2', None), ('Budget-L2', 100)]:
            factors, selection = front.choose(rows, lp, budget)
            assert not selection['incompatible_count']
            dest = output / (name + '-' + policy + '.lp')
            a.export_scaled(base, dest, factors)
            expected = metadata[name]['policies'][policy]['export_sha256']
            report['exports'].append(dict(instance=name, policy=policy,
                expected_sha256=expected, actual_sha256=sha(dest),
                byte_identical=sha(dest) == expected))
    if label == 'late-global':
        ctypes.CDLL(str(Path.home() / 'row-scaling-orf-extension-20261019/native-cplex-2212/libcplex2212.so'),
                    mode=ctypes.RTLD_GLOBAL)
    try:
        import cplex
        with cplex.Cplex() as model:
            for setter in [model.set_log_stream, model.set_results_stream,
                           model.set_warning_stream, model.set_error_stream]:
                setter(None)
            model.parameters.threads.set(1)
            model.parameters.timelimit.set(10)
            model.variables.add(obj=[1.] * 2501, lb=[0.] * 2501, ub=[1.] * 2501)
            model.objective.set_sense(model.objective.sense.maximize)
            report['technical_license_LP_calls'] += 1
            model.solve()
            report['cplex'] = dict(version=model.get_version(),
                passed=model.solution.is_primal_feasible() and model.solution.get_objective_value() == 2501.)
    except Exception as error:
        report['cplex'] = dict(passed=False, error=type(error).__name__ + ': ' + str(error))
    report['all_exports_byte_identical'] = all(r['byte_identical'] for r in report['exports'])
    save(HERE / ('EXPORT_RUNTIME-' + label + '.json'), report)
    print(label, 'identical exports', sum(r['byte_identical'] for r in report['exports']),
          '/', len(report['exports']), 'CPLEX full-size LP', report['cplex']['passed'], flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Integrity assertions require execution without -O.')
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    main(parser.parse_args().label)
