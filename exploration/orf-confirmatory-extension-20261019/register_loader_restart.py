#!/usr/bin/env python3
"""Register a loader-only successor after the complete old attempt is retained."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

from runner import HERE, ROOT, load, save, sha


def main():
    old_sha = 'b960242359f2645cb6b6b9e05558e80c64ff2385b6daae7130a0716cdce85fda'
    assert sha(HERE / 'CONFIRMATION_PLAN.json') == old_sha
    old = load(HERE / 'CONFIRMATION_PLAN.json')
    for name, expected in old['dependencies'].items():
        assert sha(ROOT / name) == expected, name
    evidence = HERE / 'setup-evidence/confirmation-loader-6071906'
    archived = load(evidence / 'ARCHIVE.json')
    assert archived['status'] == 'retained_before_loader_correction'
    assert archived['old_plan_sha256'] == old_sha and archived['pre_optimizer_failures'] == 12
    assert archived['all_original_attempts_retained'] and not archived['policy_rankings_consulted']
    assert sha(evidence / 'ARCHIVE_RAW_MANIFEST.json') == archived['raw_manifest_sha256']
    assert sha(evidence / 'CONFIRMATION_PLAN.json') == old_sha
    gate = load(HERE / 'FACTOR_PORTABILITY-Haswell-library-path-all.json')
    assert gate['status'] == 'passed' and gate['exports_checked'] == gate['byte_identical_exports'] == 384
    assert load(HERE / 'PREFLIGHT-loader-corrected.json')['status'] == 'passed'
    wrapper = HERE / 'cluster/confirmation.slurm'
    previous = wrapper.read_text()
    assert previous == (evidence / 'confirmation.slurm').read_text()
    replacement = 'export SINGULARITYENV_LD_LIBRARY_PATH="$ENV_ROOT/native-cplex-2212"\nunset SINGULARITYENV_LD_PRELOAD'
    line = 'export SINGULARITYENV_LD_PRELOAD="$ENV_ROOT/native-cplex-2212/libcplex2212.so"'
    assert previous.count(line) == 1
    corrected = previous.replace(line, replacement)
    design_keys = ['blocks', 'cap_rules', 'analysis', 'threads', 'memory_GiB',
                   'runtime', 'simultaneous_MIP_processes']
    design_sha = hashlib.sha256(json.dumps({k: old[k] for k in design_keys}, sort_keys=True).encode()).hexdigest()
    prior_amendment = load(HERE / 'CONFIRMATION_EXECUTION_AMENDMENT.json')
    assert design_sha == prior_amendment['scientific_design_sha256']
    local = HERE / 'infrastructure-attempts/loader-preload-6071906-local-view'
    local.mkdir(parents=True, exist_ok=False)
    for name in ['CONFIRMATION_PLAN.json', 'CONFIRMATION_SUBMISSION.json',
                 'CONFIRMATION_EXECUTION_AMENDMENT.json', 'CONFIRMATION_GATE.json',
                 'PREFLIGHT-confirmation.json', 'CONFIRMATION_PROGRESS.json',
                 'CONFIRMATION_LOCAL_AUDIT.json', 'CONFIRMATION_INITIAL_LOCAL_REPLAY.json',
                 'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json', 'CONFIRMATION_RAW_MANIFEST.json',
                 'CONFIRMATION_EXECUTION_REPORT.json', 'CONFIRMATION_ASSIGNMENTS.csv',
                 'CONFIRMATION_ANALYSIS.json', 'INFORME_CONFIRMACION.md',
                 'confirmation-runs', 'confirmation-execution-logs', 'confirmation-replay',
                 'setup-evidence/confirmation', 'setup-evidence/confirmation-local']:
        path = HERE / name
        if path.exists():
            destination = local / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            path.rename(destination)
    wrapper.write_text(corrected)
    dependencies = dict(prior_amendment['archived_evidence_sha256'])
    paths = [p for p in evidence.rglob('*') if p.is_file()]
    paths += [HERE / n for n in ['LOADER_RECOVERY_PROTOCOL.md', 'LOADER_CORRECTION_GATE_PLAN.json',
        'LOADER_CORRECTION_GATE_SUBMISSION.json', 'LOADER_ARCHIVE_SUBMISSION.json',
        'FACTOR_PORTABILITY-Haswell-library-path-all.json', 'PREFLIGHT-loader-corrected.json',
        'EXPORT_RUNTIME_DIAGNOSTIC_PLAN.json', 'EXPORT_RUNTIME_DIAGNOSTIC_SUBMISSION.json',
        'EXPORT_RUNTIME-preloaded.json', 'EXPORT_RUNTIME-none.json', 'EXPORT_RUNTIME-library-path.json',
        'EXPORT_RUNTIME-late-global.json', 'diagnose_export_runtime.py', 'archive_confirmation_loader.py',
        'register_loader_restart.py', 'cluster/diagnose_export_runtime.slurm',
        'cluster/check_loader_exports.slurm', 'cluster/archive_confirmation_loader.slurm']]
    for path in paths:
        dependencies[path.relative_to(HERE).as_posix()] = sha(path)
    amendment = dict(registered_utc=datetime.now(timezone.utc).isoformat(),
        kind='uniform whole-campaign repetition after a loader-level export identity failure',
        original_array='6071906', old_plan_sha256=old_sha,
        original_wrapper_sha256=hashlib.sha256(previous.encode()).hexdigest(),
        corrected_wrapper_sha256=sha(wrapper),
        cause='Global CPLEX LD_PRELOAD changes math.exp by one ULP; LD_LIBRARY_PATH retains full CPLEX and all frozen exports.',
        recorded_prior_assignments=archived['recorded_assignments'],
        recorded_prior_native_solver_invocations=archived['recorded_native_solver_invocations'],
        pre_optimizer_failures=12, previous_attempt_wholly_excluded_from_primary_analysis=True,
        full_repetition_assignments=3840, prior_attempts_retained=True,
        assignment_order_caps_policies_analysis_unchanged=True,
        scientific_design_sha256=design_sha, archived_evidence_sha256=dependencies,
        source_submission_modified=False, original_generator_modified=False,
        new_reference_acquisitions_allowed=False)
    save(HERE / 'CONFIRMATION_EXECUTION_AMENDMENT.json', amendment)
    subprocess.run([sys.executable, str(HERE / 'plan_confirmation.py')], cwd=ROOT, check=True)
    successor = load(HERE / 'CONFIRMATION_PLAN.json')
    for key in design_keys:
        assert successor[key] == old[key], key
    assert all(successor[k] == v for k, v in old.items()
               if k not in ['dependencies', 'execution_amendment_sha256'])
    save(HERE / 'LOADER_RESTART_REGISTRATION.json', dict(status='registered',
        old_plan_sha256=old_sha, new_plan_sha256=sha(HERE / 'CONFIRMATION_PLAN.json'),
        scientific_design_byte_values_equal=True, assignment_count=3840,
        previous_attempt_wholly_excluded=True, optimizer_calls=0,
        protected_scientific_sources_unchanged=True))
    print('Registered uniform loader-corrected repetition; all scientific settings unchanged.')


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
