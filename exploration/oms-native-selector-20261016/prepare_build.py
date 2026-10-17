#!/usr/bin/env python3
"""Create an isolated generator source tree. Original files stay untouched."""
import hashlib
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
if (HERE/'source').exists():raise RuntimeError('isolated source already exists')
hashes={}
for path in (ROOT/'code').rglob('*'):
    if path.suffix not in ['.h','.cpp'] or any(p.startswith('build') for p in path.relative_to(ROOT/'code').parts):continue
    rel=path.relative_to(ROOT/'code');dest=HERE/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,dest);hashes[str(rel)]=hashlib.sha256(path.read_bytes()).hexdigest()
shutil.copyfile(ROOT/'code/Makefile',HERE/'source/Makefile')
shutil.copyfile(HERE/'NativeContracts.h',HERE/'source/NativeContracts.h')
p=HERE/'source/1_SistemaElectrico.cpp';text=p.read_text()
text=text.replace('#include "synthetic/ComandoBenchmarkSintetico.h"','#include "synthetic/ComandoBenchmarkSintetico.h"\n#include "NativeContracts.h"')
needle='prep.diagnosticar();';assert text.count(needle)==1
text=text.replace(needle,needle+'\n                oms_native::apply(*p);')
p.write_text(text)
(HERE/'original-source-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
