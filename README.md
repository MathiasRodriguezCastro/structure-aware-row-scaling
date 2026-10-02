# Pre-Export Row Scaling for Generated Mixed-Integer Programs: Mechanism Attribution and Residual-Budget Contracts

**Research status, 25 September 2026: prepared for submission to Mathematical Programming
Computation.** The manuscript is in `paper/` in a journal-neutral layout and in `paper/mpc/` in
Springer's `svjour3` format, the version intended for MPC; `paper/mpc/MPC_NOTES.md` records
every change the format required and the checks that the two versions agree. The submission
package, and the script that verifies it, are in `paper/submission/`. What changed in the last
revision round, and which claims are confirmatory rather than exploratory, is recorded in
[the revision record](paper/research-audit/revision-record-20260924.md).

A pre-registered solver-robustness campaign was prepared and partly run on ClusterUY, then
descoped from this manuscript to keep it about mechanism and guarantees rather than
benchmarking. Its protocol, split, frozen run tables and the 9,057 runs completed before it was
stopped remain in [`results-revision/solver-robustness/`](results-revision/solver-robustness/)
for a separate study; nothing in the paper depends on them.

## Online Resource 2

This repository is **Online Resource 2** of the manuscript above, submitted to *Mathematical
Programming Computation*. Online Resource 1 is the supplement,
[`paper/supporting-information.pdf`](paper/supporting-information.pdf).

Author: Mathias Rodríguez Castro, Facultad de Ingeniería, Universidad de la República,
Montevideo, Uruguay — <mathiasr@fing.edu.uy>.

The current manuscript is **unpublished**. No journal acceptance, submission, or
upload of this revision to an external archive is claimed.

The paper separates what row scaling demonstrably does from what it is credited with. With one
LP basis held fixed, scaling moves the basis condition number by six to eight orders of
magnitude; the apparent block-metadata advantage of an earlier draft turns out to be a
coupling-kernel effect that a control without ownership information reproduces; residual budgets
stated in application units survive consistent row re-emission and determine the admissible row
factors exactly; and what a solver then does with the representation is measured, not assumed.
The results do not establish a universal solver speedup or reliability improvement.

The earlier positive block-attribution claim is superseded. Historical drafts and intermediate
results remain available so the change in interpretation can be audited; the separate
rounding-safety investigation lives in its own
[working note](paper/research-notes/joint-rounding.pdf) and is not part of this manuscript.

## Reproduce the current paper without a solver license

Run commands from the repository root. The recorded environment is Python 3.10.12,
NumPy 2.2.6, SciPy 1.15.3, pandas 2.3.3, matplotlib 3.10.9, and pytest 9.0.3.
The requirements file pins these Python packages; it does not install an optimizer.

On a stock Debian or Ubuntu, `python3 -m venv` needs a package that is not installed by
default, and the C++ and PDF targets below need a compiler and a TeX installation:

```bash
sudo apt install python3-venv build-essential texlive-latex-recommended texlive-fonts-recommended
```

```bash
python3 -m venv .venv-research
. .venv-research/bin/activate
python3 -m pip install -r environment/research-requirements.txt
make research-check-python
make research-analysis
make paper
```

`research-check-python` runs the row-factor mathematical/numerical tests, independently
checks the saved binary solutions and enumerated optima, and checks all 1,080 final
LP hashes. It imports neither HiGHS nor Gurobi. It writes an updated
`budget-final/verification.json`; the saved model and solution data are unchanged.
`research-analysis` regenerates the current budget, matrix, and operational summaries,
tables, and vector figures from saved data. `paper` builds `paper/main.pdf` and
`paper/supporting-information.pdf` with pdfLaTeX and BibTeX. A standard TeX Live
installation with the packages listed in [paper/README.md](paper/README.md) suffices;
the historical Wiley class and its assets now sit beside the baseline that uses them, in paper/research-audit/baseline-20260908/.

`research-fixed-basis-check` recomputes the conditioning audit of §4 from the stored
exports and bases, independently of the campaign that produced them, and
`research-fixed-basis-precision` recomputes the certified bounds of Table S2 into a new
directory. Neither needs an optimizer:

```bash
make research-fixed-basis-check
make research-fixed-basis-precision
```

To also check the actual C++ LP serializer, install GNU Make and a C++17 compiler:

```bash
make research-check
```

This builds a solver-free `DummyLp` executable in the isolated `code/build-audit/`
directory, then runs both Python checks and a C++ export integration test. The test
covers small coefficients, the RHS, bounds, and objective values that the old fixed
precision format could lose. `code/build/` is not used for this target. A first build
takes longer than the Python-only check.

