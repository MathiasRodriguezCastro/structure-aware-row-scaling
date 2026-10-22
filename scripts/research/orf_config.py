"""Identity of the ORF submission and its inherited and prospective evidence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper'
ORF = PAPER / 'orf'
OUT = PAPER / 'submission/orf'
VERSION = 'v1.6.0-orf-submission'
DATE = '2026-10-22'
TITLE = ('Accuracy-Aware Row Scaling for Generated Mixed-Integer Programs: '
         'A Computational and Software Study')
PARENT = 'v1.3.17-oms-submission'
PARENT_COMMIT = 'f7cfc0b3'
PARENT_DIR = PAPER / 'submission/oms/releases' / PARENT
FOLLOWUP = ROOT / 'exploration/orf-confirmatory-20261018'
FOLLOWUP_ARCHIVE = 'prospective-scenarios-orf-20261018.zip'
VERIFIED = ROOT / 'exploration/orf-v15-verified-20261019'
VERIFIED_ARCHIVE = 'verified-candidates-orf-20261019.zip'
CONFIRMATION = ROOT / 'exploration/orf-confirmatory-extension-20261019'
CONFIRMATION_ARCHIVE = 'confirmation-evidence-20261022.tar.xz'
CONFIRMATION_ARCHIVE_PATH = CONFIRMATION / CONFIRMATION_ARCHIVE
COMPARATIVE_MIP_CALLS = 1351 + 3840


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
