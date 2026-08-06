# Editorial reframe — memo

Senior-editor restructuring pass on `main.tex`. No experiment, number, p-value, table, figure,
equation, sample, or reliability criterion was changed. All edits are to prose and section
organization. Deliverables: the clean revised `main.pdf`, the marked-changes `main_reframe_diff.pdf`
(latexdiff vs the pre-reframe commit), this memo, and `REFRAME_CLAIMS.md`.

## What was reframed

The paper now leads with what the study *demonstrates* and treats "non-identifying" as one scoped,
technical qualifier rather than the governing narrative. The governing thesis is two complementary
contributions:

- **(A) Operational.** External generator-level row scaling improves the solver-facing numerical
  diagnostics and, under Gurobi, often improves completed-run time or deterministic effort beyond
  the solver's *own* default internal scaling (which is left enabled) — favorable but class-,
  tolerance-, and solver-dependent, with no robust CPLEX gain.
- **(B) Methodological.** Under identical kernel and identical coverage, block metadata lowers the
  spectral pseudo-condition number by one to two orders of magnitude on the heterogeneous-block
  grid (Table 14) — the metadata's causal, active-regime contribution.

Section-by-section:

- **Abstract.** Rewritten to the intended logical sequence: problem → method → operational result →
  operational interpretation (inactive coupling regime ⇒ gain from local normalization) →
  metadata-causal synthetic result → runtime/reliability caveats → the three-questions lesson.
  "Non-identifying" now appears once, *after* the positive operational result, as a precise scoping
  term.
- **Practitioner Points.** Reordered to the six-point hierarchy: external value first; metadata
  matters specifically under heterogeneous block scales; no activation on balanced coupling rows is
  expected/desirable, not a failure; equal kernel + coverage are prerequisites for attribution;
  prefer the matrix-only rule and verify original-scale; measure conditioning and runtime
  separately. PP1 is no longer a bare "generators have metadata" statement.
- **Introduction.** Restructured to: generators retain structure flat exports discard → solvers
  already scale internally but an external pass changes the representation the pipeline begins on →
  the two research questions (external value beyond internal scaling; metadata value beyond a
  role-blind rule at matched kernel/coverage) → previewed answers → the attribution principle
  (Prop. 3). The contribution list was rewritten to five items in the new order. The dominant
  defensive block ("we are deliberate about what the campaigns can and cannot answer …") was
  replaced by the two-regime framing.
- **Discussion.** Converted from "A first/second/third/fourth objection …" into four conceptual
  subsections: 7.1 External preprocessing beyond solver-internal scaling; 7.2 When metadata adds
  numerical value; 7.3 Conditioning versus runtime; 7.4 Reliability and the recommended variant.
  (Deployability retained as its own subsection.)
- **Limitations.** Re-expressed as scope delimitations; the "the revision responds in three ways /
  what the revision does not yet do" and all review-process references were removed and replaced by
  final-design scope statements. Every real limitation is retained (single domain; inactive
  operational coupling stage; synthetic-only metadata conditioning; solver dependence; single-run
  cells except the seed replication; incomplete initial role map; row-only vs structured column
  scaling; no universal conditioning→runtime link).
- **Conclusion.** Rewritten to answer the four questions explicitly (does external scaling help;
  is the operational gain attributable to metadata; does metadata itself add numerical value; does
  conditioning guarantee speed) and to close on complementarity — the operational study establishes
  practical value, the synthetic study identifies the metadata mechanism — instead of closing on
  "non-identifying."
- **Results.** Opening retoned to lead with the favorable-but-bounded Gurobi pattern (internal
  scaling enabled) and to keep numerical/runtime claims separate; the activation-audit closing now
  points forward to the synthetic test that exercises the mechanism rather than ending on
  "untested." No table, number, or subsection was moved.

## What moved to the Supporting Information

Nothing was physically relocated in this pass. Moving results subsections/tables to the SI is a
larger, cross-reference-sensitive operation that I did not perform because it risks disturbing
numbers and labels, which this pass was constrained not to touch. **Recommended follow-up
candidates** for relocation (they do not carry the three central comparisons): the multiple PAR10
readings beyond the fixed-pool primary, the endpoint-hierarchy exposition, the per-contrast
multiplicity-correction detail, and the cached-metadata/build-invariance sensitivities. Their
summary sentences can stay in the body with the full detail pointed to the SI.

## Repetition removed

- The "three strands of evidence" paragraph in the Introduction was condensed and de-duplicated
  against the new two-regime preview (the fixed-pool PAR10 detail now lives once, in Results/7.1).
- The Discussion previously restated the "flat matches/beats on the global proxy" oracle behavior
  and the conditioning–runtime dissociation in two places each; each is now stated once (7.2 and
  7.3 respectively).
- The coupling-null structural explanation and the synthetic-benchmark "closes part of the gap"
  paragraph were merged into 7.2.

## The three comparisons, kept separate

The reframe makes explicit that three different comparisons answer three different questions, and
they are no longer conflated:

1. **SA vs Base** — practical value of the external preprocessing pass (Base runs Gurobi's default
   internal scaling + presolve). Reported in Results (Gurobi/CPLEX) and 7.1.
2. **SA vs internally tuned Base (ScaleFlag control)** — whether the solver can reproduce the
   external effect internally: tie on Simple, descriptive external advantage on SG-Ter-Mer,
   tolerance-dependent on Full. Reported in the internal-scaling baseline and 7.1.
3. **SA-Mat vs Flat-Mat (same kernel, same coverage)** — the causal value of the metadata: the
   one-to-two-orders spectral conditioning advantage (Table 14, synthetic grid). Reported in the
   synthetic mechanism check / spectral audit and 7.2.

## Inconsistencies

None requiring a number change was introduced or, in the prose touched, found: every numeric anchor
carried into the reframed prose (Table-14 ratios and significance; the 2.06/2.01, 8.83/8.58,
78.9/70.9 s ablation figures; $\widehat\rho\approx3\times10^{-4}$/exactly $1$; the $\approx1.00$
no-presolve median) was copied verbatim from the source text and tables. A full independent
text-vs-table audit of the untouched results tables was outside this pass.
