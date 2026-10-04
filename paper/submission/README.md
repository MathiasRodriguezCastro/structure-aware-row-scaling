# COAP submission package

Target: **Computational Optimization and Applications**.
Guidelines: https://link.springer.com/journal/10589/submission-guidelines
Current release: `v1.2-coap-submission`.

## Files to upload

Extract `coap-delivery.zip` and upload the following files **separately** in Editorial Manager:

| File | Upload role |
|---|---|
| `main_coap.pdf` | Manuscript |
| `coap-submission.zip` | Editable LaTeX sources |
| `cover-letter.pdf` | Cover letter |
| `ESM_1.pdf` | Supplementary material: Online Resource 1 |
| `ESM_2.zip` | Supplementary material: Online Resource 2 |

`editorial-manager/UPLOAD_INSTRUCTIONS.md` supplies captions for the supplements.
`ESM_1.pdf` is byte-identical to `paper/supporting-information.pdf`; `ESM_2.zip` is
byte-identical to `reproducibility-artifact.zip`. Online Resource 2 includes the exact
Online Resource 1 PDF for standalone verification. The two ESM files must still be uploaded
as separate supplements. Online Resource 2 is not nested inside the manuscript source ZIP.

## Build and check

From the repository root:

```bash
make paper
make research-claims
python3 scripts/research/package_submission.py
python3 scripts/research/validate_submission.py
```

The packaging script creates the manuscript source ZIP, Online Resource 2, upload-name copies
and the complete delivery ZIP. `VALIDATION.json` records archive checksums, independent source
compilation and the audits executed from a clean extraction of Online Resource 2.
`SHA256SUMS` covers the submission files; each archive also carries an internal manifest.

## Bulk data

The exported LP text and bases of the fixed-basis audit are distributed as
`data-deposit/fixed-basis-exports.tar.zst`, with manifest and checksum in the same directory.
Only the full fixed-basis reconstruction needs those 5.18 GB of raw inputs. The artifact
includes the summaries and native operational logs used by its documented verification commands.

The release is archived under the concept DOI https://doi.org/10.5281/zenodo.20648949.
The scripts prepare and verify local files; they do not submit the manuscript to the journal.