### What it costs, measured from a fresh clone

Timed on 2 October 2026 on one machine --- Intel Core i7-13620H, 16 threads, 15 GB RAM,
Ubuntu 22.04.5, kernel 6.8, g++ 11.4, TeX Live 2022/Debian, CPython 3.10.12 --- by cloning
this repository into an empty directory and running each target in order. The log of that run
is [`paper/research-audit/cleanroom-20261002.log`](paper/research-audit/cleanroom-20261002.log).

| Command | Time | What it needs |
|---|---|---|
| `git clone` | 17 s | 5.3 GB on disk, of which 5.0 GB is the stored LP text and bases of the fixed-basis audit |
| `make research-check-python` | 2 s | the pinned Python packages |
| `make research-check` | 16 s | also a C++17 compiler; includes the first `build-audit` compile |
| `make research-analysis` | 10 s | regenerates every current table, figure and summary |
| `make research-fixed-basis-check` | 218 s | rebuilds all 1,530 bases from the LP text and recomputes their conditioning |
| `make research-fixed-basis-precision` | 107 s | recomputes the certified rational bounds of the stress sample; reproduced them bit for bit |
| `make research-application-budgets` | 4 s | regenerates the declared-budget table and its sweep |
| `make research-application-export` | 11 s | re-exports that model and compares it byte by byte |
| `make research-budget BUDGET_SOLVERS=highs BUDGET_OUT=...` | 7 s | `highspy`; 1,728 fresh configurations |
| `make -C paper all` | 5 s | pdfLaTeX and BibTeX; builds the article, the supplement and the Springer submission version |
| `make research-online-resources` | <1 s | audits the two Online Resources against the manuscript |

Nothing here needs a commercial solver. Gurobi and CPLEX are needed only to rerun their arms
of the stress experiment and the operational campaign, both of which are reported from stored
data. The one long step is the fixed-basis check, and it is the only one that reads the bulk
data.

## Which data support the current manuscript?

| Location under `results-revision/research-audit/` | Role |
|---|---|
| `identifiability-final/` | Authoritative matrix audit: 180 generated instances, six policies, 1,080 LP exports using the corrected round-trip serializer; named comparisons, whole-row checks, spectra at a common reference rank, and hashes. |
| `budget-final/` | Authoritative binary stress experiment, HiGHS and Gurobi arms: 96 models, nine policies, two presolve settings; 3,456 planned configurations, including 288 abstentions and 3,168 optimizer calls. Models, factors, returned points, protocol and source snapshots are retained. |
| `budget-final-cplex/` | The third solver of the same experiment: the identical 96 stored models and row factors under CPLEX, 1,728 configurations. Together with `budget-final/` this is the three-solver experiment the manuscript reports, 4,752 optimizer calls in total. The models are byte-identical to `budget-final/models/`, which the claims verifier asserts. |
| `exploration-lattice/`, `exploration-lattice-cplex/` | The integer-aware GCD controls of that experiment, 576 configurations per solver. |
| `operational-replication/` | The two matched sensitivity reruns of the operational reconstruction: the same 30 instances, policies, gaps and limit under a second seed and under a second solver, 240 runs each, with frozen run tables and the comparison against the reconstruction. |
| `application-budgets/` | The declared residual contract applied to the 4,320 interpretable rows of one dispatch instance, with the exported model itself, its provenance, and the sweep that tightens the declared budgets to find where each kernel stops being admissible. Regenerated by `make research-application-budgets`; `make research-application-export` re-exports the model from the instance and compares it byte by byte. |
| `operational/` | Authoritative reconstruction of 240 historical dispatch runs, with recovered native logs, input hashes, fixed-pool PAR10, conditional completed-run Work summaries, and residual diagnostics. These are reconstructed observations, not new optimizer runs. |
| `budget-pilot/`, `budget-confirmatory/`, `budget-confirmatory-v2/` | Earlier stress runs, retained for provenance. The initial endpoint implementation and later correction give different results; these folders must not be substituted for `budget-final/`. |
| `identifiability-confirmatory/` | Earlier matrix export with the old serializer; retained to expose the effect of representation changes. |

`budget-final/protocol.json` and `budget-final-cplex/protocol.json` record versions, seeds,
settings, methods and source hashes. The independent checker verifies the complete Cartesian configuration grid,
all 96 enumerated optima and stored acceptance labels, 768 exact dyadic exports, and
288 justified abstentions. Its current saved-data SHA-256 is
`f0cfa86aa97e60dcca6985dd66b235883ecabafb1fe1f4de40a3b70b39840aa2`
for `budget-final/runs.csv`.

