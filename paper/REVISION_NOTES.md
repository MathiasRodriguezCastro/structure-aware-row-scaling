# Revision notes — response to the peer-review panel

Manuscript: *Structure-Aware Row Scaling for Block-Structured Mixed-Integer Programs*
(retitled from *Generator-Aware Positive Row Scaling for Block-Structured Engineering MIPs*;
the method name is unified as "structure-aware" throughout).
This file maps each required (R) and suggested (S) revision from the editorial decision to
the concrete change made in the **code**, the **paper**, and the **cluster experiments**.
The released code is frozen at the version that produced the published 12-scenario results;
all new capabilities are **additive** (the original variants are byte-identical without the
new flags, golden regression 23/23), so the existing results remain valid.

Legend: ✅ done · 🔄 campaign running on ClusterUY.

---

## Required revisions

### R1 — Solver-internal-scaling baseline  ✅ (all 12 cells run; CPLEX-Full 0.1% partial)
- **Code:** `configurarSolver --scaleflag <-1..3>` (Gurobi) / `--cplexscale <-1..1>` (CPLEX);
  driver `--scaleflag/--cplexscale`; SLURM `cluster/run_internal_scaling_baseline.slurm`.
- **Data:** `results-revision/r1-internal-scaling/<class>-<solver>-<gap>/` — aware-default
  (5 variants) + base under each internal setting, for all 3 classes × 2 solvers × 2 gaps.
  The CPLEX-Full 0.1% sweep is partial (4-day budget expired; scale=1 missing, scale=0
  truncated) and is declared as such in the paper.
- **Paper:** `tab:internal-scaling` now covers Simple/Full/SG-Ter-Mer at 1%; the 0.1% sweep is
  summarized in text with two honest qualifications: (a) at Full 0.1% the retuned internal
  Gurobi modes (337–353 s) overtake the external rule (388 s); (b) CPLEX Read::Scale=-1 on
  Full looks 10× faster but its claimed-optimal objectives disagree with the default pipeline
  beyond tolerance on 11/33 instances → flagged numerically unreliable (footnote c).
- The presolve-off CPLEX probe now has artifacts: `results-revision/r1-cplex-presolve/{on,off}`.

### R2 — Conditioning↔runtime inconsistency  ✅
- As before (variant-level inversion + weak Spearman + partial-mediator framing), plus:
  the correlations table note now reports the per-variant decomposition (the pooled negative
  association is carried by the Ruiz baselines; structure-aware ≈ 0), which further supports
  the partial-mediator reading. Miltenberger–Ralphs–Steffy and Elble–Sahinidis added as
  precedent citations.

### R3 — Hyperparameter sensitivity  ✅
- As before; canonical CSVs now in `results-revision/r3-hyperparam/simple-gurobi-1pct/`.
  Text range corrected to the table ([2.01,2.12]).

### R4 — Rescope generality / row-only premise  ✅ (unchanged)

### R5 — Operational stage ablation  ✅ (Full class now included)
- `tab:stage-ablation` now reports all three classes at 1% (Full: base 82.55 → local-only
  70.94 vs full rule 71.41; coupling-only 83.69 ≈ base — same attribution). Data in
  `results-revision/r5-ablation/`. The Full 0.1% cell failed in June (Gurobi WLS session
  limit, all-ERROR resumen) and is 🔄 re-running.
- **NEW: role-blind flat control (🔄 running).** The ablation created the obvious objection:
  if the local stage (a per-row geometric-mean kernel computable from the flat matrix)
  carries the runtime effect, is the metadata needed at all? New opt-in `--plano` variant
  applies the same kernel + safeguards to EVERY row with no roles/blocks (single block, no
  β, no coupling stage; byte-identical without the flag, golden 23/23). Campaign
  `results-revision/plano-control/{simple,sgtm}-gurobi-{1pct,01pct}` with variants
  base, estructurado, estructurado_solo_local, estructurado_plano, estructurado_matricial,
  matricial_solo_local, matricial_plano (jobs 5580448–53, chained ≤2 concurrent WLS
  sessions). On completion: if plano ≠ solo-local → metadata isolated as active ingredient;
  if plano ≈ solo-local → rescope the performance claim and anchor the metadata novelty in
  the diagnostics. Over-claiming sentences already moderated in the manuscript.

### R6 — Related-work positioning  ✅
- As before, plus Elble–Sahinidis 2012 (empirical irregularity of LP scaling),
  Miltenberger et al. 2018 (numerics along the B&C tree) and Bergner et al. 2015
  (automatic DW structure detection, cited at the deployability fallback). The absolute
  "flat matrix" claim about modeling languages is now qualified (block-structured
  extensions exist but feed decomposition, not numerical preprocessing).

---

## Suggested revisions

- **S1 (deployability)** ✅ — unchanged; fallback now cites Bergner et al. 2015.
- **S2 (duals)** ✅ — unchanged.
- **S3 (proposition bridge)** ✅ — unchanged.
- **S4 (abstract effect-size language)** ✅ — unchanged; the SG-Ter-Mer single-instance
  PAR10 hedge is now replicated in the 0.1% table notes as well.
- **S5 (partial correlations + missingness)** ✅ — unchanged, plus the per-variant
  correlation decomposition (see R2).

## New in this pass (beyond the panel's letter)

- **Original-scale equivalence audit** (`subsec:original-scale-audit` + tab): the claim-1
  evidence promised by the design is now reported for all 4 operational campaigns, with
  verified explanations of every exceedance (CPLEX-Simple checker behavior matches the
  unscaled base; large-|rhs| absolute residuals at solver tolerance; 72/4806 wrong-optimal
  outliers in both directions, incl. Ruiz claiming gap 0 at grossly suboptimal incumbents).
- **CPLEX tree-level KappaStats** reported (numerical claim now tabulated under both solvers).
- **Performance variability paragraph** in §validity (base drift across campaigns as the
  empirical bound; Full flagged as fragile → within-campaign pairs only).
- Conclusion updated (stage-ablation result integrated; stale future-work item removed).
- All result figures/tables now \cref'd in text; synthetic figures regenerated in English
  (fig2 collapsed to a single panel; fig3 with per-pattern line styles).
- Reproducibility package: repo renamed to `structure-aware-row-scaling` (old URL redirects),
  CITATION.cff/.zenodo.json/README aligned to the new title, manuscript excluded from the
  MIT/CC BY blanket licenses, N3 instructions fixed (XeLaTeX + WileyNJDv5).

## Pending before resubmission
- 🔄 plano-control campaign + R5 Full 0.1% rerun (jobs 5580448–53) → integrate into
  §stage-attribution and finalize the flat-control sentence in the conclusion.
- EIC length trim (~15–20%): planned as the next editing pass (P2), after the new content
  settles.
- Formal point-by-point response letter + latexdiff vs `ef6b96e` (draft in progress).
- Tag v1.1.0 + Zenodo refresh once the campaign data and letter are final.
