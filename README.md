# Pre-Export Row Scaling for Generated Mixed-Integer Programs: Accuracy Contracts and Software Evaluation

Manuscript and reproducibility artifact prepared for **Optimization Methods and
Software (OMS)**. Author: Mathias Rodríguez Castro, Facultad de Ingeniería,
Universidad de la República, Montevideo, Uruguay; mathiasr@fing.edu.uy;
ORCID [0009-0002-7235-7677](https://orcid.org/0009-0002-7235-7677).

The manuscript develops an implementation and evaluation workflow for pre-export row scaling:
residual-budget contracts in original application units, explicit factor-selection decisions,
finite-precision export and independent verification. The C++ dispatch exporter and Python
budget selector are separate components. The archived numerical baseline is retained, with
a controlled row-only Ruiz comparison, final-policy stage ablation, and three application
precision scenarios on the same 30 operational models added for OMS. The locally frozen `v1.3.15-oms-submission` snapshot includes those additions. It has not
been submitted or published as a separate Zenodo release and has no version DOI.

The OMS activation follow-up adds 114 nonpilot solver calls, 20 exact feasible witnesses, and matched numerical controls on six archived scenarios without the documented demand inversion. [Findings and limits](exploration/oms-followup-20261014/RESULTADOS.md) distinguish original-unit precision from MILP-bound validity; `make research-oms-check` verifies the supplied data without optimizing.

The [matched IF control and workflow measurement](exploration/oms-if1-workflow-20261015/RESULTADOS.md)
retain twelve principal calls and a twelve-call instrumentation pass. IF1 leaves
the paired points and work unchanged; complete fresh-process costs are measured
on the declared shared machine. Both passes are supplied, without a general speed claim.

The [fully matched accuracy/remedy comparison](exploration/oms-matched-accuracy-20261016/RESULTADOS.md)
adds six known models, automatic/off presolve, three seeds and four policies: 144
terminal comparisons plus one preserved externally interrupted attempt. Main Table 11 and supplementary Table S16
keep primal budgets, effort and bound/gap refutations separate. This is within-family
confirmation, with all full-process stages supplied, not external generalization.

The [secondary evidence audit](exploration/oms-evidence-audit-20261017/RESULTADOS.md)
checks model/seed deletion and complete external costs without new optimization.
Its work advantage is stable within the observed dispatch sample; the external
example validates budget delivery without lower complete time than L2.

The [directed unscaled-control study](exploration/oms-base-control-20261018/RESULTADOS.md)
fills the omitted Base comparison in the favorable dispatch experiment. At 100 m³,
Budget-L2/Base and Budget-L2/Base-tight work ratios are 0.317 and 0.264, with all
three policies meeting every tested primal budget and less than 0.1% maximum
candidate-cost worsening. These are comparisons on six known models, with no
additional primal recovery over Base or general MILP optimality certificate.

## Manuscript and supplements

| File | Purpose |
|---|---|
| `paper/oms/main_oms.pdf` | Manuscript for OMS in the publisher's Interact layout |
| `paper/submission/oms/oms-submission.zip` | Editable LaTeX sources, class/style files, figures and bibliography |
| `paper/oms/cover-letter.pdf` | Cover letter for OMS |
| `paper/supporting-information.pdf` | Supplementary Material 1: proofs, protocols and reproduction instructions |
| `paper/submission/oms/reproducibility-artifact.zip` | Supplementary Material 2: code, stored data, analysis and verification scripts |
| `paper/submission/oms/oms-delivery.zip` | Local package with separate files and upload instructions |

Supplementary Material 2 includes `paper/supporting-information.pdf`, byte-identical to
Supplementary Material 1. See the [OMS submission checklist](paper/submission/oms/SUBMISSION_CHECKLIST.md)
and [adaptation notes](paper/oms/OMS_NOTES.md). File roles must be selected in the journal's
submission portal; its detailed current author instructions could not be retrieved.

The frozen experimental baseline is
[`v1.2-coap-submission`](https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.2-coap-submission).
This version is archived at Zenodo DOI [10.5281/zenodo.23145294](https://doi.org/10.5281/zenodo.23145294).
The repository uses the Zenodo concept DOI
[10.5281/zenodo.20648949](https://doi.org/10.5281/zenodo.20648949).
[CITATION.cff](CITATION.cff) and `.zenodo.json` describe the local OMS snapshot
`v1.3.15-oms-submission`, frozen 2026-10-18. The former root metadata for the published
baseline are preserved in `artifacts/baseline-metadata/`; the baseline DOI belongs to
`v1.2-coap-submission`, not to the new OMS experiments. The version metadata and new-data
inventory are in `paper/submission/oms/SNAPSHOT.json` and `OMS_DATA_MANIFEST.json`.
After package validation, `python3 scripts/research/freeze_oms.py` creates the immutable
local copy under `paper/submission/oms/releases/v1.3.15-oms-submission/`, with hashes and both
supplements. It does not publish to Zenodo or create a remote Git tag. The prior locally frozen `v1.3-oms-submission` copy is retained; this revision clarifies
two main contributions supported by computational evidence. Earlier editorial
files remain in `paper/coap/`; `make paper` builds OMS.

Git retains the canonical manuscript, experiment inputs, saved results, protocols
and independent verification programs. Generated OMS source mirrors, compiler
intermediates, duplicate study bundles and local upload/deposit preparation are
excluded from version control. The two recorded native-selector executables are
retained because their exact hashes belong to the timing evidence. Superseded
editorial previews and packaging logs are kept in a separate local archive.
The [baseline repository validation](paper/validation/oms-repository-validation.json)
records replay and compilation from the preceding committed sources.

## Reproduce and verify

The additional OMS campaign is preserved in
[`results-revision/research-audit/oms-close-20261013`](results-revision/research-audit/oms-close-20261013/README.md).
`make research-oms-check` verifies its saved exports, incumbents, rational contract intervals
and comparison summaries without optimizing. Its 120-second, four-thread Gurobi 13.0.2
protocol is separate from the archived 1,800-second operational experiments. The three
physical budget scenarios are declared study precision objectives, not operator standards.

Run commands from the repository root. The recorded environment is CPython 3.10.12,
NumPy 2.2.6, SciPy 1.15.3, pandas 2.3.3, matplotlib 3.10.9 and pytest 9.0.3.
The requirements pin analysis dependencies; optimizer packages are optional.

```bash
sudo apt install python3-venv build-essential texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
python3 -m venv .venv-research
. .venv-research/bin/activate
python3 -m pip install -r environment/research-requirements.txt
make research-oms-check
make research-check-python
make research-check
make research-analysis
make research-claims
make paper
make research-online-resources
python3 scripts/research/package_oms.py
python3 scripts/research/validate_oms.py
```

`research-check-python` tests the row-factor implementation, independently verifies saved
binary solutions and optima, and checks all 1,080 matrix-export hashes. `research-claims`
independently enumerates the stored binary models, verifies solver acceptance labels,
checks native operational logs and audits the matrix comparisons. Neither imports an optimizer.
`make research-check` also builds the C++ LP exporter and verifies its decimal serialization.

`make research-analysis` regenerates the current tables, figures and summaries from stored data.
`make paper` compiles the canonical manuscript, OMS version and supplement with pdfLaTeX and
BibTeX. [paper/README.md](paper/README.md) maps the manuscript sources.

`validate_oms.py` extracts the archives, verifies their checksums, recompiles the
manuscript and supplement, verifies the exact Supplementary Material 1 copy in Material 2,
checks relative README links and runs the documented audits from the extracted artifact.
Results are saved in `paper/submission/oms/VALIDATION.json`.

## Stored experiment data

The authoritative datasets are under `results-revision/research-audit/`:

| Directory | Evidence |
|---|---|
| `fixed-basis-final-20260914/` | Fixed-basis audit of 306 dispatch models under five policies, with 1,530 bases and an independent precision check |
| `identifiability-final/` | 180 generated instances, six policies and 1,080 matrix exports; named comparisons, spectra and hashes |
| `budget-final/`, `budget-final-cplex/` | Identical 96 stored binary models under three solvers, nine policies and two presolve settings: 5,184 planned configurations and 4,752 optimizer calls |
| `exploration-lattice/`, `exploration-lattice-cplex/` | Integer-aware GCD controls with exact-enumeration verification |
| `operational/` | Reconstruction of 240 dispatch runs, with native logs, input hashes, completed-run work comparisons and fixed-pool PAR10 |
| `operational-replication/` | Two matched 240-run sensitivity campaigns using a second seed and a second solver |
| `application-budgets/` | Declared residual budgets for 4,320 interpretable rows of one dispatch model, its exported LP and a budget-sensitivity sweep |

Protocols retain versions, seeds, settings and source hashes. Recorded results and source
snapshots are frozen. Intermediate datasets needed to interpret the experiments retain their
provenance; the supplement identifies which comparisons are exploratory.

The root directories `results/` and `results-revision/` also retain dispatch aggregates and
controls used by the current audits. The input instances are under `data/`.
The binary stress models approach integer feasibility boundaries and do not estimate
industrial failure rates. Exact global-LP bounds and integer reference witnesses now
certify the original dispatch model instance031 and provide intervals for five others
(three of the six within 1%). These reference certificates do not certify every saved
native MILP result. Dispatch residual budgets are study precision targets, not
operator-calibrated tolerances.

## Bulk inputs

Supplementary Material 2 carries the stored summaries, analysis inputs and native logs used by the
verification commands above. The bulk fixed-basis LP text and bases are distributed separately
as `fixed-basis-exports.tar.zst`: 337 MB compressed, 5.18 GB uncompressed in 11,585 files.
Their manifest and checksum are in `paper/submission/data-deposit/`; the archive is attached
to the archived baseline release. See [artifacts/README.md](artifacts/README.md).

The four commands `make research-oms-check`, `make research-check-python`,
`make research-check` and `make research-analysis` are self-contained in Material 2.
The stress audit explicitly covers HiGHS, Gurobi and CPLEX: 5,184 configurations,
432 abstentions and 4,752 saved optimizer calls on 96 shared models.
The stopped-campaign `analysis/runs.csv` and `analysis/contradictions.csv` are also
supplied under `results-revision/solver-robustness/` to regenerate the historical
screening tables. These numerical screening records are distinct from the exact
feasible witnesses supplied for the newer activation comparisons.

Extract the separate bulk archive at the repository root before
`make research-fixed-basis-check` (all 1,530 bases) or a fresh
`make research-fixed-basis-precision`. The latter recomputes rational lower bounds
and numerical upper estimates into a new output directory; the upper endpoints
are not formally certified. The bulk archive belongs to the
[historical baseline DOI](https://doi.org/10.5281/zenodo.23145294), and its hashes
are supplied in `paper/submission/data-deposit/`. These checks require no optimizer run.

## Optional fresh experiments

Fresh experiment targets require new output directories and retain the stored evidence:

```bash
make research-grid GRID_OUT=results-revision/research-audit/reruns/grid
make research-budget BUDGET_SOLVERS=highs BUDGET_OUT=results-revision/research-audit/reruns/budget-highs
```

The matrix grid uses the solver-free C++ exporter. A HiGHS-only binary run requires `highspy`
and covers one solver arm; it does not replace the three-solver manuscript data. The Gurobi
and CPLEX arms require their respective packages and licenses. The supplement gives the full
recorded protocols. Solver trajectories and wall times can depend on versions and platforms.

## Layout and licensing

| Path | Contents |
|---|---|
| `paper/` | Current manuscript, supplement, cover letter, bibliography, tables and figures |
| `scripts/` | Experiment, analysis, packaging and independent verification tools |
| `tests/` | Row-factor mathematics and C++ export integration checks |
| `code/` | C++ generator and row-scaling implementation |
| `data/`, `results/`, `results-revision/` | Instances, stored observations and provenance |
| `environment/` | Recorded dependencies and solver environment |

Code is MIT-licensed ([LICENSE](LICENSE)); data and aggregate results use CC BY 4.0
([DATA_LICENSE.md](DATA_LICENSE.md)). The manuscript is outside those licenses.

## Additional precision and verification evidence — 16 October 2026

The [prespecified multi-budget study](exploration/oms-frontier-20261016/RESULTADOS.md)
retains 330 MILP calls, 30 abstentions and 31 exact native-export witnesses. At
30–100 m3 with automatic presolve, all six known models meet the preset comparison
criterion against NF3; primal recovery over L2 remains localized. Supplementary
Tables S17–S19 also document an [isolated C++ preparation benchmark](exploration/oms-native-selector-20261016/RESULTADOS.md)
and [exact original-model LP reference intervals](exploration/oms-global-lp-20261016/RESULTADOS.md).
`make research-oms-check` replays these additions without optimizing. The native
benchmark measures standalone preparation, not a full optimization speedup. The
exact Base certificates do not certify all native floating-export results.

The v1.3.12 editorial revision highlights that existing regime in the abstract,
introduction and compact main Table 12. It introduces no research solver calls;
S17 retains both presolve panels and all prespecified adverse outcomes.

## Bounded follow-up, 17 October 2026

The [follow-up report](exploration/oms-followup-20261017/RESULTADOS.md) adds an
independent batch-scheduling check, a matched integer-tolerance control, direct
activation-factor verification and a complete C++/Python process benchmark.
There are 176 new MIP calls and eight exact LP attempts; seven reference
refinements remain unknown. Budget and matched L2 each meet all 24 external
primal-budget checks, NF3 meets 23. The 18 implementation pairs preserve every
point, solver endpoint and Work, with paired full-time ratio 0.824 on this host.
The favorable dispatch zero-flag regime does not persist across both tolerances.
`make research-oms-check` replays these results without solving.
