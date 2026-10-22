# Operations Research Forum delivery

Local version: **v1.6.0-orf-submission**, 22 October 2026.
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
`SCIENTIFIC_PARENT_VALIDATION.json` there as `VALIDATION.json`. Extract both follow-up ZIPs over the same revision root. Copy
`verified-candidates-orf-20261019.zip` into
`exploration/orf-v15-verified-20261019/research-evidence.zip`, and its supplied
`VERIFIED_PACKAGE_VALIDATION.json` into that directory as `PACKAGE_VALIDATION.json`.
Then run the commands above. The directory is created locally if absent; no download of an
unpublished parent release is required.
The canonical code, experiments and current editorial fragments remain in Git.
The editable LaTeX source bundle can be compiled independently of the code/data
archive. No original generator or stored experiment is modified by this adaptation.

`VALIDATION.json` records clean-extraction compilation and numerical replay.
The ORF audit checks unchanged mathematical statements, proofs, displayed
formulae and numerical tables against the scientific source. It also verifies
the identity of the inherited archive and regenerates the final 42 tables and
three analysis figures from its saved data. Replay solves no research MILPs. The separate prospective archive records 360 new MIP calls and 96 exact LP attempts on 24 new parameter scenarios, and is checked by an additional license-free rational replay.

The generated portal fields and separate upload roles are preparation material;
exact portal categories and limits are confirmed at upload. The author must enter
contributions and competing interests in the submission interface as well.

The new Zenodo deposit/DOI remains deferred by the author. The archived baseline
DOI identifies v1.2-coap-submission, rather than this ORF snapshot or the later
experiments. The ORF snapshot and its predecessor are local, not published
Zenodo versions. Nothing here asserts acceptance or editorial submission.

See [checklist](SUBMISSION_CHECKLIST.md) and
[publisher-template provenance](../../orf/TEMPLATE_PROVENANCE.md).

The prospective outcome table in the main text reports all accuracy and bound
checks alongside work and complete-process ratios. A separately identified post
hoc analysis resamples 24 whole scenarios, retaining all three seeds together.
Against L2, the work ratio is 0.931 (95% interval 0.702–1.133), with 10/24 scenario
wins; the time ratio is 0.996 (0.832–1.119), with 6/24 wins. These conditional
intervals do not establish a general incremental advantage or external validity.
Replay: `python3 exploration/orf-confirmatory-20261018/check_cluster_analysis.py`.


The v1.5.0 update selectively incorporates the frozen candidate/precision/robustness
follow-up: 630 assigned MIP runs plus one identified technical repeat, on the same
24 known scenarios with three new seeds. Section 5.3 adds finite-candidate selection
with actual-export error reserves. A short main-text summary reports verified-target
successes and PAR2 without claiming a general time advantage over L2. Detailed
CPLEX, ScaleFlag, margin and selector checks are in Online Resource 1. The exact
frozen follow-up ZIP and its prior validation are included in Online Resource 2.
All five new tables regenerate from the independently replayed machine results.


The v1.5.1 editorial revision gives the 24-scenario evidence priority in the
abstract. Physical budgets and exact variable domains are separate columns;
Base passes domains in 69/72 points and Base-tight in 66/72. A post hoc deletion
of each known parent leaves 20 scenarios / 60 paired runs: the Base work ratio
ranges from 0.355 to 0.504, while the L2 ratio ranges from 0.883 to 1.041.
All four controls and both metrics replay from native work and external clocks:
`python3 exploration/orf-confirmatory-20261018/parent_sensitivity.py --check`.
In v1.6.0, the closed 3,840-run campaign is incorporated as a brief main-text
confirmation with full controls, all primary strata and domain/applicability
diagnostics in Online Resource 1. Online Resource 2 includes its lossless raw
archive, pilot/reference evidence and saved-result replay. No superiority
claim is inferred from a null result; Gurobi process time is higher.
The earlier v1.5.0/v1.5.1 releases remain unchanged.
