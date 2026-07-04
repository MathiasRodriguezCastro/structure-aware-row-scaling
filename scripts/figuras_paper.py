#!/usr/bin/env python3
"""Regenerate the paper figures with a unified, publication-quality style.

Reuses the plotting functions of analisis_tesis_preproc.py but applies a
serif / colorblind-safe / despined matplotlib style (via rcParams) that matches
the paper's typography, and writes straight to paper/figs/ with the esc* names
the manuscript references. No analysis logic is changed.

Run from the repository root:
    python3 scripts/figuras_paper.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- unified publication style -------------------------------------------------
# Okabe-Ito colorblind-safe palette (base, SA-Aug, SA-Mat, Ruiz, Ruiz+Cols).
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000"]
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Nimbus Roman", "Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "axes.prop_cycle": plt.cycler(color=PALETTE),
    "grid.color": "0.8",
    "grid.linestyle": ":",
    "grid.linewidth": 0.6,
    "grid.alpha": 0.7,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "legend.handletextpad": 0.4,
    "legend.columnspacing": 1.0,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "lines.linewidth": 1.8,
    "lines.markersize": 5,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "pdf.fonttype": 42,   # embed TrueType (editable text, vector)
})

import analisis_tesis_preproc as A  # noqa: E402  (style must be set before import use)

# English labels to match the manuscript terminology (figures are for an English paper).
A.GRUPO_ORDEN = ["Simple", "Full", "SG-Ter-Mer"]
A.VARIANTE_LABEL = {
    "estructurado": "SA-Aug",
    "estructurado_matricial": "SA-Mat",
    "ruiz": "Ruiz",
    "ruiz_columnas": "Ruiz+Cols",
}

FIGS = ROOT / "paper" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
TIMEOUT = 3600.0

GROUPS = {  # GRUPO_ORDEN names -> result folder per scenario suffix
    "Simple": "validacion-preproc-simple",
    "Full": "validacion-preproc-completo",
    "SG-Ter-Mer": "validacion-preproc-sg-ter-mer",
}

SCENARIOS = [
    # (tag, folder-suffix, is_gurobi)
    ("esc1_gurobi_1pct", "", True),
    ("esc2_gurobi_01pct", "-gap0001", True),
    ("esc3_cplex_1pct", "-cplex-ute", False),
    ("esc4_cplex_01pct", "-cplex-ute-gap0001", False),
]


def load_rows(suffix: str):
    rows = []
    for nombre, base_folder in GROUPS.items():
        folder = base_folder + suffix
        if not (ROOT / "results" / folder).exists():
            print(f"  [skip] sin carpeta: {folder}")
            continue
        rows += A.cargar_grupo(nombre, [folder], ROOT / "results")
    return rows


def main():
    for tag, suffix, is_gurobi in SCENARIOS:
        print(f"== {tag} ==")
        rows = load_rows(suffix)
        if not rows:
            print("  (sin datos, salto)")
            continue
        A.figura_boxplot(rows, FIGS / f"{tag}_boxplot.pdf")
        A.figura_perfil_desempeno(rows, FIGS / f"{tag}_perfil.pdf", TIMEOUT)
        if is_gurobi:  # the manuscript only uses the conditioning scatters for Gurobi
            A.figura_scatter(rows, FIGS / f"{tag}_scatter_rho.pdf",
                             xcol="matrix_kappa_ratio_vs_base",
                             xlabel=r"$\rho_\kappa$ (exported coef.-range ratio)")
            A.figura_scatter(rows, FIGS / f"{tag}_scatter_rhosolver.pdf",
                             xcol="kappa_solver_ratio_vs_base",
                             xlabel=r"$\rho_\kappa^{\mathrm{solver}}$ (solver-level cond. ratio)")
    print("Done -> paper/figs/")


if __name__ == "__main__":
    main()
