# Reconstructed final operational campaign

All four variants are retained on the assigned pool (15 instances per cell). Work comes from the native Gurobi log, at 0.01-unit resolution. The historical scaled Work marker was rounded to integers; zero is a rounding artifact, not a zero-cost solve.

PAR10 below is the arithmetic mean of solver seconds with 18,000 seconds per non-completion. Work ratios use the same all-variants-completed pool within each cell and are secondary, conditional summaries. The confidence intervals are exploratory paired bootstrap intervals; the small pools and influential timeouts prevent a general superiority or equivalence claim.

| Cell | Variant | Completed | PAR10 seconds | Absolute residual max | Activity residual max |
|---|---|---:|---:|---:|---:|
| gurobi_sgtm_01pct | Base | 15/15 | 134.08 | 2.38e-07 | 8.14e-11 |
| gurobi_sgtm_01pct | Flat-GM | 14/15 | 1216.24 | 5.72e-06 | 1.75e-13 |
| gurobi_sgtm_01pct | Flat-L2 | 14/15 | 1216.05 | 0.001 | 4.42e-11 |
| gurobi_sgtm_01pct | Role-Hybrid | 14/15 | 1216.91 | 0.000553 | 7.21e-11 |
| gurobi_sgtm_1pct | Base | 15/15 | 116.15 | 2.38e-07 | 8.14e-11 |
| gurobi_sgtm_1pct | Flat-GM | 14/15 | 1216.51 | 4.96e-05 | 1.75e-13 |
| gurobi_sgtm_1pct | Flat-L2 | 14/15 | 1217.60 | 0.001 | 4.42e-11 |
| gurobi_sgtm_1pct | Role-Hybrid | 14/15 | 1217.34 | 1.91e-06 | 1.27e-11 |
| gurobi_simple_01pct | Base | 15/15 | 52.00 | 9e-06 | 1.25e-07 |
| gurobi_simple_01pct | Flat-GM | 15/15 | 72.98 | 0.0019 | 1.19e-06 |
| gurobi_simple_01pct | Flat-L2 | 15/15 | 33.17 | 0.000429 | 4.02e-07 |
| gurobi_simple_01pct | Role-Hybrid | 15/15 | 72.63 | 0.0019 | 1.19e-06 |
| gurobi_simple_1pct | Base | 15/15 | 11.90 | 9e-06 | 1.25e-07 |
| gurobi_simple_1pct | Flat-GM | 15/15 | 2.12 | 6.27e-05 | 1.38e-07 |
| gurobi_simple_1pct | Flat-L2 | 15/15 | 20.44 | 4.97 | 4.02e-07 |
| gurobi_simple_1pct | Role-Hybrid | 15/15 | 2.11 | 6.27e-05 | 1.38e-07 |

| Cell | Contrast | Common completed n | Work GM ratio [95% CI] | Rounding-only bounds |
|---|---|---:|---:|---:|
| gurobi_sgtm_01pct | Flat-GM/Base | 14 | 0.682 [0.470, 0.925] | [0.675, 0.690] |
| gurobi_sgtm_01pct | Flat-L2/Base | 14 | 0.802 [0.649, 0.980] | [0.793, 0.811] |
| gurobi_sgtm_01pct | Role-Hybrid/Base | 14 | 0.726 [0.476, 1.005] | [0.718, 0.734] |
| gurobi_sgtm_1pct | Flat-GM/Base | 14 | 0.698 [0.486, 0.944] | [0.690, 0.707] |
| gurobi_sgtm_1pct | Flat-L2/Base | 14 | 0.863 [0.721, 1.030] | [0.853, 0.873] |
| gurobi_sgtm_1pct | Role-Hybrid/Base | 14 | 0.744 [0.487, 1.036] | [0.736, 0.753] |
| gurobi_simple_01pct | Flat-GM/Base | 15 | 1.063 [0.889, 1.247] | [1.059, 1.067] |
| gurobi_simple_01pct | Flat-L2/Base | 15 | 1.385 [0.903, 2.331] | [1.381, 1.390] |
| gurobi_simple_01pct | Role-Hybrid/Base | 15 | 1.063 [0.894, 1.245] | [1.059, 1.067] |
| gurobi_simple_1pct | Flat-GM/Base | 15 | 0.631 [0.312, 1.032] | [0.627, 0.634] |
| gurobi_simple_1pct | Flat-L2/Base | 15 | 1.792 [1.033, 3.542] | [1.783, 1.801] |
| gurobi_simple_1pct | Role-Hybrid/Base | 15 | 0.631 [0.314, 1.033] | [0.627, 0.634] |

The 4.9704 original-scale residual on caso46e (Flat-L2, 1%) belongs to an equality with zero RHS. Its RHS-normalized diagnostic divides by 1; interpreting it as a 497% physical error is invalid. The maximum activity-normalized diagnostic in that run is 1.15e-7. Both scales must be reported until application tolerances are justified.

The native Work summaries are still rounded. Equal Work at 0.01 resolution, or equal node counts, is not proof of identical trajectories or matrices. Model-equivalence claims require direct matrix/row-factor comparisons.
