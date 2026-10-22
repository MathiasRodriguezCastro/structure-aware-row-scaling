# Operations Research Forum manuscript

Current editorial version: **v1.5.1-orf-submission**.

**Accuracy-Aware Row Scaling for Generated Mixed-Integer Programs: A Computational
and Software Study** — Mathias Rodríguez Castro.

Run `make paper` from the repository root. The main PDF is `main_orf.pdf`;
`ESM_1.pdf` is Online Resource 1 and `cover-letter.pdf` is the new ORF letter.
The publisher class and numeric bibliography style are retained unmodified;
see [template provenance](TEMPLATE_PROVENANCE.md).

The ORF adaptation leads with accuracy-aware model generation and verification,
followed by computational evaluation and mechanism attribution. It adds practical
interpretation of original-unit budgets, returned-point checks and preparation
overhead. Mathematical statements, proofs, experimental records and numerical
tables are preserved. A separate prospective within-family study adds 24 new parameter scenarios, 360 primary MIP calls plus 360 logging confirmations and 96 rational LP attempts; known parent data and plant structure are retained. See `exploration/orf-confirmatory-20261018/RESULTADOS.md` for all outcomes and qualifications.

`editorial/` contains the canonical ORF abstract, opening, workflow figure, concise discussion, prospective results, export-error accounting, practical implications,
availability and reproduction instructions. `scripts/research/build_orf.py` applies
them to the preserved scientific body in `paper/main.tex`, generates
`main_orf.tex` and `ESM_1.tex`, and copies shared inputs. Edit those editorial
fragments or the shared scientific source, rather than the generated mirrors.
The self-contained editable source ZIP includes the generated complete TeX files.

The current data archive is Online Resource 2. It contains the **exact** previously
audited `v1.3.17-oms-submission` scientific-evidence ZIP, its validation report, the
current ORF sources and an inheritance record. Its historical internal names are
preserved. This keeps scientific replay separate from the current editorial
format. The frozen OMS delivery remains unchanged.

See [submission preparation](../submission/orf/README.md). The current local
snapshot has no separately assigned Zenodo DOI; the historical baseline DOI does
not identify the later experiments. No journal submission has been performed.

The 19 October logging amendment retains the first campaign and adds a complete
360-call native-trace confirmation. These are repeated assignments, with no new
models or seeds. Both sets of points are independently checked.

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
The separate later 3,840-run campaign remains in its research report and is not
included in this editorial snapshot or its scientific result counts.
