# Accuracy-Aware Row Scaling for Generated Mixed-Integer Programs: A Computational and Software Study

Manuscript and reproducibility artifact prepared for **Operations Research
Forum (ORF)**. Author: Mathias Rodríguez Castro, Facultad de Ingeniería,
Universidad de la República, Montevideo, Uruguay; mathiasr@fing.edu.uy;
ORCID [0009-0002-7235-7677](https://orcid.org/0009-0002-7235-7677).

**Current submission snapshot: `v1.7.2-orf-submission` (22 October 2026).**
The v1.7.2 editorial revision shares the ClusterUY acknowledgement between the
manuscript and title page and consolidates repeated qualifications. It retains
all scientific results and the cover letter. The v1.7.1 packaging correction adds 38 small cluster support/launch files and
an installation wheel lock omitted by the earlier raw-tar metadata filter.
It leaves the sealed scientific tar and all results unchanged; a clean package
audit checks the restored helpers alongside every confirmatory job bundle.
The paper presents a verifiable model-generation procedure connecting original-unit
residual budgets, admissible row-factor selection or explicit abstention,
finite-precision export and independent returned-point checks. It integrates
established scaling ideas into explicit, reproducible software decisions.

The larger frozen confirmation contains **3,840 assignments** on 160 models
from 40 historically generated parents, three dispatch formulations, four
horizons, three seeds and two solvers. All assignments are retained: 3,816 are
quality-eligible and 24 are diagnostic because their model is independently
infeasible. The primary Budget-L2/L2 PAR2 ratios are 0.995 (Gurobi) and 1.000
(CPLEX), with whole-parent intervals containing one. Gurobi complete-process
time increases by 7.9%. Every eligible final point meets the mapped physical
budgets under every policy. These results establish neither general incremental
acceleration nor additional prospective physical-budget recovery.

The [v1.7.0 sensitivity analysis](exploration/orf-acceptance-sensitivity-20261022/README.md)
explains much of CPLEX's strict-domain rejection through small written-bound
residues; its independent vector/bound replay checks 13,387 candidate domains.
It does not change the registered endpoint or the primary time comparisons.
The [closed campaign report](exploration/orf-confirmatory-extension-20261019/INFORME_CIERRE_CONFIRMATORIO.md)
retains the protocol, adverse outcomes and generalization limits. The earlier
24-scenario prospective study and the audited OMS scientific archive are inherited
explicitly; these generated inputs are not independent operational observations.

## Public repository and review package

| Material | Availability |
|---|---|
| Canonical manuscript fragments, bibliography, generator/scaling code, protocols, analysis programs and aggregate results | Public in this repository |
| Current `main_orf.pdf`, `ESM_1.pdf` and editable LaTeX ZIP | Supplied in the frozen submission delivery; generated PDFs/ZIPs are not tracked in Git |
| Complete raw results, candidate vectors, model exports, native logs and clocks for all 3,840 assignments, plus prospective/follow-up evidence | **Online Resource 2 (`ESM_2.zip`)**, supplied for review; the bulk raw files are not hosted in this Git repository |
| Pinned dependencies, integrity manifests, rational witnesses and license-free replay inputs | Included in Online Resource 2 with canonical sources and byte-identical inherited archives |
| Historical public baseline | [Zenodo DOI 10.5281/zenodo.23145294](https://doi.org/10.5281/zenodo.23145294); this DOI does not identify the later ORF experiments |

The current complete data package has **no new public Zenodo DOI yet**. A Git
clone is sufficient to inspect the public sources and reports; full saved-data
reproduction requires extracting Online Resource 2 according to its README.
The manuscript's availability statement and the public repository therefore refer
to different, explicitly identified delivery channels. The [submission guide](paper/submission/orf/README.md)
provides the upload roles; [audit_orf_release.py](scripts/research/audit_orf_release.py)
checks the frozen package without modifying it or executing new MIP experiments.

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
Main Table 13 exposes the existing interleaved complete-process times: scaling
is faster on models 001, 027 and 046, and slower on 005, 022 and 031. All ratios
are paired geometric means; these shared-host observations are not a predictive
selection rule for unseen instances.

## Manuscript and supplements

Run `make paper` for the current ORF documents. The adaptation leads with
accuracy-aware model generation and verification, followed by computational
assessment and practical implications. Mathematical statements, experiments and
numerical results are preserved from the audited OMS v1.3.17.

| File | Purpose |
|---|---|
| `paper/orf/main_orf.pdf` | ORF manuscript in the Springer Nature template |
| `paper/orf/ESM_1.pdf` | Online Resource 1: proofs, controls and reproduction instructions |
| `paper/orf/cover-letter.pdf` | New letter addressed to ORF |
| `paper/submission/orf/ESM_2.zip` | Online Resource 2: current sources and the complete unchanged scientific archive |
| `paper/submission/orf/orf-delivery.zip` | Complete local delivery, source ZIP, both resources, form fields and checksums |

[ORF preparation](paper/submission/orf/README.md) and the
[checklist](paper/submission/orf/SUBMISSION_CHECKLIST.md) describe the package.
`paper/orf/editorial/` and `scripts/research/build_orf.py` generate the current
manuscript from the preserved scientific source in `paper/main.tex`.
Generated mirrors, local delivery ZIPs and compiler intermediates stay outside Git.
Canonical text, source code, experiment records and verifiers remain versioned.

The immutable local OMS v1.3.17 delivery is retained. Online Resource 2 contains
its exact scientific-evidence ZIP, parent validation record and current ORF
sources, with an explicit inheritance record. The current CFF and Zenodo metadata
identify the ORF adaptation. The published historical baseline is
[v1.2-coap-submission](https://doi.org/10.5281/zenodo.23145294), with concept DOI
[10.5281/zenodo.20648949](https://doi.org/10.5281/zenodo.20648949). These DOIs
identify the earlier baseline, rather than the later experiments or current ORF
snapshot. The new deposit/DOI remains deferred. No journal submission has been made.

## Reproduce and verify

The additional OMS campaign is preserved in
[`results-revision/research-audit/oms-close-20261013`](results-revision/research-audit/oms-close-20261013/README.md).
`make research-oms-check` verifies its saved exports, incumbents, rational contract intervals
and comparison summaries without optimizing. Its 120-second, four-thread Gurobi 13.0.2
protocol is separate from the archived 1,800-second operational experiments. The three
physical budget scenarios are declared study precision objectives, not operator standards.

For the complete saved-data replay, first extract Online Resource 2 and its
nested evidence archives as described in its supplied README. Run the following
commands from that extracted repository root; a bare Git clone does not contain
all recent raw data. The recorded environment is CPython 3.10.12,
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
```

`research-check-python` tests the row-factor implementation, independently verifies saved
binary solutions and optima, and checks all 1,080 matrix-export hashes. `research-claims`
independently enumerates the stored binary models, verifies solver acceptance labels,
checks native operational logs and audits the matrix comparisons. Neither imports an optimizer.
`make research-check` also builds the C++ LP exporter and verifies its decimal serialization.

`make research-analysis` regenerates the current tables, figures and summaries from stored data.
`make paper` compiles the canonical manuscript, OMS version and supplement with pdfLaTeX and
BibTeX. [paper/README.md](paper/README.md) maps the manuscript sources.

The frozen ORF package can be checked without replacing its files:

```sh
TMPDIR=/dev/shm python3 scripts/research/audit_orf_release.py \
  --release /path/to/v1.7.2-orf-submission \
  --output /path/to/new-audit-directory
```

This command requires the complete frozen delivery (including its validation
record), the analysis dependencies and enough temporary space. It checks all
3,840 raw job bundles and 480 replay reports, runs the current saved-result
verifiers, rebuilds the editable LaTeX sources and regenerates the manuscript
summaries. Only the byte-identical historical parent's already completed
four-command audit is reused. It performs no new MIP experiments and leaves
all frozen input files unchanged. The latest [package audit](paper/submission/orf/VALIDATION.json)
records the exact input hashes and verification scope.

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

The prospective outcome table in the main text reports all accuracy and bound
checks alongside work and complete-process ratios. A separately identified post
hoc analysis resamples 24 whole scenarios, retaining all three seeds together.
Against L2, the work ratio is 0.931 (95% interval 0.702–1.133), with 10/24 scenario
wins; the time ratio is 0.996 (0.832–1.119), with 6/24 wins. These conditional
intervals do not establish a general incremental advantage or external validity.
Replay: `python3 exploration/orf-confirmatory-20261018/check_cluster_analysis.py`.

The ORF v1.7.0 revision presents the large confirmation separately and adds
[post hoc written-bound acceptance sensitivity](exploration/orf-acceptance-sensitivity-20261022/README.md),
independently checked from 13,387 saved candidate domains. The registered
criterion, primary times and scientific archive remain unchanged.
