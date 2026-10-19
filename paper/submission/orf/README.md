# Operations Research Forum delivery

Local version: **v1.4.0-orf-submission**, 18 October 2026.
Proposed type: Original Research Article.

| File | Role |
|---|---|
| main_orf.pdf | Manuscript with author details |
| orf-editable-sources.zip | LaTeX sources, publisher class/style, figures and Online Resource 1 source |
| cover-letter.pdf | Letter addressed to the ORF editors |
| title-page.pdf | Author information and acknowledgements; supplied for the title-page portal role if requested |
| ESM_1.pdf | Online Resource 1: proofs, protocols, full controls and reproduction instructions |
| ESM_2.zip | Online Resource 2: current sources and complete inherited scientific evidence |
| orf-delivery.zip | Complete local delivery, form fields, captions, checksums and validation report |

From the repository root:

```sh
make paper
python3 scripts/research/package_orf.py
python3 scripts/research/validate_orf.py
python3 scripts/research/freeze_orf.py
```

The packager reads the exact frozen OMS v1.3.17 scientific ZIP and validation
record from `paper/submission/oms/releases/v1.3.17-oms-submission/`. Those large
distribution files are outside Git and are supplied inside Online Resource 2.
To rebuild the full package after extracting the canonical revision sources,
copy `scientific-evidence-oms-v1.3.17.zip` from Online Resource 2 to that frozen
directory as `reproducibility-artifact.zip`, and copy
`SCIENTIFIC_PARENT_VALIDATION.json` there as `VALIDATION.json`. Then run the
commands above. The directory is created locally if absent; no download of an
unpublished parent release is required.
The canonical code, experiments and current editorial fragments remain in Git.
The editable LaTeX source bundle can be compiled independently of the code/data
archive. No original generator or stored experiment is modified by this adaptation.

`VALIDATION.json` records clean-extraction compilation and numerical replay.
The ORF audit checks unchanged mathematical statements, proofs, displayed
formulae and numerical tables against the scientific source. It also verifies
the identity of the inherited archive and regenerates the final 42 tables and
three analysis figures from its saved data. No new research MILPs are solved.

The generated portal fields and separate upload roles are preparation material;
exact portal categories and limits are confirmed at upload. The author must enter
contributions and competing interests in the submission interface as well.

The new Zenodo deposit/DOI remains deferred by the author. The archived baseline
DOI identifies v1.2-coap-submission, rather than this ORF snapshot or the later
experiments. The ORF snapshot and its predecessor are local, not published
Zenodo versions. Nothing here asserts acceptance or editorial submission.

See [checklist](SUBMISSION_CHECKLIST.md) and
[publisher-template provenance](../../orf/TEMPLATE_PROVENANCE.md).
