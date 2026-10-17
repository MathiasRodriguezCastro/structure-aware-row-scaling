#!/usr/bin/env python3
"""Freeze validated OMS delivery under a versioned path; never overwrite a version."""
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from oms_snapshot import OUT, ROOT, VERSION, REVISION_DATE, sha, verify_manifest


def main():
    validation = json.loads((OUT / "VALIDATION.json").read_text())
    assert validation["local_revision_date"] == REVISION_DATE
    assert validation["snapshot_version"] == VERSION
    assert validation["delivery"]["sha256"] == sha(OUT / "oms-delivery.zip")
    assert validation["artifact_audit"]["complete_new_oms_data_supplied"]
    uploads = OUT / "uploads"
    files = {p.name: p for p in uploads.iterdir() if p.is_file() and p.name != "SHA256SUMS"}
    files.update({"oms-delivery.zip": OUT / "oms-delivery.zip",
                  "VALIDATION.json": OUT / "VALIDATION.json", "SNAPSHOT.json": OUT / "SNAPSHOT.json",
                  "OMS_DATA_MANIFEST.json": OUT / "OMS_DATA_MANIFEST.json",
                  "CITATION.cff": ROOT / "CITATION.cff", "zenodo-metadata.json": ROOT / ".zenodo.json"})
    release = OUT / "releases" / VERSION
    if release.exists():
        for name, origin in files.items():
            assert sha(release / name) == sha(origin), "Frozen version differs: " + name
        print("Existing frozen version verified:", release)
        return
    release.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".oms-freeze-", dir=release.parent) as tmp:
        staging = Path(tmp) / VERSION
        staging.mkdir()
        for name, origin in files.items():
            shutil.copy2(origin, staging / name)
            assert sha(staging / name) == sha(origin)
        (staging / "README.md").write_text(f"""# {VERSION}

Frozen local OMS submission snapshot, {REVISION_DATE}. This is not a public Zenodo
release and has no assigned version DOI. The baseline DOI in the metadata identifies
v1.2-coap-submission, not the new experiments. No editorial submission was performed.

Contains the manuscript, cover letter, both supplements, editable sources and complete
delivery, plus the validated file inventory and checksums. New OMS exports, named bases,
factors, native logs, incumbents and replay programs are inside reproducibility-artifact.zip.
Extract that artifact and run make research-oms-check without optimizing. The complete
historical 1,530-basis rebuild additionally uses the baseline bulk archive.

Files in this directory are read-only. Revisions must use a new snapshot version.
""")
        entries = sorted(p for p in staging.iterdir() if p.is_file())
        (staging / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.name}\n" for p in entries))
        staging.rename(release)
    for path in release.iterdir():
        if path.is_file():
            path.chmod(0o444)
    # Inspect the artifact in the frozen copy, not just the mutable working package.
    with tempfile.TemporaryDirectory(prefix="oms-frozen-check-") as tmp:
        with zipfile.ZipFile(release / "reproducibility-artifact.zip") as bundle:
            bundle.extractall(tmp)
        verified = verify_manifest(tmp)
    print("Frozen OMS snapshot:", release)
    print("Verified new-data inventory:", verified["inventoried_files_verified"], "files")


if __name__ == "__main__":
    main()
