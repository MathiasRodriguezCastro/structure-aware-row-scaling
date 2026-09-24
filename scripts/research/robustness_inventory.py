#!/usr/bin/env python3
"""Instance inventory for the solver-level robustness campaign.

Hashes every instance of the three 500-instance pools, attaches the generator
metadata of the recombined bank, checks the market demand series, exports the
Base model with the solver-free LP writer to record its dimensions, and looks
for duplicates and overlaps with the historical instances and the 10k pool.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import highspy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from validar_preprocesamiento import clean_instance_text  # noqa: E402

FAMILIES = {"simple": "Simple", "sgtm": "SG-Ter-Mer", "completo": "Full"}
HISTORICAL = {"simple": "entrada-modelo-simple", "sgtm": "entrada-SG-Ter-Mer",
              "completo": "entrada-modelo-completo"}
CLUSTER_POOL = "/clusteruy/home/Grupos/UTE_FING/mathiasr/soluciones_seccion45/{}/instancias/{}"
META = ["seed", "rn_fuente", "sg_fuente", "demanda_fuente", "economia_agua_fuente",
        "costo_falla_fuente", "termica_fuente", "mercado_fuente", "bellman_fuente",
        "huella_semantica_sha256", "es_historica", "validacion_estructural"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def demand_check(text):
    lines = text.splitlines()
    dem = total = None
    for i, line in enumerate(lines):
        if line.startswith("agregarAgente --DemandaFija"):
            dem = np.array(lines[i + 1].split(), dtype=float)
        if line.startswith("crearDespacho --mercado") and "--conDemandaTotal" in line:
            total = np.array(lines[i + 4].split(), dtype=float)
    if dem is None or total is None:
        return "", ""
    return int((dem > total).sum()), float((dem - total).max())


def dims(args):
    path, exe = args
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "base.lp"
        cmds = (f"{clean_instance_text(path)}\n\nconfigurarSolver --DummyLp\n"
                f"preprocesar --solodiagnostico\ngrabar {lp} --noConstante\nsalir\n")
        p = subprocess.run([exe], input=cmds, text=True, cwd=ROOT / "code",
                           capture_output=True, timeout=600)
        if p.returncode or not lp.exists():
            return path.name, {"export_ok": False}
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.readModel(str(lp))
        m = h.getLp()
        kinds = np.array([int(v) for v in m.integrality_]) if len(m.integrality_) else np.zeros(m.num_col_)
        integer = kinds != int(highspy.HighsVarType.kContinuous)
        lo, hi = np.array(m.col_lower_), np.array(m.col_upper_)
        binary = integer & (lo == 0) & (hi == 1)
        a = np.abs(np.array(m.a_matrix_.value_))
        return path.name, {"export_ok": True, "rows": m.num_row_, "cols": m.num_col_,
                           "integer_vars": int(integer.sum()), "binary_vars": int(binary.sum()),
                           "continuous_vars": int((~integer).sum()), "nonzeros": int(a.size),
                           "coef_min": float(a[a > 0].min()), "coef_max": float(a.max())}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    base = ROOT / "results-revision/solver-robustness/inventory"
    ap.add_argument("--raw", type=Path, default=base / "raw")
    ap.add_argument("--out", type=Path, default=base)
    ap.add_argument("--exe", type=Path, default=ROOT / "code/build-audit/SistemaElectrico")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    raw = args.raw
    release = {}
    with (raw / "banco_meta/manifest.csv").open() as fh:
        for r in csv.DictReader(fh):
            release[(r["grupo"], Path(r["archivo"]).name)] = r
    tenk = {line.split()[0] for line in (raw / "banco10k_sha256.txt").read_text().splitlines()}
    hist_clean = {}
    for fam, folder in HISTORICAL.items():
        for p in sorted((ROOT / "data/entradas" / folder).glob("*.txt")):
            hist_clean[sha(clean_instance_text(p).encode())] = f"{folder}/{p.name}"
    paths = [p for fam in FAMILIES for p in sorted((raw / "pools" / fam).glob("*.txt"))]
    with ProcessPoolExecutor(args.workers) as pool:
        dim = dict(pool.map(dims, [(p, str(args.exe)) for p in paths]))
    rows = []
    for p in paths:
        fam = p.parent.name
        data = p.read_bytes()
        rel = release[(fam, p.name)]
        cleaned = sha(clean_instance_text(p).encode())
        over, worst = demand_check(data.decode())
        row = {"family": FAMILIES[fam], "family_key": fam, "instance": p.stem,
               "cluster_path": CLUSTER_POOL.format(fam, p.name), "sha256": sha(data),
               "bytes": len(data), "release_sha256": rel["archivo_sha256"],
               "same_as_release": sha(data) == rel["archivo_sha256"],
               "model_text_sha256": cleaned, "equals_historical": hist_clean.get(cleaned, ""),
               "in_10k_pool": sha(data) in tenk,
               "demand_above_total_hours": over, "max_demand_minus_total": worst}
        row.update({k: rel[k] for k in META})
        row.update(dim[p.name])
        rows.append(row)
    args.out.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    for r in rows:
        fields += [k for k in r if k not in fields]
    with (args.out / "instance-manifest.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    summary = {}
    for fam, label in FAMILIES.items():
        sub = [r for r in rows if r["family_key"] == fam]
        num = lambda k: [r[k] for r in sub if r.get("export_ok")]
        summary[label] = {
            "instances": len(sub), "export_ok": sum(bool(r.get("export_ok")) for r in sub),
            "unique_file_hashes": len({r["sha256"] for r in sub}),
            "unique_model_texts": len({r["model_text_sha256"] for r in sub}),
            "unique_semantic_fingerprints": len({r["huella_semantica_sha256"] for r in sub}),
            "same_as_sealed_release": sum(r["same_as_release"] for r in sub),
            "equal_to_historical_instance": sum(bool(r["equals_historical"]) for r in sub),
            "in_10k_pool": sum(r["in_10k_pool"] for r in sub),
            "instances_with_demand_above_total": sum(1 for r in sub if r["demand_above_total_hours"] not in ("", 0)),
            "validacion_estructural": dict(Counter(r["validacion_estructural"] for r in sub)),
            "dimension_sets_rows_cols_int_bin_count": [
                list(k) + [v] for k, v in Counter((r.get("rows"), r.get("cols"), r.get("integer_vars"),
                                                   r.get("binary_vars")) for r in sub).most_common(3)],
            "nonzeros_range": [min(num("nonzeros")), max(num("nonzeros"))],
            "coefficient_range": [min(num("coef_min")), max(num("coef_max"))],
        }
    summary["pool_10k"] = {"instances": len(tenk)}
    (args.out / "inventory-summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
