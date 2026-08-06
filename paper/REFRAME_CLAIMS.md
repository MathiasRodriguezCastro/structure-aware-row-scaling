# Claims that could have been overstated, and the prudent wording used

The reframe strengthens the paper's positive framing, so the risk is over-claiming in the new
direction. For each place the two contributions are asserted, the guardrail wording actually used is
recorded below. Nothing on the plan's "do not assert" list is claimed.

| Where | Tempting (too-strong) claim | Prudent wording used |
|---|---|---|
| Abstract, Intro, PP1, Concl. | "External row scaling improves Gurobi performance." | "…**often** improves completed-run time or deterministic effort **in several class--tolerance cells** beyond the **default** internal-scaling pipeline" — favorable and explicitly **class-, tolerance-, and solver-dependent**. |
| Abstract, Intro | "External scaling beats the solver's internal scaling." | Beats **Base** (which has default internal scaling on). Against the *best* internal mode the ScaleFlag control's exact reading is kept: **tie on Simple, descriptive advantage on SG-Ter-Mer, tolerance-dependent on Full**; "no universal dominance over the internal modes is claimed." |
| Abstract, 7.2, Concl. | "Metadata improves conditioning / helps." | Scoped: "**under an identical kernel and identical coverage**", "**spectral pseudo-conditioning**", "**when the blocks … occupy heterogeneous scales**", "negligible when near-homogeneous". Never "metadata accelerates". |
| Abstract, 7.3, Concl. | "Better conditioning yields faster solves." | Explicitly denied: "does not translate into a universal runtime gain"; "conditioning is a distinct numerical contribution whose runtime consequence must be evaluated separately"; the weak Spearman association is retained. |
| 7.1, 7.3, Concl. | "CPLEX just fails to reproduce a real effect." / "CPLEX contradicts the result." | "CPLEX shows **no robust runtime gain**"; "this does **not weaken the numerical claim; it limits the performance claim**." CPLEX is a scope boundary, not a contradiction of the numerics. |
| 7.2, Concl. | "The synthetic experiment proves the method works." | "isolates a **spectral pseudo-conditioning** improvement" — a **numerical** result on **synthetic** instances that "**solve in milliseconds**"; "does not close the performance gap." No runtime claim from the synthetic grid. |
| PP3, 7.2 | "The coupling stage did not help." | Reframed as **expected inactive-regime behavior**: "should not intervene merely because metadata are available; only when the structural scale mismatch is present." Presented as designed behavior, not a failure — but **not** as evidence the stage helps operationally (it is untested there). |
| 7.4, Concl. | "SA-Mat is the safe, faster method." | "the variant we **recommend**" on **cleaner numerical rationale and reliability profile**; runtime "a separate empirical criterion"; SA-Aug's right-hand-side reliability failure retained as the reason. No speed claim for SA-Mat over SA-Aug. |
| Concl. | Close on "the operational comparison is non-identifying." | Closes on **complementarity**: operational study establishes practical value; synthetic study identifies the metadata mechanism. "Non-identifying" kept once, mid-conclusion, as the precise answer to question 2. |
| Abstract | Suppress the non-identifying qualifier entirely. | Kept **once**, **after** the positive operational result, so accuracy is preserved without the qualifier governing the abstract. |

### "Do not assert" checklist (all avoided)
- metadata caused the operational speedup — avoided (gain attributed to local normalization);
- SA-Mat is always faster — avoided (class/tolerance/solver-dependent);
- no worsening anywhere — not claimed;
- a non-significant result proves non-inferiority — not claimed;
- Gurobi cannot reproduce the effect in any class — avoided (class-dependent ScaleFlag reading);
- the condition number predicts runtime — explicitly denied;
- the synthetic experiments demonstrate acceleration — avoided (numerical only);
- the method generalizes to any MIP — avoided (single-domain limitation retained);
- CPLEX contradicts the numerical result — avoided (limits performance claim only).
