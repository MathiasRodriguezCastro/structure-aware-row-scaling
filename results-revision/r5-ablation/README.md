# Historical stage ablation

The runs behind Table S7 of Online Resource 1 and the paragraph on stage attribution in the
article's discussion. They belong to the **earlier preprocessing campaign**, not to the policy
set of the current manuscript, and are reported there as exploratory evidence about solver
effort.

## What was run

The structured rules of that campaign had three conceptual stages: local-row normalization,
block-scale construction and coupling-row scaling. The ablation kept either the local stage
alone or the coupling stage alone and compared them with Base and the full rule on the same
instance banks. Variant names in the CSVs:

| Variant | Stage |
|---|---|
| `base` | no scaling |
| `estructurado` | the structured rule, all stages |
| `estructurado_solo_local` | local-row normalization only |
| `estructurado_solo_acoplamiento` | coupling-row scaling only |
| `estructurado_matricial` | the matrix rule, all stages |
| `matricial_solo_local`, `matricial_solo_acoplamiento` | its two stages |

Solver Gurobi, relative MIP gaps 1% and 0.1%, one directory per class and gap:
`{simple,sgtm,full}-gurobi-{1pct,01pct}/resumen.csv`, with 204, 68 and 34 instances. The
runner is `cluster/run_stage_ablation.slurm`.

## Regenerating the table

```bash
make research-stage-ablation
```

reads `resumen.csv` in each directory, computes the shifted geometric mean of
`tiempo_solver_s` with a shift of one second, writes `stage-ablation.csv` here and
`paper/tables/stage-ablation.tex`. The numbers in the article come from that script, not from
a transcription.

## What this is not

It is not a rerun of the current policies, it is one solver, and its summary is a typical-time
measure rather than the failure-sensitive endpoint the article uses elsewhere. The attribution
it supports is about which stage a time difference sat in, within that campaign.
