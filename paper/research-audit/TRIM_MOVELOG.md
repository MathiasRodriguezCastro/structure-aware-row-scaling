# Length-revision move log

Baseline: commit `108d35e` (main 55 pp, SI 21 pp). **Now: main 49 pp, SI 24 pp**, both compile
with 0 undefined references (343 source lines removed from the main text). Marked-changes version:
`paper/main_diff.pdf` (latexdiff vs the baseline; deletions struck through, additions underlined).

The arc is preserved and now reads: motivation → theory (Props 1–3 + attribution) → SA-Mat as the
recommended method → non-identifying operational evidence → positive synthetic evidence → bounded
conclusion. Guardrails untouched: Props 1–3 and the attribution proposition; §4.3 (SA-Mat);
`tab:reliability`; `tab:spectral-audit`, `tab:metadata-grid`, the stylized model; `tab:flat-control`
(kept in the body with a single main reading); "Restoring exhaustive coverage".

## Mandatory scientific corrections (this round)
- §3.3 and §3.4: the two remaining "role differentiation obtains no conditioning advantage"
  statements replaced by the split-by-rule reading (augmented no advantage; matrix-only
  block-relative advantage under identical coverage).
- Discussion: "Flat was run only with Gurobi" (false) replaced by the CPLEX Flat-control cell
  showing the ordering is not solver-stable; the "metadata is only a selection policy" passage
  now distinguishes the operational row-selection role from the synthetic block-relative effect.
- Conclusion: the fallback no longer says "revert a row" (impossible post-solve) but "reject and
  re-solve"; "safe rule" → "preferred candidate"; "Two things follow for a next version of the
  study" → "Two implications follow from the present evidence".

## Moved to the Supporting Information ("Section S5. Relocated results tables")
Nothing deleted; every moved table is referenced from the body by its new number.

| Table | Was (body) | Now | Body references repointed |
|-------|-----|-----|------|
| Gurobi efficiency, 0.1 % | `tab:robust-gurobi-01pct-mipgap` | **S14** | pointer |
| CPLEX efficiency, 0.1 %  | `tab:robust-cplex-01pct-mipgap`  | **S15** | pointer |
| Internal-scaling (§6.6)  | `tab:internal-scaling` | **S16** | intro + split compound `\cref` |
| Cached-metadata sensitivity | `tab:flat-cached` | **S17** | 4 refs → "Table S17" |
| Component-timing summaries | `tab:flat-absolute` | **S18** | 2 refs → "Table S18" |
| Common-pool reliability | `tab:flat-reliability-body` | **S19** | 5 refs (incl. one compound) → "Table S19" |
| Computational environment | `tab:computational-environment` | **S20** | 1 ref → "Table S20" (final conservative pass) |

SI preamble additions: `siunitx` (+ the main's `\sisetup`) and the
`\methodBase/\methodRuiz/\methodRuizCols/\AvgGap` macros. SI contents paragraph in the main text
updated to "twenty tables" and to announce Sections S3–S5. Removing S17–S19 clears the two
implementation-cost tables that were burying "Restoring exhaustive coverage", so the central R1
result now follows the flat-control table with only a short reliability paragraph between them.

## Compressed in place
| Location | Cut | Note |
|----------|-----|------|
| §4.2 SA-Aug | ~30 lines | all equations kept; surrogate/grid exposition condensed. |
| §6.7 reliability discussion | ~10 lines | per-cell PAR10 detail deferred to Table S9. |
| §6.7 cached-metadata counterfactual | ~14 lines | descriptive-only verdict kept. |
| §6.7 build-invariance audit | ~23 lines | 1204/1224 + last-place-float kept; transfer-factor prose withdrawn. |
| §7 Discussion "second objection" | ~16 lines | kernel/coverage/solver condensed. |
| §9 Conclusion | 7 paragraphs → 4 | title answer / operational shows-and-doesn't / scope / method + next experiment. |

## Deleted outright
None. All detail was moved to the SI or condensed.

## Final conservative pass
- `tab:computational-environment` moved to Table S20; `tab:gurobi-conditioning-correlations`
  **kept in the body** (it directly supports the numerical-vs-runtime separation).
- One redundant "non-identifying" restatement and the "noise floor" mention removed from the
  contributions list only. The abstract, the Practitioner Points, the §6.7 close, and the
  Limitations development were left untouched.

## Stopping point
The paper reads continuously at 49 pp with the arc and all guardrails intact; no further reduction
was attempted, since additional cuts would touch the abstract or the Limitations/Discussion
development.
