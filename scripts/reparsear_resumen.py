#!/usr/bin/env python3
"""Regenera resumen.csv (+ reporte.html) de una corrida de validar_preprocesamiento
RE-PARSEANDO los logs/CSV ya existentes, SIN volver a resolver ningún MIP.

Útil cuando se enriquece el parser o la clasificación de equivalencia y se quiere
actualizar los agregados de corridas ya hechas (p.ej. en el cluster) sin pagar de
nuevo el tiempo de solver.

Uso:
    python3 utils/reparsear_resumen.py ejecuciones/validacion-preproc-simple-ute
    python3 utils/reparsear_resumen.py OUT1 OUT2 ...   # varias carpetas
"""
from __future__ import annotations

import argparse
import csv as _csv
from pathlib import Path

import validar_preprocesamiento as vp

# Campos derivados de los CSV (no del log) que se conservan al re-parsear solo logs.
_CSVOK_FIELDS = ("objetivo_post", "equivalente_vs_base", "max_diff_post_csv",
                 "diffs_post_csv", "status")


def _cargar_csvok(old_csv: Path) -> dict[tuple[str, str], dict]:
    """Lee equivalente_vs_base / max_diff_post_csv / ... de un resumen.csv viejo."""
    out: dict[tuple[str, str], dict] = {}
    if not old_csv.exists():
        return out
    with old_csv.open(encoding="utf-8", errors="ignore") as f:
        for r in _csv.DictReader(f):
            inst = _norm_inst(r.get("instancia", ""))
            out[(inst, r.get("variante", ""))] = r
    return out


def _norm_inst(nombre: str) -> str:
    """Normaliza el nombre de instancia para emparejar logs (sin extensión) con el
    resumen viejo (que la guarda con .txt)."""
    return nombre[:-4] if nombre.endswith(".txt") else nombre


def _split_stem(stem: str) -> tuple[str, str] | None:
    """Separa '<instancia>_<variante>' usando las variantes conocidas (la más larga
    primero, porque 'ruiz_columnas' contiene 'ruiz' y un guion bajo)."""
    for v in sorted(vp.VARIANT_FLAGS, key=len, reverse=True):
        suf = "_" + v
        if stem.endswith(suf):
            return stem[: -len(suf)], v
    return None


def reparsear(out_dir: Path, salida: Path | None = None,
              merge_csvok: Path | None = None) -> int:
    logs = out_dir / "logs"
    resultados = out_dir / "resultados"
    if not logs.is_dir():
        print(f"[aviso] sin carpeta logs/: {out_dir}")
        return 0
    # Si resultados/ no está local (logs-only), se conservan los campos de CSV del
    # resumen.csv viejo (CSV OK es reproducibilidad, no se recomputa sin los CSV).
    csvok = _cargar_csvok(merge_csvok) if merge_csvok else {}
    tiene_resultados = resultados.is_dir()

    rows: list[vp.RunSummary] = []
    for log_path in sorted(logs.glob("*.log")):
        sp = _split_stem(log_path.stem)
        if sp is None:
            continue
        instancia, variante = sp
        csv_path = resultados / f"{instancia}_{variante}.csv"
        csv_post = vp.post_csv_path(csv_path)
        base_post = resultados / f"{instancia}_base_postprocesado.csv"
        rc = 0 if (csv_post.exists() or not tiene_resultados) else 1
        summary = vp.summarize(
            Path(instancia), variante, rc, csv_path, log_path,
            base_post if base_post.exists() else None,
            tol=1e-7, tol_factibilidad=1e-4, tol_objetivo=1e-3,
        )
        if not tiene_resultados:
            # status real: hubo solución si el log trae objetivo del solver.
            summary.status = "OK" if summary.objetivo_solver is not None else "ERROR"
            old = csvok.get((instancia, variante))
            if old:
                for k in _CSVOK_FIELDS:
                    v = old.get(k)
                    if v in (None, ""):
                        continue
                    if k in ("equivalente_vs_base", "status"):
                        setattr(summary, k, v)            # strings tal cual
                    elif k == "diffs_post_csv":
                        try: setattr(summary, k, int(float(v)))
                        except ValueError: pass
                    else:                                  # objetivo_post, max_diff_post_csv: float
                        try: setattr(summary, k, float(v))
                        except ValueError: pass
        rows.append(summary)
    if not rows:
        print(f"[aviso] sin logs parseables en {out_dir}")
        return 0
    dest = salida or (out_dir / "resumen.csv")
    vp.write_summary_csv(rows, dest)  # llama a add_relative_metrics
    n_inst = len({r.instancia for r in rows})
    print(f"[ok] {out_dir}: {len(rows)} filas ({n_inst} instancias) -> {dest}")
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dirs", nargs="+", type=Path, help="Carpetas con logs/ (y resultados/).")
    ap.add_argument("--salida", type=Path, default=None,
                    help="Ruta del resumen.csv de salida (def: <out_dir>/resumen.csv).")
    ap.add_argument("--merge-csvok", type=Path, default=None,
                    help="resumen.csv viejo del que copiar CSV OK/obj_post cuando falta resultados/.")
    args = ap.parse_args()
    for d in args.out_dirs:
        reparsear(d, args.salida, args.merge_csvok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
