# Smoke tests and model signatures

This file records the smoke tests run on the **cleaned reproducibility build** of the
solver platform (the version with the neural-network and Dantzig–Wolfe / column-generation
code removed). The goal is to verify that the **monolithic MIP path** and the
**preprocessing methods** still build and run correctly, and to provide a non-normative
model fingerprint.

## Build

```bash
cd code
make USE_HEXALY=0          # Gurobi + CPLEX + Cbc; Hexaly optional
# binary: build/SistemaElectrico
```

Toolchain used for these results: `g++ 11.4.0`, Gurobi 13.0.1 (`libgurobi130`),
CPLEX 22.1.2.0, Cbc (system COIN-OR). See `../environment/solver-notes.md`.

## Smoke 1 — dispatch model, monolithic path (Gurobi / CPLEX)

Instance: `data/entradas/entrada-modelo-completo/instance001.txt` (model part only;
solver/`resolver` lines appended for the test). `--timeout 20 --mipgap 0.01`.

| Run | `[MODELO]` rows / cols / nnz | Result |
|-----|------------------------------|--------|
| Gurobi, Base (no preprocessing) | 23763 / 16561 / 57555 | `[SOLVE]` emitted, CSV written |
| Gurobi, `Estructurado` (SA-Aug) | 23763 / 16561 / 57555 | preprocessing applied; `[SOLVE]` emitted; objective within MIP gap of Base |
| CPLEX, Base | 23763 / 16561 / 57555 | `[SOLVE]` emitted, CSV written |

The preprocessing path runs end to end and the objective stays within the optimality
tolerance of the unscaled run (equivalence preserved). `instance001` of the *completo*
class is numerically hard, so the 20 s smoke run stops at the time limit — this is
expected and only exercises the code path.

## Smoke 2 — model signature (non-normative fingerprint)

The processed **base** model of `entrada-modelo-completo/instance001.txt` was exported
with the `grabar <file>.lp` command and hashed:

```
rows   = 23763
cols   = 16561
nonzeros = 57555
sha256(model_base.lp) = 74210ee0ad90fcd96fd9fae22428177a0983b6a5d6294965120e56ea4f0c1429
```

> The LP hash is used as a non-normative smoke-test fingerprint. When available, canonical
> model signatures should be preferred: rows, columns, nonzeros, coefficient range,
> objective hash, RHS hash, and bounds hash.

The `.lp` hash can change with solver version, write order, variable/row naming, or
comments, so it is only a practical control, not a formal proof of model identity. The
`[MODELO] rows= cols= nnz=` marker (printed on every `resolver`) is the stable,
solver-independent part of the signature.

## Smoke 3 — synthetic block-structured benchmark (mechanism check)

```bash
cd code
./build/SistemaElectrico < ../data/synthetic/validacion_mini.txt
```

Runs 4 imbalance patterns × 5 variants (`Base, SA-Aug, SA-Mat, Ruiz, Ruiz+Cols`) with
Gurobi and writes `synthetic/resultados/valid/<pattern>_metrics.csv`. Verified:

- All runs report `is_feasible_original_scale = true` with
  `max_original_row_violation` at the order of `1e-14` (algebraic equivalence preserved).
- The generator-aware variants compress the coefficient-range/conditioning proxies, e.g.
  `Base` `kappa_despues = 420.6` vs `SA-Aug` `344.3` on the `none/S0` instance.

## Reproducing these smoke tests

```bash
cd code && make USE_HEXALY=0
# dispatch (Gurobi/CPLEX): build a script = <model part of an instance> + configurarSolver
#   + [habilitarPreprocesamiento Estructurado] + grabar model.lp + resolver out.csv
# synthetic:
./build/SistemaElectrico < ../data/synthetic/validacion_mini.txt
```
