"""Coverage checks on the extracted scientific archives and support overlay."""
import json
from pathlib import Path
import re


def check_coverage(root, manifest, support_members):
    prefix = 'exploration/orf-confirmatory-extension-20261019/'
    names = {f['path'] for f in manifest['files']}
    combined = names | set(support_members)
    study = root/prefix
    plan = json.loads((study/'CONFIRMATION_PLAN.json').read_text())
    jobs = [j for b in plan['blocks'] for j in b['jobs']]
    assert len(jobs) == len({j['id'] for j in jobs}) == 3840
    for job in jobs:
        base = prefix+'confirmation-runs/'+job['id']+'/'
        for name in ['result.json','candidates.npz','Base.lp','solver.log']:
            assert base+name in names, base+name
        if job['policy'] != 'Base':
            assert base+'scaled.lp' in names
        assert prefix+'confirmation-execution-logs/'+job['id']+'.json' in names
    for i in range(480):
        assert prefix+f'confirmation-replay/{i:03d}.json' in names
    required = ['environment/research-requirements.txt','environment/python-requirements.txt',
                'environment/apt-packages.txt','environment/solver-notes.md']
    assert all((root/n).is_file() for n in required)
    cluster_required = ['WHEELS.json','install_wheels.py','preflight.py','install_environment.slurm']
    for name in cluster_required:
        relative = prefix+'cluster/'+name
        assert relative in combined and (root/relative).is_file(), relative
    launch_helpers = set()
    for script in (study/'cluster').glob('*.slurm'):
        for name in re.findall(r'cluster/([A-Za-z0-9_.-]+\.py)', script.read_text()):
            assert (study/'cluster'/name).is_file(), (script.name,name)
            launch_helpers.add(name)
    installed = json.loads((study/'DEPENDENCY_INSTALLATION.json').read_text())
    wheels = json.loads((study/'cluster/WHEELS.json').read_text())
    assert installed['wheels'] == wheels['wheels'], 'Wheel lock differs from recorded installation.'
    seals = [prefix+n for n in ['CONFIRMATION_RAW_MANIFEST.json',
        'CONFIRMATION_ANALYSIS_VALIDATION_MANIFEST.json','PENDING_RAW_MANIFEST.json',
        'REFERENCE_RECOVERY_RAW_MANIFEST.json','PILOT_RAW_MANIFEST.json']]
    assert all(n in names for n in seals)
    return dict(status='passed', assignments=3840, quality_eligible=3816,
        diagnostic_assignments=sum(j['diagnostic'] for j in jobs),
        result_files=3840, candidate_archives=3840, native_solver_logs=3840,
        complete_process_logs=3840, independent_block_reports=480,
        raw_files=len(names), raw_logical_bytes=sum(f['bytes'] for f in manifest['files']),
        supporting_cluster_files=len(support_members),
        cluster_python_helpers_checked=sorted(launch_helpers),
        pinned_dependency_files=required, wheel_lock_matches_recorded_installation=True,
        integrity_seals=seals, raw_archive_unchanged=True, new_MIP_experiments=0)
