"""Check immutable scientific payload; replay-derived files are listed separately."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
manifest=json.loads((HERE/'MANIFEST.json').read_text())
for item in manifest['immutable_files']:
    path=ROOT/item['path'];assert path.is_file(),str(path)
    assert path.stat().st_size==item['bytes'],str(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],str(path)
print(json.dumps({'immutable_files_checked':len(manifest['immutable_files']),
                  'replay_outputs_listed_separately':len(manifest['recomputed_outputs']),
                  'new_optimizer_calls':0}))
