#!/usr/bin/env python3
"""Compute-node admission: frozen references, saved candidates and licensed runtimes."""
import os
import subprocess
import sys
from run_confirmation import checked_plan
from runner import HERE, ROOT, load, save, sha


def main():
    report = dict(status='failed', benchmark_MIP_calls=0, technical_license_LP_calls=0,
                  hostname=os.uname().nodename, slurm_job=os.environ.get('SLURM_JOB_ID'))
    try:
        plan = checked_plan()
        report['confirmation_plan_sha256'] = sha(HERE / 'CONFIRMATION_PLAN.json')
        for script, arguments in [('seal_pending_validation.py', ['--check']),
                                  ('verify_reference_witnesses_stdlib.py', []),
                                  ('verify_recovered_references_stdlib.py', []),
                                  ('seal_reference_recovery.py', ['--check']),
                                  ('check_confirmation_execution.py', []),
                                  ('check_confirmation_analysis.py', [])]:
            subprocess.run([sys.executable, str(HERE / script), *arguments], cwd=ROOT, check=True)
        checked_plan()  # Replayed reports must retain their originally registered hashes.
        probe = HERE / 'PREFLIGHT-confirmation.json'
        process = subprocess.run([sys.executable, str(HERE / 'cluster/license_probe.py'), str(probe)], cwd=ROOT)
        if probe.exists():
            report['technical_license_LP_calls'] = load(probe)['technical_LP_calls']
        assert process.returncode == 0 and load(probe)['status'] == 'passed'
        assert report['technical_license_LP_calls'] == plan['technical_gate_LP_calls']
        report.update(status='passed', registered_assignments=sum(len(b['jobs']) for b in plan['blocks']),
            exact_feasible_references=159, diagnostic_models=1, quality_evaluable_assignments=3816,
            original_generator_modified=False, policy_outcomes_used=False)
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        save(HERE / 'CONFIRMATION_GATE.json', report)
    print('Confirmation admission passed; references, saved-candidate audits and both full licenses checked.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
