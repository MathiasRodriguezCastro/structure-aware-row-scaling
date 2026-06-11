#!/usr/bin/env python3
"""Valida experimentalmente equivalencia e impacto del preprocesamiento.

Ejemplo:
    python3 utils/validar_preprocesamiento.py entradas/entrada-SG-Ter-Mer \
        --solver Gurobi --timeout 120 --mipgap 0.1 --max-instancias 50 \
        --variantes base,estructurado,ruiz_columnas \
        --output ejecuciones/validacion_preprocesamiento
"""

from __future__ import annotations

import argparse
import csv
import html
import math
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

from report_styles import report_document


COMMAND_PREFIXES = (
    "configurarSolver",
    "preprocesar",
    "resolver",
    "grabar",
    "finalizar",
    "salir",
)

VARIANT_FLAGS = {
    "base": "",
    "estructurado": "preprocesar --local-estructurado",
    "estructurado_matricial": "preprocesar --local-matricial",
    "filas": "preprocesar --local-filas",
    "bloque": "preprocesar --local-bloque",
    "ruiz": "preprocesar --local-ruiz --ruiz-iters 4",
    "ruiz_columnas": "preprocesar --local-ruiz --ruiz-iters 4 --columnas-continuas --normalizacion-fisica",
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class RunSummary:
    instancia: str
    variante: str
    status: str
    rc: int
    tiempo_solver_s: float | None = None
    gap_pct: float | None = None
    objetivo_solver: float | None = None          # incumbent reportado por el solver
    objetivo_post: float | None = None
    # --- Desempeño / estado del solver (parseado del log de Gurobi) ---
    status_solver: str | None = None              # OPTIMAL | TIME_LIMIT | INFEASIBLE | ...
    best_bound: float | None = None
    nodos_explorados: float | None = None
    iter_simplex: float | None = None
    presolve_time_s: float | None = None
    rows_cargadas: float | None = None
    cols_cargadas: float | None = None
    nz_cargados: float | None = None
    rows_presolved: float | None = None
    cols_presolved: float | None = None
    nz_presolved: float | None = None
    reduccion_rows_pct: float | None = None        # presolve: (cargadas-presolved)/cargadas
    reduccion_cols_pct: float | None = None
    reduccion_nz_pct: float | None = None
    solver_warnings: int | None = None
    solver_warnings_txt: str | None = None
    # --- Rangos de coeficientes (los 4) y razones variante/base ---
    matrix_min: float | None = None
    matrix_max: float | None = None
    objective_min: float | None = None
    objective_max: float | None = None
    rhs_min: float | None = None
    rhs_max: float | None = None
    bounds_min: float | None = None
    bounds_max: float | None = None
    matrix_range_ratio_vs_base: float | None = None
    objective_range_ratio_vs_base: float | None = None
    rhs_range_ratio_vs_base: float | None = None
    bounds_range_ratio_vs_base: float | None = None
    kappa_antes: float | None = None
    kappa_despues: float | None = None
    rho_antes: float | None = None
    rho_despues: float | None = None
    tiempo_preprocesamiento_s: float | None = None
    tiempo_total_s: float | None = None
    speedup_vs_base: float | None = None
    speedup_solver_vs_base: float | None = None
    speedup_total_vs_base: float | None = None
    overhead_preprocesamiento_vs_base: float | None = None
    ratio_preproc_solver: float | None = None
    gap_delta_vs_base: float | None = None
    obj_solver_delta_vs_base: float | None = None
    obj_solver_rel_delta_vs_base: float | None = None
    obj_post_delta_vs_base: float | None = None
    obj_post_rel_delta_vs_base: float | None = None
    matrix_kappa_ratio_vs_base: float | None = None
    kappa_proxy_ratio: float | None = None
    # Número de condición de la base óptima reportado por el solver (Gurobi Kappa/KappaExact).
    # Distinto de kappa_antes/kappa_despues (estimador de dispersión κ̂ de PreprocesamientoMIP).
    kappa_solver: float | None = None
    kappa_solver_exact: float | None = None
    kappa_solver_ratio_vs_base: float | None = None
    # --- Métricas robustas de eficiencia ([NUM-EFIC]; None en binarios viejos) ---
    work_units: float | None = None        # Gurobi Work (unidades deterministas)
    dettime_ticks: float | None = None     # CPLEX getDetTime (ticks deterministas)
    root_gap: float | None = None          # gap relativo al final del nodo raíz
    root_time: float | None = None         # tiempo de pared al final de la raíz
    tiempo_determinista: float | None = None   # work_units (Gurobi) o dettime_ticks (CPLEX)
    speedup_det_vs_base: float | None = None   # T_det base / T_det variante
    primal_integral: float | None = None       # (1/T)∫ gap(t) dt (marcador [SOLVE])
    # --- Condicionamiento de árbol (CPLEX KappaStats; None en Gurobi y datos viejos) ---
    kappa_arbol_max: float | None = None
    kappa_attention: float | None = None
    kappa_stable_frac: float | None = None
    kappa_suspicious_frac: float | None = None
    kappa_unstable_frac: float | None = None
    kappa_illposed_frac: float | None = None
    kappa_arbol_max_ratio_vs_base: float | None = None
    # --- Equivalencia (MIP OK): basada en la solución del solver desescalada sobre el
    #     modelo ORIGINAL. mip_equivalente es el veredicto rigoroso; post_factible verifica
    #     aparte la solución físicamente postprocesada (paso común a base, no atribuible al
    #     preprocesamiento) para exponer la discrepancia desescalado vs postprocesado. ---
    mip_equivalente: str = "N/D"
    post_factible: str = "N/D"
    solver_max_viol: float | None = None     # max viol. de factibilidad (≤,≥,=,cotas) desescalado
    solver_int_viol: float | None = None     # max viol. de integralidad desescalado
    solver_obj_diff: float | None = None     # |obj_recalc_original - incumbent|
    post_max_viol: float | None = None       # idem sobre la solución postprocesada
    post_int_viol: float | None = None
    # Estadísticos de violación (avg/p95/p99 absolutos y máx RELATIVA). Solo presentes en
    # binarios nuevos (los de esta corrida emiten solo el máximo) -> None en datos actuales.
    verif_solver_avg_viol: float | None = None
    verif_solver_p95_viol: float | None = None
    verif_solver_p99_viol: float | None = None
    verif_solver_max_viol_rel: float | None = None
    verif_post_avg_viol: float | None = None
    verif_post_p95_viol: float | None = None
    verif_post_p99_viol: float | None = None
    verif_post_max_viol_rel: float | None = None
    verif_solver_max_le: float | None = None
    verif_solver_max_ge: float | None = None
    verif_solver_max_eq: float | None = None
    verif_solver_max_lb: float | None = None
    verif_solver_max_ub: float | None = None
    verif_solver_max_int: float | None = None
    verif_solver_viol_le_count: float | None = None
    verif_solver_viol_ge_count: float | None = None
    verif_solver_viol_eq_count: float | None = None
    verif_solver_viol_lb_count: float | None = None
    verif_solver_viol_ub_count: float | None = None
    verif_solver_viol_int_count: float | None = None
    verif_solver_missing: int | None = None
    verif_solver_obj_original: float | None = None
    verif_post_max_le: float | None = None
    verif_post_max_ge: float | None = None
    verif_post_max_eq: float | None = None
    verif_post_max_lb: float | None = None
    verif_post_max_ub: float | None = None
    verif_post_max_int: float | None = None
    verif_post_viol_le_count: float | None = None
    verif_post_viol_ge_count: float | None = None
    verif_post_viol_eq_count: float | None = None
    verif_post_viol_lb_count: float | None = None
    verif_post_viol_ub_count: float | None = None
    verif_post_viol_int_count: float | None = None
    verif_post_missing: int | None = None
    verif_post_obj_original: float | None = None
    # --- Calidad de solución vs base (objetivo en ESCALA ORIGINAL recomputado) ---
    obj_original_variante: float | None = None
    abs_obj_diff_vs_base: float | None = None
    rel_obj_diff_vs_base: float | None = None
    sentido_obj_vs_base: str | None = None   # "mejora" | "empeora" | "igual" (minimización)
    best_bound_delta_vs_base: float | None = None
    equivalente_vs_base: str = "N/D"
    max_diff_post_csv: float | None = None
    diffs_post_csv: int | None = None
    csv: str = ""
    csv_post: str = ""
    log: str = ""


def clean_instance_text(path: Path) -> str:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw.strip()
        if not stripped:
            lines.append(raw)
            continue
        if stripped.startswith(COMMAND_PREFIXES):
            continue
        lines.append(raw)
    return "\n".join(lines).strip()


def is_instance_file(path: Path) -> bool:
    if not path.is_file() or path.name.startswith("."):
        return False
    if path.suffix in {".py", ".csv", ".log", ".lp", ".html"}:
        return False
    try:
        with path.open(encoding="utf-8", errors="ignore") as f:
            for _ in range(25):
                line = f.readline()
                if not line:
                    break
                if line.strip().startswith("inicializar"):
                    return True
    except OSError:
        return False
    return False


def discover_instances(inputs: list[Path], max_instances: int | None) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            files.extend(sorted(p for p in item.glob("**/*") if is_instance_file(p)))
        elif is_instance_file(item):
            files.append(item)
    unique = sorted(dict.fromkeys(p.resolve() for p in files))
    if max_instances is not None:
        unique = unique[:max_instances]
    return unique


def variant_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def build_script(instance: Path, solver: str, timeout: float, mipgap: float,
                 variant: str, csv_path: Path, verificar_original: bool = False) -> str:
    base = clean_instance_text(instance)
    prep = VARIANT_FLAGS[variant]
    if verificar_original:
        if prep:
            prep = f"{prep} --verificar-original"
        else:
            # Variante 'base': snapshotear y verificar SIN escalar el modelo, para que su
            # solución postprocesada también se contraste con la formulación original.
            prep = "preprocesar --solodiagnostico --verificar-original"
    lines = [
        base,
        "",
        f"configurarSolver --{solver} --timeout {timeout:g} --mipgap {mipgap:g}",
    ]
    if prep:
        lines.append(prep)
    lines.append(f"resolver --noConstante {csv_path}")
    lines.append("salir")
    return "\n".join(lines) + "\n"


def run_case(exe: Path, instance: Path, solver: str, timeout: float, mipgap: float,
             variant: str, csv_path: Path, log_path: Path, force: bool,
             verificar_original: bool = False) -> int:
    if not force and csv_path.exists() and post_csv_path(csv_path).exists() and log_path.exists():
        return 0
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    script = build_script(instance, solver, timeout, mipgap, variant, csv_path, verificar_original)
    # Margen sobre el timeout del solver para el trabajo posterior del binario
    # (postprocesamiento, verificación y medición de κ del solver). Generoso para no
    # cortar antes de que el binario escriba su CSV en instancias grandes.
    margen = max(timeout + 300.0, 180.0)
    try:
        proc = subprocess.run(
            [str(exe)],
            input=script,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(exe.parent.parent),
            timeout=margen,
            check=False,
        )
        log_path.write_text(proc.stdout or "", encoding="utf-8")
        return proc.returncode
    except subprocess.TimeoutExpired as e:
        # El binario excedió el margen externo: se registra lo capturado y se CONTINÚA
        # con el siguiente caso (una instancia lenta no debe abortar todo el grupo).
        salida = e.output if isinstance(e.output, str) else (
            e.output.decode("utf-8", "ignore") if e.output else "")
        log_path.write_text(salida + f"\n[VALIDAR] TIMEOUT externo tras {margen:.0f}s\n",
                            encoding="utf-8")
        return 124


def post_csv_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_postprocesado{path.suffix}")


def parse_float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_range(line: str) -> tuple[float | None, float | None]:
    m = re.search(r"\[([0-9.eE+-]+),\s*([0-9.eE+-]+)\]", line)
    if not m:
        return None, None
    return parse_float(m.group(1)), parse_float(m.group(2))


VERIF_RE = re.compile(
    r"\[VERIF ORIGINAL\] etapa=(\S+).*?"
    r"max_le=([0-9.eE+-]+).*?"
    r"max_ge=([0-9.eE+-]+).*?"
    r"max_eq=([0-9.eE+-]+).*?"
    r"max_lb=([0-9.eE+-]+).*?"
    r"max_ub=([0-9.eE+-]+).*?"
    r"max_int=([0-9.eE+-]+).*?"
    # avg/p95/p99/max_viol_rel: opcionales (solo binarios nuevos los emiten).
    r"(?:avg_viol=([0-9.eE+-]+).*?p95_viol=([0-9.eE+-]+).*?"
    r"p99_viol=([0-9.eE+-]+).*?max_viol_rel=([0-9.eE+-]+).*?)?"
    r"viol_le_count=(\d+).*?"
    r"viol_ge_count=(\d+).*?"
    r"viol_eq_count=(\d+).*?"
    r"viol_lb_count=(\d+).*?"
    r"viol_ub_count=(\d+).*?"
    r"viol_int_count=(\d+).*?"
    r"missing_values=([0-9]+).*?"
    r"obj_original_recalc=([0-9.eE+-]+)"
)


def read_objective_post(csv_post: Path) -> float | None:
    if not csv_post.exists():
        return None
    for line in csv_post.read_text(encoding="utf-8", errors="ignore").splitlines()[:5]:
        if line.startswith("Valor de la función objetivo post-procesado:"):
            return parse_float(line.split(":", 1)[1].strip())
    return None


def parse_log(log_path: Path) -> dict[str, float | str | None]:
    if not log_path.exists():
        return {}
    text = ANSI_RE.sub("", log_path.read_text(encoding="utf-8", errors="ignore"))
    data: dict[str, float | str | None] = {}
    # Incumbent, best bound y gap final (línea de cierre de Gurobi).
    m = re.search(r"Best objective\s+([0-9.eE+-]+), best bound\s+([0-9.eE+-]+), gap\s+([0-9.]+)%", text)
    if m:
        data["objetivo_solver"] = parse_float(m.group(1))   # incumbent
        data["best_bound"] = parse_float(m.group(2))
        data["gap_pct"] = parse_float(m.group(3))
    # Nodos B&B, iteraciones símplex y tiempo (toma el PRIMER 'Explored' = solve principal,
    # no el LP de κ posterior).
    m = re.search(r"Explored\s+(\d+)\s+nodes?\s+\((\d+)\s+simplex iterations?\)\s+in\s+([0-9.]+)\s+seconds", text)
    if m:
        data["nodos_explorados"] = parse_float(m.group(1))
        data["iter_simplex"] = parse_float(m.group(2))
        data["tiempo_solver_s"] = parse_float(m.group(3))
    elif (m := re.search(r"Explored .* in\s+([0-9.]+)\s+seconds", text)):
        data["tiempo_solver_s"] = parse_float(m.group(1))

    # Estado del solver (orden de prioridad).
    if re.search(r"Model is infeasible", text):
        data["status_solver"] = "INFEASIBLE"
    elif re.search(r"Model is unbounded", text):
        data["status_solver"] = "UNBOUNDED"
    elif re.search(r"Optimal solution found", text):
        data["status_solver"] = "OPTIMAL"
    elif re.search(r"Time limit reached", text):
        data["status_solver"] = "TIME_LIMIT"
    elif "objetivo_solver" in data:
        data["status_solver"] = "SUBOPTIMAL"

    # Tamaño del modelo cargado y tras el presolve de Gurobi (PRIMER match = solve principal).
    m = re.search(r"Optimize a model with\s+(\d+)\s+rows?,\s+(\d+)\s+columns?\s+and\s+(\d+)\s+nonzeros", text)
    if m:
        data["rows_cargadas"], data["cols_cargadas"], data["nz_cargados"] = (
            parse_float(m.group(1)), parse_float(m.group(2)), parse_float(m.group(3)))
    m = re.search(r"Presolved:\s+(\d+)\s+rows?,\s+(\d+)\s+columns?,\s+(\d+)\s+nonzeros", text)
    if m:
        data["rows_presolved"], data["cols_presolved"], data["nz_presolved"] = (
            parse_float(m.group(1)), parse_float(m.group(2)), parse_float(m.group(3)))
    m = re.search(r"Presolve time:\s+([0-9.]+)s", text)
    if m:
        data["presolve_time_s"] = parse_float(m.group(1))

    # --- Equivalentes para CPLEX (su log NO usa el formato de Gurobi) ---
    # Tamaño ORIGINAL: marcador solver-agnóstico [MODELO] del binario (fallback si el log de
    # Gurobi no lo trajo). Tamaño PRESOLVED y tiempo de presolve: del log de CPLEX.
    m = re.search(r"\[MODELO\]\s+rows=(\d+)\s+cols=(\d+)\s+nnz=(\d+)", text)
    if m:
        if data.get("rows_cargadas") is None:
            data["rows_cargadas"] = parse_float(m.group(1))
        if data.get("cols_cargadas") is None:
            data["cols_cargadas"] = parse_float(m.group(2))
        if data.get("nz_cargados") is None:
            data["nz_cargados"] = parse_float(m.group(3))
    if data.get("nz_presolved") is None:
        m = re.search(r"Reduced MIP has\s+(\d+)\s+rows?,\s+(\d+)\s+columns?,\s+and\s+(\d+)\s+nonzeros", text)
        if m:
            data["rows_presolved"], data["cols_presolved"], data["nz_presolved"] = (
                parse_float(m.group(1)), parse_float(m.group(2)), parse_float(m.group(3)))
    if data.get("presolve_time_s") is None:
        m = re.search(r"Presolve time\s*=\s*([0-9.]+)\s*sec", text)
        if m:
            data["presolve_time_s"] = parse_float(m.group(1))

    # Rangos de coeficientes (PRIMER bloque = modelo principal). Se añade Objective range.
    for clave, etiqueta in (("matrix", "Matrix range"), ("objective", "Objective range"),
                            ("bounds", "Bounds range"), ("rhs", "RHS range")):
        m = re.search(re.escape(etiqueta) + r"\s*\[([0-9.eE+-]+),\s*([0-9.eE+-]+)\]", text)
        if m:
            data[f"{clave}_min"] = parse_float(m.group(1))
            data[f"{clave}_max"] = parse_float(m.group(2))

    # Advertencias numéricas del solver (p.ej. "large bounds", "large matrix coefficient range").
    warns = re.findall(r"^Warning:\s*(.+)$", text, re.MULTILINE)
    data["solver_warnings"] = len(warns)
    if warns:
        data["solver_warnings_txt"] = " | ".join(sorted(set(w.strip() for w in warns)))

    m = re.search(r"rango global\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", text)
    if m:
        data["kappa_antes"] = parse_float(m.group(1))
        data["kappa_despues"] = parse_float(m.group(2))
    m = re.search(r"rho acoplamiento\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", text)
    if m:
        data["rho_antes"] = parse_float(m.group(1))
        data["rho_despues"] = parse_float(m.group(2))

    # κ real de la base reportado por el solver. -1 => no disponible (sin base / saltado).
    m = re.search(r"\[NUM-KAPPA\]\s+kappa_solver=([0-9.eE+\-]+)\s+kappa_exact=([0-9.eE+\-]+)", text)
    if m:
        ks = parse_float(m.group(1))
        ke = parse_float(m.group(2))
        data["kappa_solver"] = ks if (ks is not None and ks >= 0) else None
        data["kappa_solver_exact"] = ke if (ke is not None and ke >= 0) else None

    # Eficiencia robusta: work (Gurobi) o dettime (CPLEX) + gap/tiempo de raíz. -1 => no disp.
    def _pos(v):  # -1/None => no disponible
        return v if (v is not None and v >= 0) else None
    m = re.search(r"\[NUM-EFIC\]\s+work=([0-9.eE+\-]+)\s+root_gap=([0-9.eE+\-]+)"
                  r"\s+root_time=([0-9.eE+\-]+)", text)
    if m:
        data["work_units"] = _pos(parse_float(m.group(1)))
        data["root_gap"] = _pos(parse_float(m.group(2)))
        data["root_time"] = _pos(parse_float(m.group(3)))
    m = re.search(r"\[NUM-EFIC\]\s+dettime=([0-9.eE+\-]+)\s+root_gap=([0-9.eE+\-]+)"
                  r"\s+root_time=([0-9.eE+\-]+)", text)
    if m:
        data["dettime_ticks"] = _pos(parse_float(m.group(1)))
        if data.get("root_gap") is None:
            data["root_gap"] = _pos(parse_float(m.group(2)))
        if data.get("root_time") is None:
            data["root_time"] = _pos(parse_float(m.group(3)))
    # tiempo determinista unificado (lo que esté disponible según el solver)
    data["tiempo_determinista"] = (data.get("work_units")
                                   if data.get("work_units") is not None
                                   else data.get("dettime_ticks"))

    # Condicionamiento de árbol (CPLEX KappaStats). -1 => quality no producida.
    m = re.search(r"\[NUM-KAPPA-ARBOL\]\s+kmax=([0-9.eE+\-]+)\s+attention=([0-9.eE+\-]+)"
                  r"\s+stable=([0-9.eE+\-]+)\s+suspicious=([0-9.eE+\-]+)"
                  r"\s+unstable=([0-9.eE+\-]+)\s+illposed=([0-9.eE+\-]+)", text)
    if m:
        data["kappa_arbol_max"] = _pos(parse_float(m.group(1)))
        data["kappa_attention"] = _pos(parse_float(m.group(2)))
        data["kappa_stable_frac"] = _pos(parse_float(m.group(3)))
        data["kappa_suspicious_frac"] = _pos(parse_float(m.group(4)))
        data["kappa_unstable_frac"] = _pos(parse_float(m.group(5)))
        data["kappa_illposed_frac"] = _pos(parse_float(m.group(6)))

    m = re.search(r"\[PREPROC TIME\] variante=(\S+)\s+tiempo_s=([0-9.eE+\-]+)", text)
    if m:
        data["tiempo_preprocesamiento_s"] = parse_float(m.group(2))

    for m in VERIF_RE.finditer(text):
        etapa = m.group(1)
        prefix = "verif_solver" if etapa == "solver_desescalado" else "verif_post"
        data[f"{prefix}_max_le"] = parse_float(m.group(2))
        data[f"{prefix}_max_ge"] = parse_float(m.group(3))
        data[f"{prefix}_max_eq"] = parse_float(m.group(4))
        data[f"{prefix}_max_lb"] = parse_float(m.group(5))
        data[f"{prefix}_max_ub"] = parse_float(m.group(6))
        data[f"{prefix}_max_int"] = parse_float(m.group(7))
        # Grupos 8-11: avg/p95/p99/max_viol_rel (None en binarios viejos).
        data[f"{prefix}_avg_viol"] = parse_float(m.group(8))
        data[f"{prefix}_p95_viol"] = parse_float(m.group(9))
        data[f"{prefix}_p99_viol"] = parse_float(m.group(10))
        data[f"{prefix}_max_viol_rel"] = parse_float(m.group(11))
        data[f"{prefix}_viol_le_count"] = parse_float(m.group(12))
        data[f"{prefix}_viol_ge_count"] = parse_float(m.group(13))
        data[f"{prefix}_viol_eq_count"] = parse_float(m.group(14))
        data[f"{prefix}_viol_lb_count"] = parse_float(m.group(15))
        data[f"{prefix}_viol_ub_count"] = parse_float(m.group(16))
        data[f"{prefix}_viol_int_count"] = parse_float(m.group(17))
        data[f"{prefix}_missing"] = parse_float(m.group(18))
        data[f"{prefix}_obj_original"] = parse_float(m.group(19))

    # Marcador SOLVER-AGNÓSTICO [SOLVE]: tiempo medido + status/gap/nodos/iter/integral primal,
    # válido para Gurobi y CPLEX. SOBRESCRIBE los valores raspados del log (que son formato
    # Gurobi) cuando está presente. -1/DESCONOCIDO => no disponible.
    m = re.search(r"\[SOLVE\]\s+tiempo_solver_s=([0-9.eE+\-]+)\s+status=(\S+)\s+gap=([0-9.eE+\-]+)"
                  r"\s+obj=([0-9.eE+\-]+)\s+best_bound=([0-9.eE+\-]+)\s+nodos=([0-9.eE+\-]+)"
                  r"\s+iter=([0-9.eE+\-]+)\s+primal_integral=([0-9.eE+\-]+)", text)
    if m:
        data["tiempo_solver_s"] = parse_float(m.group(1))
        if m.group(2) not in ("DESCONOCIDO", "OTRO"):
            data["status_solver"] = m.group(2)
        data["gap_pct"] = _pos(parse_float(m.group(3)))
        data["objetivo_solver"] = parse_float(m.group(4))
        data["best_bound"] = parse_float(m.group(5))
        data["nodos_explorados"] = _pos(parse_float(m.group(6)))
        data["iter_simplex"] = _pos(parse_float(m.group(7)))
        data["primal_integral"] = _pos(parse_float(m.group(8)))
    return data


def read_values(csv_path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    if not csv_path.exists():
        return values
    for line in csv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if " = " not in line:
            continue
        name, raw = line.split(" = ", 1)
        try:
            values[name.strip()] = float(raw.strip())
        except ValueError:
            pass
    return values


def compare_post_csv(base: Path, other: Path, tol: float) -> tuple[str, float | None, int | None]:
    base_values = read_values(base)
    other_values = read_values(other)
    if not base_values or not other_values:
        return "N/D", None, None
    keys = sorted(set(base_values) & set(other_values))
    max_diff = 0.0
    diffs = 0
    for key in keys:
        diff = abs(base_values[key] - other_values[key])
        if diff > tol:
            diffs += 1
            max_diff = max(max_diff, diff)
    return ("OK" if diffs == 0 else "DIFIERE"), max_diff, diffs


# Tolerancia de integralidad (separada de la de factibilidad de restricciones).
TOL_INTEGRALIDAD = 1e-5


def _verif_etapa(summary: RunSummary, prefix: str):
    """(max_viol_factibilidad, viol_integralidad, obj_recalc_original, missing) de una etapa.
    La factibilidad agrupa restricciones (≤,≥,=) y cotas (lb,ub); la integralidad va aparte."""
    g = lambda s: getattr(summary, f"{prefix}_{s}", None)
    feas = [g("max_le"), g("max_ge"), g("max_eq"), g("max_lb"), g("max_ub")]
    if any(v is None for v in feas):
        return None, None, None, None
    return (max(v or 0.0 for v in feas), g("max_int") or 0.0,
            g("obj_original"), g("missing"))


def classify_equivalence(summary: RunSummary, prefix: str, incumbent: float | None,
                         tol_fact: float, tol_obj: float, tol_int: float = TOL_INTEGRALIDAD):
    """Veredicto OK/REVISAR/N/D evaluando la solución (etapa prefix) sobre el modelo
    ORIGINAL: factibilidad de restricciones < tol_fact, integralidad < tol_int, y
    |obj recomputado en escala original - incumbent del solver| < tol_obj. NO usa CSVs."""
    max_feas, int_viol, obj_recalc, missing = _verif_etapa(summary, prefix)
    if max_feas is None or obj_recalc is None or incumbent is None:
        return "N/D", max_feas, int_viol, None
    obj_diff = abs(obj_recalc - incumbent)
    ok = (max_feas <= tol_fact and int_viol <= tol_int and obj_diff <= tol_obj
          and (missing or 0) == 0)
    return ("OK" if ok else "REVISAR"), max_feas, int_viol, obj_diff


def summarize(instance: Path, variant: str, rc: int, csv_path: Path, log_path: Path,
              base_post: Path | None, tol: float,
              tol_factibilidad: float, tol_objetivo: float) -> RunSummary:
    csv_post = post_csv_path(csv_path)
    parsed = parse_log(log_path)
    status = "OK" if rc == 0 and csv_post.exists() else "ERROR"
    summary = RunSummary(
        instancia=instance.name,
        variante=variant,
        status=status,
        rc=rc,
        objetivo_post=read_objective_post(csv_post),
        csv=str(csv_path),
        csv_post=str(csv_post),
        log=str(log_path),
    )
    for key, value in parsed.items():
        setattr(summary, key, value)

    # Reducción del presolve de Gurobi (cargado -> presolved).
    def _red(carg, pres):
        if carg and pres is not None and carg > 0:
            return 100.0 * (carg - pres) / carg
        return None
    summary.reduccion_rows_pct = _red(summary.rows_cargadas, summary.rows_presolved)
    summary.reduccion_cols_pct = _red(summary.cols_cargadas, summary.cols_presolved)
    summary.reduccion_nz_pct = _red(summary.nz_cargados, summary.nz_presolved)

    # --- Equivalencia rigurosa sobre el modelo ORIGINAL (no usa CSVs) ---
    inc = summary.objetivo_solver
    if variant == "base":
        summary.mip_equivalente = "BASE"
        summary.post_factible = "BASE"
    else:
        v, mv, iv, od = classify_equivalence(summary, "verif_solver", inc,
                                             tol_factibilidad, tol_objetivo)
        summary.mip_equivalente = v
        summary.solver_max_viol, summary.solver_int_viol, summary.solver_obj_diff = mv, iv, od
        pv, pmv, piv, _ = classify_equivalence(summary, "verif_post", inc,
                                               tol_factibilidad, tol_objetivo)
        summary.post_factible = pv
        summary.post_max_viol, summary.post_int_viol = pmv, piv
        # Objetivo de la variante en ESCALA ORIGINAL: el recomputado sobre la solución del
        # solver DESESCALADA (no el postprocesado, que es una reconstrucción física en otras
        # unidades). Si no hay verificación, se cae al incumbent reportado por el solver.
        summary.obj_original_variante = (
            summary.verif_solver_obj_original
            if summary.verif_solver_obj_original is not None
            else summary.objetivo_solver)

    # --- CSV OK: reproducibilidad numérica estricta (NO criterio de correctitud) ---
    if variant == "base":
        summary.equivalente_vs_base = "BASE"
        summary.max_diff_post_csv = 0.0
        summary.diffs_post_csv = 0
    elif base_post is not None and base_post.exists() and csv_post.exists():
        eq, max_diff, diffs = compare_post_csv(base_post, csv_post, tol)
        summary.equivalente_vs_base = eq
        summary.max_diff_post_csv = max_diff
        summary.diffs_post_csv = diffs
    return summary


def add_relative_metrics(rows: list[RunSummary]) -> None:
    by_instance: dict[str, dict[str, RunSummary]] = {}
    for row in rows:
        by_instance.setdefault(row.instancia, {})[row.variante] = row

    for variants in by_instance.values():
        base = variants.get("base")
        if base is None:
            continue
        for row in variants.values():
            if row.variante == "base":
                row.speedup_vs_base = 1.0
                row.speedup_solver_vs_base = 1.0
                row.speedup_total_vs_base = 1.0
                if row.tiempo_determinista:
                    row.speedup_det_vs_base = 1.0
                row.gap_delta_vs_base = 0.0
                row.obj_post_delta_vs_base = 0.0
                row.overhead_preprocesamiento_vs_base = 0.0
                row.ratio_preproc_solver = 0.0
                if row.tiempo_preprocesamiento_s is None:
                    row.tiempo_preprocesamiento_s = 0.0
                row.tiempo_total_s = row.tiempo_solver_s
                continue
            if base.tiempo_solver_s and row.tiempo_solver_s and row.tiempo_solver_s > 0:
                row.speedup_vs_base = base.tiempo_solver_s / row.tiempo_solver_s
            row.speedup_solver_vs_base = row.speedup_vs_base

            # Timing compuesto
            base_preproc = base.tiempo_preprocesamiento_s if base.tiempo_preprocesamiento_s is not None else 0.0
            row_preproc = row.tiempo_preprocesamiento_s if row.tiempo_preprocesamiento_s is not None else 0.0
            base_solver = base.tiempo_solver_s or 0.0
            row_solver = row.tiempo_solver_s or 0.0
            base_total = base_solver + base_preproc
            row_total = row_solver + row_preproc
            row.tiempo_total_s = row_total if (row_solver > 0 or row_preproc > 0) else None
            if base_total > 0 and row_total > 0:
                row.speedup_total_vs_base = base_total / row_total
            row.overhead_preprocesamiento_vs_base = row_preproc - base_preproc
            if row_solver > 0:
                row.ratio_preproc_solver = row_preproc / row_solver

            if base.gap_pct is not None and row.gap_pct is not None:
                row.gap_delta_vs_base = base.gap_pct - row.gap_pct
            if base.objetivo_solver is not None and row.objetivo_solver is not None:
                row.obj_solver_delta_vs_base = row.objetivo_solver - base.objetivo_solver
                if abs(base.objetivo_solver) > 0:
                    row.obj_solver_rel_delta_vs_base = row.obj_solver_delta_vs_base / abs(base.objetivo_solver)
            if base.objetivo_post is not None and row.objetivo_post is not None:
                row.obj_post_delta_vs_base = row.objetivo_post - base.objetivo_post
                if abs(base.objetivo_post) > 0:
                    row.obj_post_rel_delta_vs_base = row.obj_post_delta_vs_base / abs(base.objetivo_post)
            if (base.matrix_min and base.matrix_max and row.matrix_min and row.matrix_max and
                    base.matrix_min > 0 and row.matrix_min > 0):
                base_kappa = base.matrix_max / base.matrix_min
                row_kappa = row.matrix_max / row.matrix_min
                if base_kappa > 0:
                    row.matrix_kappa_ratio_vs_base = row_kappa / base_kappa
            if row.kappa_antes and row.kappa_despues and row.kappa_antes > 0:
                row.kappa_proxy_ratio = row.kappa_despues / row.kappa_antes
            # ρ_κ con el número de condición REAL de la base (solver), análogo a
            # matrix_kappa_ratio_vs_base pero sobre κ medido, no sobre el rango de coeficientes.
            if (base.kappa_solver and row.kappa_solver and
                    base.kappa_solver > 0 and row.kappa_solver > 0):
                row.kappa_solver_ratio_vs_base = row.kappa_solver / base.kappa_solver
            # speedup determinista (work units en Gurobi, ticks en CPLEX): reproducible.
            if (base.tiempo_determinista and row.tiempo_determinista and
                    row.tiempo_determinista > 0):
                row.speedup_det_vs_base = base.tiempo_determinista / row.tiempo_determinista
            # razón variante/base del κ máximo de árbol (CPLEX KappaStats).
            if (base.kappa_arbol_max and row.kappa_arbol_max and
                    base.kappa_arbol_max > 0 and row.kappa_arbol_max > 0):
                row.kappa_arbol_max_ratio_vs_base = row.kappa_arbol_max / base.kappa_arbol_max

            # --- Razones variante/base de los 4 rangos de coeficientes ---
            def _rango_ratio(bmin, bmax, rmin, rmax):
                if (bmin and bmax and rmin and rmax and bmin > 0 and rmin > 0):
                    b = bmax / bmin
                    return (rmax / rmin) / b if b > 0 else None
                return None
            row.matrix_range_ratio_vs_base = _rango_ratio(
                base.matrix_min, base.matrix_max, row.matrix_min, row.matrix_max)
            row.objective_range_ratio_vs_base = _rango_ratio(
                base.objective_min, base.objective_max, row.objective_min, row.objective_max)
            row.rhs_range_ratio_vs_base = _rango_ratio(
                base.rhs_min, base.rhs_max, row.rhs_min, row.rhs_max)
            row.bounds_range_ratio_vs_base = _rango_ratio(
                base.bounds_min, base.bounds_max, row.bounds_min, row.bounds_max)

            # --- Calidad de solución vs base en ESCALA ORIGINAL recomputada ---
            # obj_base: la base no se escala, su incumbent ya está en escala original.
            obj_base = base.objetivo_solver
            obj_var = (row.obj_original_variante if row.obj_original_variante is not None
                       else row.objetivo_solver)
            if obj_base is not None and obj_var is not None:
                row.abs_obj_diff_vs_base = obj_var - obj_base
                row.rel_obj_diff_vs_base = abs(obj_var - obj_base) / max(1.0, abs(obj_base))
                # Minimización: menor objetivo = mejor.
                tol_sentido = 1e-6 * max(1.0, abs(obj_base))
                if obj_var < obj_base - tol_sentido:
                    row.sentido_obj_vs_base = "mejora"
                elif obj_var > obj_base + tol_sentido:
                    row.sentido_obj_vs_base = "empeora"
                else:
                    row.sentido_obj_vs_base = "igual"
            if base.best_bound is not None and row.best_bound is not None:
                row.best_bound_delta_vs_base = row.best_bound - base.best_bound


def write_summary_csv(rows: list[RunSummary], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    add_relative_metrics(rows)
    fields = list(asdict(rows[0]).keys()) if rows else list(RunSummary("", "", "", 0).__dict__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def fmt(value: object, digits: int = 3) -> str:
    if value is None or value == "":
        return '<span class="nd">N/D</span>'
    if isinstance(value, float):
        if math.isnan(value):
            return '<span class="nd">N/D</span>'
        if abs(value) >= 1000 or (0 < abs(value) < 0.001):
            return f"{value:.{digits}e}"
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def numeric(values: list[float | None]) -> list[float]:
    return [v for v in values if v is not None and not math.isnan(v)]


def mean(values: list[float | None]) -> float | None:
    xs = numeric(values)
    if not xs:
        return None
    return sum(xs) / len(xs)


def median(values: list[float | None]) -> float | None:
    xs = sorted(numeric(values))
    if not xs:
        return None
    mid = len(xs) // 2
    if len(xs) % 2:
        return xs[mid]
    return 0.5 * (xs[mid - 1] + xs[mid])


def build_stats(rows: list[RunSummary]) -> list[dict[str, object]]:
    variants = sorted({r.variante for r in rows if r.variante != "base"})
    stats: list[dict[str, object]] = []
    for variant in variants:
        items = [r for r in rows if r.variante == variant and r.status == "OK"]
        if not items:
            continue
        stats.append({
            "variante": variant,
            "n": len(items),
            "mip_ok": sum(1 for r in items if r.mip_equivalente in ("OK", "BASE")),
            "csv_ok": sum(1 for r in items if r.equivalente_vs_base == "OK"),
            "preproc_med": median([r.tiempo_preprocesamiento_s for r in items]),
            "preproc_mean": mean([r.tiempo_preprocesamiento_s for r in items]),
            "total_med": median([r.tiempo_total_s for r in items]),
            "total_mean": mean([r.tiempo_total_s for r in items]),
            "speedup_solver_med": median([r.speedup_solver_vs_base for r in items]),
            "speedup_solver_mean": mean([r.speedup_solver_vs_base for r in items]),
            "speedup_total_med": median([r.speedup_total_vs_base for r in items]),
            "speedup_total_mean": mean([r.speedup_total_vs_base for r in items]),
            "ratio_preproc_solver_med": median([r.ratio_preproc_solver for r in items]),
            "speedup_med": median([r.speedup_vs_base for r in items]),
            "speedup_mean": mean([r.speedup_vs_base for r in items]),
            "gap_delta_med": median([r.gap_delta_vs_base for r in items]),
            "solver_delta_med": median([r.obj_solver_delta_vs_base for r in items]),
            "solver_rel_delta_med": median([r.obj_solver_rel_delta_vs_base for r in items]),
            "post_delta_med": median([r.obj_post_delta_vs_base for r in items]),
            "post_rel_delta_med": median([r.obj_post_rel_delta_vs_base for r in items]),
            "max_diff_med": median([r.max_diff_post_csv for r in items]),
            "max_diff_max": max(numeric([r.max_diff_post_csv for r in items]), default=None),
            "matrix_ratio_med": median([r.matrix_kappa_ratio_vs_base for r in items]),
            "kappa_proxy_ratio_med": median([r.kappa_proxy_ratio for r in items]),
        })
    return stats


def render_stats(rows: list[RunSummary]) -> str:
    stats = build_stats(rows)
    if not stats:
        return ""

    trs = []
    for s in stats:
        trs.append(f"""
        <tr>
          <td>{html.escape(str(s["variante"]))}</td>
          <td>{fmt(s["n"], 0)}</td>
          <td>{fmt(s["mip_ok"], 0)}</td>
          <td>{fmt(s["csv_ok"], 0)}</td>
          <td>{fmt(s["preproc_med"])}</td>
          <td>{fmt(s["preproc_mean"])}</td>
          <td>{fmt(s["total_med"])}</td>
          <td>{fmt(s["total_mean"])}</td>
          <td>{fmt(s["speedup_solver_med"])}</td>
          <td>{fmt(s["speedup_solver_mean"])}</td>
          <td>{fmt(s["speedup_total_med"])}</td>
          <td>{fmt(s["speedup_total_mean"])}</td>
          <td>{fmt(s["ratio_preproc_solver_med"])}</td>
          <td>{fmt(s["speedup_med"])}</td>
          <td>{fmt(s["speedup_mean"])}</td>
          <td>{fmt(s["gap_delta_med"])}</td>
          <td>{fmt(s["solver_delta_med"])}</td>
          <td>{fmt(s["solver_rel_delta_med"])}</td>
          <td>{fmt(s["post_delta_med"])}</td>
          <td>{fmt(s["post_rel_delta_med"])}</td>
          <td>{fmt(s["max_diff_med"])}</td>
          <td>{fmt(s["max_diff_max"])}</td>
          <td>{fmt(s["matrix_ratio_med"])}</td>
          <td>{fmt(s["kappa_proxy_ratio_med"])}</td>
        </tr>
        """)

    return f"""
    <section class="card summary">
      <h2>Análisis estadístico contra base</h2>
      <p>
        <b>MIP OK</b> evalúa factibilidad y objetivo en unidades originales antes del postprocesamiento.
        <b>CSV post iguales</b> mide estabilidad del postprocesamiento respecto a base.
        <b>Speedup solver</b> mide solo tiempo del solver; <b>Speedup total</b> incluye el costo de preprocesamiento.
        En razones de matriz/κ, valores menores que 1 indican mejora de escala.
      </p>
      <div class="table-wrap"><table>
        <thead>
          <tr>
            <th>Variante</th><th>n</th><th>MIP OK</th><th>CSV post iguales</th>
            <th>Preproc. med. (s)</th><th>Preproc. prom. (s)</th>
            <th>Total med. (s)</th><th>Total prom. (s)</th>
            <th>Speedup solver med.</th><th>Speedup solver prom.</th>
            <th>Speedup total med.</th><th>Speedup total prom.</th>
            <th>Ratio preproc/solver med.</th>
            <th>Speedup (legacy) med.</th><th>Speedup (legacy) prom.</th>
            <th>Δ gap med.</th><th>Δ obj solver med.</th><th>Δ rel. solver med.</th>
            <th>Δ obj post med.</th><th>Δ rel. post med.</th>
            <th>Max diff med.</th><th>Max diff máx.</th><th>Ratio matriz med.</th><th>Ratio κ proxy med.</th>
          </tr>
        </thead>
        <tbody>{''.join(trs)}</tbody>
      </table></div>
    </section>
    """


def write_html(rows: list[RunSummary], path: Path) -> None:
    add_relative_metrics(rows)
    grouped: dict[str, list[RunSummary]] = {}
    for row in rows:
        grouped.setdefault(row.instancia, []).append(row)

    cards = []
    for instance, items in grouped.items():
        trs = []
        for r in items:
            cls = "ok" if r.mip_equivalente in ("OK", "BASE") and r.status == "OK" else "bad"
            _viol_solver = numeric([r.verif_solver_max_le, r.verif_solver_max_ge, r.verif_solver_max_eq,
                                    r.verif_solver_max_lb, r.verif_solver_max_ub, r.verif_solver_max_int])
            _viol_post = numeric([r.verif_post_max_le, r.verif_post_max_ge, r.verif_post_max_eq,
                                  r.verif_post_max_lb, r.verif_post_max_ub, r.verif_post_max_int])
            status_badge = "badge-ok" if r.status == "OK" else "badge-bad"
            mip_badge = "badge-ok" if r.mip_equivalente in ("OK", "BASE") else ("badge-warn" if r.mip_equivalente == "REVISAR" else "badge-bad")
            csv_badge = "badge-ok" if r.equivalente_vs_base == "OK" else "badge-warn"
            trs.append(f"""
            <tr class="{cls}">
              <td>{html.escape(r.variante)}</td>
              <td><span class="badge {status_badge}">{html.escape(r.status)}</span></td>
              <td><span class="badge {mip_badge}">{html.escape(r.mip_equivalente)}</span></td>
              <td><span class="badge {csv_badge}">{html.escape(r.equivalente_vs_base)}</span></td>
              <td>{fmt(r.tiempo_solver_s)}</td>
              <td>{fmt(r.tiempo_preprocesamiento_s)}</td>
              <td>{fmt(r.tiempo_total_s)}</td>
              <td>{fmt(r.gap_pct)}</td>
              <td>{fmt(r.objetivo_solver)}</td>
              <td>{fmt(r.verif_solver_obj_original)}</td>
              <td>{fmt(r.objetivo_post)}</td>
              <td>{fmt(r.speedup_solver_vs_base)}</td>
              <td>{fmt(r.speedup_total_vs_base)}</td>
              <td>{fmt(r.overhead_preprocesamiento_vs_base)}</td>
              <td>{fmt(r.ratio_preproc_solver)}</td>
              <td>{fmt(r.speedup_vs_base)}</td>
              <td>{fmt(r.gap_delta_vs_base)}</td>
              <td>{fmt(r.obj_solver_delta_vs_base)}</td>
              <td>{fmt(r.obj_solver_rel_delta_vs_base)}</td>
              <td>{fmt(r.obj_post_delta_vs_base)}</td>
              <td>{fmt(r.obj_post_rel_delta_vs_base)}</td>
              <td>{fmt(max(_viol_solver), 3) if _viol_solver else '<span class="nd">N/D</span>'}</td>
              <td>{fmt(max(_viol_post), 3) if _viol_post else '<span class="nd">N/D</span>'}</td>
              <td>{fmt(r.matrix_min)} .. {fmt(r.matrix_max)}</td>
              <td>{fmt(r.matrix_kappa_ratio_vs_base)}</td>
              <td>{fmt(r.kappa_antes)} -> {fmt(r.kappa_despues)}</td>
              <td>{fmt(r.kappa_proxy_ratio)}</td>
              <td>{fmt(r.max_diff_post_csv)}</td>
            </tr>
            """)
        cards.append(f"""
        <section class="card">
          <h2>{html.escape(instance)}</h2>
          <div class="table-wrap"><table>
            <thead>
              <tr>
                <th>Variante</th><th>Estado</th><th>MIP equiv.</th><th>CSV post</th>
                <th>T. solver (s)</th><th>T. preproc. (s)</th><th>T. total (s)</th>
                <th>Gap %</th><th>Obj solver</th><th>Obj orig. recalc.</th><th>Obj post</th>
                <th>Speedup solver</th><th>Speedup total</th>
                <th>Overhead preproc. (s)</th><th>Ratio preproc/solver</th>
                <th>Speedup (legacy)</th>
                <th>Δ gap</th><th>Δ obj solver</th><th>Δ rel. solver</th>
                <th>Δ obj post</th><th>Δ rel. post</th>
                <th>Max viol. solver</th><th>Max viol. post</th>
                <th>Matrix range</th><th>Ratio matriz</th><th>κ global</th><th>Ratio κ</th><th>Max diff CSV</th>
              </tr>
            </thead>
            <tbody>{''.join(trs)}</tbody>
          </table></div>
        </section>
        """)

    body = f"""
    <section class="info-note">
      Este reporte compara transformaciones de preprocesamiento contra la variante base.
      <code>MIP equiv. OK</code> usa la solución del solver desescalada sobre el modelo original;
      <code>CSV post OK</code> compara la salida postprocesada.
    </section>
    {render_stats(rows)}
    {''.join(cards)}
    """
    doc = report_document(
        "Validación experimental de preprocesamiento",
        "Comparación estadística de variantes numéricas sobre instancias del sistema eléctrico.",
        body,
        meta=[
            ("Instancias", len({r.instancia for r in rows})),
            ("Corridas", len(rows)),
            ("Variantes", ", ".join(sorted({r.variante for r in rows}))),
            ("Tolerancia factibilidad", "ver CSV"),
        ],
        eyebrow="Reporte técnico de optimización",
    )
    path.write_text(doc, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida preprocesamiento con corridas reales del solver.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Instancias .txt o carpetas.")
    parser.add_argument("--exe", type=Path, default=Path("build/SistemaElectrico"))
    parser.add_argument("--solver", default="Gurobi")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--mipgap", type=float, default=0.1)
    parser.add_argument("--max-instancias", type=int, default=None)
    parser.add_argument("--variantes", default="base,estructurado,ruiz_columnas")
    parser.add_argument("--output", type=Path, default=Path("ejecuciones/validacion_preprocesamiento"))
    parser.add_argument("--tol", type=float, default=1e-7)
    parser.add_argument("--verificar-original", action="store_true",
                        help="Activa snapshot y verificación de factibilidad en unidades originales.")
    parser.add_argument("--tol-factibilidad", type=float, default=1e-4)
    parser.add_argument("--tol-objetivo", type=float, default=1e-3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--sin-base", action="store_true",
                        help="No anteponer 'base' automáticamente: corre EXACTAMENTE las variantes "
                             "pedidas. Útil para re-correr solo una variante (p.ej. estructurado_matricial) "
                             "cuando el 'base' de referencia ya se calculó aparte y se compara al combinar.")
    args = parser.parse_args()

    exe = args.exe.resolve()
    if not exe.is_file():
        raise SystemExit(f"No existe el ejecutable: {exe}")

    instances = discover_instances(args.inputs, args.max_instancias)
    if not instances:
        raise SystemExit("No se encontraron instancias.")

    variants = [v.strip() for v in args.variantes.split(",") if v.strip()]
    unknown = [v for v in variants if v not in VARIANT_FLAGS]
    if unknown:
        raise SystemExit(f"Variantes desconocidas: {', '.join(unknown)}")
    if "base" not in variants and not args.sin_base:
        variants.insert(0, "base")

    out = args.output
    result_dir = out / "resultados"
    log_dir = out / "logs"
    rows: list[RunSummary] = []

    for instance in instances:
        base_post: Path | None = None
        for variant in variants:
            stem = f"{instance.stem}_{variant_slug(variant)}"
            csv_path = result_dir / f"{stem}.csv"
            log_path = log_dir / f"{stem}.log"
            print(f"[run] {instance.name} / {variant}")
            rc = run_case(exe, instance, args.solver, args.timeout, args.mipgap,
                          variant, csv_path, log_path, args.force, args.verificar_original)
            summary = summarize(
                instance,
                variant,
                rc,
                csv_path,
                log_path,
                base_post,
                args.tol,
                args.tol_factibilidad,
                args.tol_objetivo,
            )
            rows.append(summary)
            if variant == "base":
                base_post = Path(summary.csv_post)
            write_summary_csv(rows, out / "resumen.csv")
            write_html(rows, out / "reporte.html")

    print(f"Resumen: {out / 'resumen.csv'}")
    print(f"Reporte: {out / 'reporte.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
