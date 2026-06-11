# Toolchain and solver notes

## Compiler / language
- C++17.
- g++ 11.4.0 (Ubuntu 22.04) was used for the reference build. CPLEX 22.1.2 compiles
  cleanly with g++ <= 12; with g++ 13 the IBM Concert headers are pathologically slow,
  so prefer g++ <= 12 when CPLEX is enabled.

## Solvers
- **Gurobi 13.0.1** (`libgurobi130`). Set `GUROBI_HOME` and your Gurobi license via
  the vendor's environment, then `make` in `code/`. Do not commit the license file.
- **IBM ILOG CPLEX 22.1.2.0**. Set `CPLEX_HOME`; ensure the CPLEX runtime and license
  are available per IBM's instructions.
- **Cbc (COIN-OR)**: COIN-OR Cbc (system package; run `cbc --version` for the exact build) . Installed from the system packages
  (`coinor-libcbc-dev`); this is the license-free path (reproduction level N1).
- **Hexaly 14.5** (optional, off by default; `USE_HEXALY=1` to enable).

## Build matrix
```bash
cd code
make                                                  # Gurobi + CPLEX + Cbc
make USE_GUROBI=0 USE_CPLEX=0 USE_CBC=1 USE_HEXALY=0  # license-free (Cbc only)
```

## Python
See `python-requirements.txt`. The analysis scripts use numpy/scipy/pandas/matplotlib.

## LaTeX
TeX Live with the `elsarticle` class and `elsarticle-harv.bst` (e.g. Ubuntu
`texlive-publishers` + `texlive-latex-extra`).
