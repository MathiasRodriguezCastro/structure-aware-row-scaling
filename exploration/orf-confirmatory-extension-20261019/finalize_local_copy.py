#!/usr/bin/env python3
"""Wait for the frozen raw transfer, then run the existing complete seal check."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from seal_confirmation import digest

HERE = Path(__file__).resolve().parent


def process_token(pid):
    try:
        fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        return fields[19]
    except FileNotFoundError:
        return None


def main(pid, token):
    os.nice(10)
    receipt = HERE / 'CONFIRMATION_LOCAL_COPY_FOLLOWUP.json'
    assert not receipt.exists(), 'An existing follow-up must be inspected before another attempt.'
    sources = {name: digest(HERE / name) for name in
               ['close_confirmation.py', 'seal_confirmation.py', 'CONFIRMATION_RAW_MANIFEST.json',
                'finalize_local_copy.py']}
    report = dict(status='waiting_for_transfer', registered_utc=datetime.now(timezone.utc).isoformat(),
                  transfer_pid=pid, transfer_start_token=token, sources=sources,
                  timeout_seconds=21600, optimizer_calls=0,
                  scientific_analysis_modified=False, automatic_git_changes=False)
    def save():
        temporary = receipt.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(receipt)
    save()
    started = time.monotonic()
    try:
        while process_token(pid) == token:
            assert time.monotonic() - started < report['timeout_seconds'], 'Raw transfer wait timed out.'
            time.sleep(10)
        for name, expected in sources.items():
            assert digest(HERE / name) == expected, name
        report['status'] = 'verifying_complete_local_archive'
        save()
        result = subprocess.run([sys.executable, str(HERE / 'close_confirmation.py'), '--verify-local-raw'],
                                cwd=HERE.parents[1], text=True, capture_output=True, timeout=3600)
        report.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        assert result.returncode == 0, 'Complete local seal verification failed; inspect the retained output.'
        proof = json.loads((HERE / 'CONFIRMATION_LOCAL_RAW_CHECK.json').read_text())
        assert proof['status'] == 'passed' and proof['raw_manifest_sha256'] == sources['CONFIRMATION_RAW_MANIFEST.json']
        report.update(status='passed', completed_utc=datetime.now(timezone.utc).isoformat(),
                      local_proof_sha256=digest(HERE / 'CONFIRMATION_LOCAL_RAW_CHECK.json'))
        save()
        print('Complete local raw copy and every sealed hash verified; no optimizer calls.', flush=True)
    except Exception as error:
        report.update(status='failed', completed_utc=datetime.now(timezone.utc).isoformat(),
                      error=type(error).__name__ + ': ' + str(error))
        save()
        raise


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('transfer_pid', type=int)
    parser.add_argument('start_token')
    args = parser.parse_args()
    main(args.transfer_pid, args.start_token)
