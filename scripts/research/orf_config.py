"""Identity of the ORF adaptation and its unchanged scientific evidence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper'
ORF = PAPER / 'orf'
OUT = PAPER / 'submission/orf'
VERSION = 'v1.4.0-orf-submission'
DATE = '2026-10-18'
TITLE = ('Accuracy-Aware Row Scaling for Generated Mixed-Integer Programs: '
         'A Computational and Software Study')
PARENT = 'v1.3.17-oms-submission'
PARENT_COMMIT = 'f7cfc0b3'
PARENT_DIR = PAPER / 'submission/oms/releases' / PARENT


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