The stress models deliberately approach integer feasibility boundaries and do not
estimate failure rates or runtime on industrial MILPs. A verified binary optimum uses
the paper's declared independent acceptance rule. Abstention is counted separately
from a solve. The dispatch data have no corresponding exact optimality certificate
or application-calibrated residual budgets.

The original paper sources and PDFs are preserved in
`paper/research-audit/baseline-20260908/`; superseded documentation is in its `docs/`
subdirectory. Earlier attribution controls are in
`results-revision/attribution-controls/`. Existing `results/`, `results-revision/`
campaigns, synthetic outputs, old figures, and the original `paper/references.bib`
are historical material unless explicitly referenced by the current manuscript.

## Optional fresh experiments

These commands generate new experiments; they are not needed to verify the saved
results or build the paper. Targets reject an existing output directory, so choose
a new path for each rerun. The rerun defaults are separate from the authoritative data.

The matrix grid uses `DummyLp` and performs **no optimization**:

```bash
make research-grid
# Equivalent, after make audit-build:
python3 scripts/audit_identifiability_grid.py \
    --exe code/build-audit/SistemaElectrico \
    --out results-revision/research-audit/reruns/identifiability-manual \
    --seeds 10 --seed-base 20260909 --roundtrip-export
```

The binary experiment uses the Python solver APIs. The complete recorded protocol
uses HiGHS 1.15.1 and Gurobi 13.0.2; the latter requires a suitable license:

```bash
python3 -m pip install highspy==1.15.1 gurobipy==13.0.2
make research-budget
python3 scripts/research/verify_saved_experiment.py \
    --root results-revision/research-audit/reruns/budget
```

There are up to 3,168 solver calls with a ten-second limit per call in the full run.
To run only the license-free HiGHS arm:

```bash
python3 -m pip install highspy==1.15.1
make research-budget BUDGET_SOLVERS=highs \
    BUDGET_OUT=results-revision/research-audit/reruns/budget-highs
python3 scripts/research/verify_saved_experiment.py \
    --root results-revision/research-audit/reruns/budget-highs
```

A HiGHS-only run has half the planned configurations. The current paper table/plot
script expects both solvers; do not replace the complete paper data with that subset.
For a complete rerun, analyze into a separate output location:

```bash
python3 scripts/research/analyze_budget_experiment.py \
    --root results-revision/research-audit/reruns/budget \
    --figures results-revision/research-audit/reruns/budget/figures \
    --tables results-revision/research-audit/reruns/budget/tables
```

Solver outputs can depend on the versions and platform. Frozen sources identify the
reported implementation; rerunning the current code is a reproduction attempt, not
a promise of identical trajectories or wall times. The matrix analysis script reads
`identifiability-final/` explicitly; a fresh grid produces its own comparison CSVs
and hashes without replacing the manuscript's chosen data.

The original commercial-solver dispatch campaigns and cluster templates remain in
`cluster/`, `environment/solver-notes.md`, and the historical documentation. They are
longer, separate experiments, not dependencies of any current verification target.
`make help` lists current and historical targets. `make analysis-n0` and
`make synthetic-mini` reproduce earlier analyses, not the current paper.

## Repository map and licensing

- `paper/`: current manuscript, supplement, bibliography, generated figures/tables,
  and research audits.
- `scripts/research/`: budget construction, experiment, analysis and independent checker.
- `scripts/audit_identifiability_grid.py`: direct named LP and row-scaling audit.
- `scripts/audit_operational_evidence.py`: reconstruction from saved dispatch records.
- `tests/`: mathematical/numerical checks and C++ serializer integration.
- `code/`: C++ model generator, row preprocessing and retained solver interfaces.
- `data/`, `results/`, `results-revision/`: instances and current/historical evidence.

Code is MIT-licensed ([LICENSE](LICENSE)); data and aggregate results use CC BY 4.0
([DATA_LICENSE.md](DATA_LICENSE.md)). The manuscript is not covered by those licenses;
all rights are reserved pending an explicit manuscript license. It is an unpublished
research draft, not an accepted or submitted-version article.

The pre-existing archive identifier
[10.5281/zenodo.20648950](https://doi.org/10.5281/zenodo.20648950) belongs to the project's
archive history. It does not establish that this local revision has been deposited.
See [CITATION.cff](CITATION.cff) for the current local citation metadata; there is no
journal article DOI for this manuscript.
