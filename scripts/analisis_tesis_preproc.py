#!/usr/bin/env python3
"""Análisis estadístico del preprocesamiento MIP para la sección de experimentación.

Toma los `resumen.csv` ya generados por `validar_preprocesamiento.py` (NO los modifica
ni los fusiona en disco), los agrupa por grupo de instancias y produce:

  * tabla LaTeX `tab:resumen-preproc`  (n, MIP OK, CSV OK, T_total med(IQR),
    speedup_total med(IQR), speedup_solver med(IQR), overhead med);
  * tabla LaTeX `tab:wilcoxon-preproc` (Wilcoxon pareado W, p-valor y δ de Cliff
    sobre T_solver y T_total, variante vs base);
  * reporte de censura (resueltas / timeouts) por (grupo, variante);
  * correlación de Spearman entre ρ_κ y speedup_solver;
  * figuras `boxplot_speedup_total.pdf` y `scatter_kappa_speedup.pdf`.

Todo se calcula a partir de columnas que YA existen en el resumen.csv; no requiere
re-correr el solver ni datos nuevos del backend.

--------------------------------------------------------------------------------
CÓMO APUNTARLO A LA ESTRUCTURA FINAL
--------------------------------------------------------------------------------
Cuando tengas una carpeta por modelo con todas las variantes, editá el dict GRUPOS
de abajo (o pasá --config grupos.json) con la forma:

    {
      "Modelo simple":   ["ruta/a/validacion-simple"],
      "Modelo completo": ["ruta/a/validacion-completo"],
      "SG-Ter-Mer":      ["ruta/a/validacion-sg"]
    }

Cada valor es una LISTA de carpetas (admite varios batches b1..bN del mismo grupo);
cada carpeta debe contener un `resumen.csv`. El script concatena los batches, agrega
la columna `grupo`, y deduplica por (grupo, instancia, variante).

Uso:
    python3 scripts/analisis_tesis_preproc.py --output ejecuciones/analisis_tesis
    python3 scripts/analisis_tesis_preproc.py --config grupos.json --timeout 3600
    # dry-run sobre una sola carpeta, sin fusionar nada:
    python3 scripts/analisis_tesis_preproc.py \
        --grupo "SG-Ter-Mer=resultados/resultados-cluster/validacion-preproc-sg-b1" \
        --output /tmp/analisis_sg
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

try:
    from scipy import stats as _scipy_stats
except ImportError:  # pragma: no cover
    _scipy_stats = None


# --------------------------------------------------------------------------- #
# Configuración por defecto (editar o sobreescribir con --config / --grupo)
# --------------------------------------------------------------------------- #
# OJO: por defecto NO se fusiona la estructura final (que todavía no existe).
# Estas rutas son un placeholder de ejemplo; reemplazalas por tu estructura
# definitiva (una carpeta por modelo) cuando la tengas.
GRUPOS: dict[str, list[str]] = {
    "Modelo simple": [
        "resultados/resultados-cluster/validacion-preproc-simple-b1",
        "resultados/resultados-cluster/validacion-preproc-simple-b2",
        "resultados/resultados-cluster/validacion-preproc-simple-b3",
        "resultados/resultados-cluster/validacion-preproc-simple-b4",
    ],
    "Modelo completo": [
        "resultados/resultados-cluster/validacion-preproc-completo-b1",
        "resultados/resultados-cluster/validacion-preproc-completo-b2",
    ],
    "SG-Ter-Mer": [
        "resultados/resultados-cluster/validacion-preproc-sg-b1",
        "resultados/resultados-cluster/validacion-preproc-sg-b2",
    ],
}

# Orden y etiqueta de presentación de las variantes (base se usa solo como referencia).
VARIANTES_ORDEN = ["estructurado", "estructurado_matricial", "ruiz", "ruiz_columnas"]
VARIANTE_LABEL = {
    "estructurado": "Estructurado",
    "estructurado_matricial": "Estruct. matricial",
    "ruiz": "Ruiz",
    "ruiz_columnas": "Ruiz+col.",
    "filas": "Filas",
    "bloque": "Bloque",
}
GRUPO_ORDEN = ["Modelo simple", "Modelo completo", "SG-Ter-Mer"]


# --------------------------------------------------------------------------- #
# Utilidades numéricas
# --------------------------------------------------------------------------- #
def _to_float(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "N/D", "None", "nan"):
        return None
    try:
        f = float(s)
        return None if math.isnan(f) else f
    except ValueError:
        return None


def _clean(values) -> list[float]:
    out = []
    for v in values:
        f = v if isinstance(v, float) else _to_float(v)
        if f is not None and not math.isnan(f):
            out.append(f)
    return out


def _median(values) -> float | None:
    xs = sorted(_clean(values))
    n = len(xs)
    if not n:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else 0.5 * (xs[mid - 1] + xs[mid])


def _percentile(values, p: float) -> float | None:
    xs = sorted(_clean(values))
    n = len(xs)
    if not n:
        return None
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def _iqr(values) -> float | None:
    q1, q3 = _percentile(values, 25), _percentile(values, 75)
    if q1 is None or q3 is None:
        return None
    return q3 - q1


def cliffs_delta(a: list[float], b: list[float]) -> tuple[float | None, str]:
    """δ de Cliff entre dos muestras (a = variante, b = base).

    δ = [#(a>b) - #(a<b)] / (|a|·|b|).  Negativo ⇒ a tiende a ser menor que b
    (deseable para tiempos).  Devuelve (delta, magnitud cualitativa)."""
    a, b = _clean(a), _clean(b)
    if not a or not b:
        return None, "N/D"
    gt = lt = 0
    for x in a:
        for y in b:
            if x > y:
                gt += 1
            elif x < y:
                lt += 1
    delta = (gt - lt) / (len(a) * len(b))
    mag = abs(delta)
    if mag < 0.147:
        etiqueta = "despreciable"
    elif mag < 0.330:
        etiqueta = "pequeño"
    elif mag < 0.474:
        etiqueta = "mediano"
    else:
        etiqueta = "grande"
    return delta, etiqueta


def wilcoxon_pareado(x: list[float], y: list[float]) -> tuple[float | None, float | None]:
    """Wilcoxon bilateral reproducible (x-y), sin corrección de continuidad."""
    if _scipy_stats is None:
        return None, None
    pares = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None]
    if len(pares) < 1:
        return None, None
    xs = [p[0] for p in pares]
    ys = [p[1] for p in pares]
    diferencias = [a - b for a, b in pares]
    if all(d == 0.0 for d in diferencias):
        return None, None
    no_cero = [d for d in diferencias if d != 0.0]
    absolutos = [abs(d) for d in no_cero]
    tiene_ceros = len(no_cero) != len(diferencias)
    tiene_empates = len(set(absolutos)) != len(absolutos)
    metodo = ('exact' if len(no_cero) <= 50 and not tiene_ceros
              and not tiene_empates else 'asymptotic')
    try:
        res = _scipy_stats.wilcoxon(
            diferencias, zero_method="wilcox", alternative="two-sided",
            correction=False, method=metodo)
        return float(res.statistic), float(res.pvalue)
    except ValueError:
        return None, None


def spearman(x: list[float], y: list[float]) -> tuple[float | None, float | None]:
    if _scipy_stats is None:
        return None, None
    pares = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None
             and not math.isnan(xi) and not math.isnan(yi)]
    if len(pares) < 3:
        return None, None
    xs = [p[0] for p in pares]
    ys = [p[1] for p in pares]
    try:
        res = _scipy_stats.spearmanr(xs, ys)
        rho, p = float(res.correlation), float(res.pvalue)
        if math.isnan(rho):       # entrada constante → correlación indefinida
            return None, None
        return rho, (None if math.isnan(p) else p)
    except (ValueError, TypeError):
        return None, None


def benjamini_hochberg(pvals: list[float | None]) -> list[float | None]:
    """p-valores ajustados por Benjamini-Hochberg (control de FDR) sobre la familia de
    tests. Conserva los None en su lugar; los ajustados son monótonos y acotados en [0,1]."""
    indexados = [(i, p) for i, p in enumerate(pvals) if p is not None]
    ajustados: list[float | None] = [None] * len(pvals)
    m = len(indexados)
    if m == 0:
        return ajustados
    indexados.sort(key=lambda t: t[1])
    min_acum = 1.0
    for rank in range(m, 0, -1):           # de mayor a menor p, imponiendo monotonía
        i, p = indexados[rank - 1]
        q = min(1.0, p * m / rank)
        min_acum = min(min_acum, q)
        ajustados[i] = min_acum
    return ajustados


def _sgm(values, shift: float = 1.0) -> float | None:
    """Media geométrica desplazada: exp(mean(ln(x_i + s))) - s. Robusta a valores chicos y
    a ceros (estándar para agregar tiempos de solver, p.ej. MIPLIB). shift en las mismas
    unidades de la serie (1 s para tiempos, 10 para nodos)."""
    xs = [x for x in _clean(values) if x + shift > 0]
    if not xs:
        return None
    s = sum(math.log(x + shift) for x in xs) / len(xs)
    return math.exp(s) - shift


def _par10(values, limite: float, factor: float = 10.0) -> float | None:
    """Tiempo penalizado: los timeouts (t >= 0.99·límite) cuentan como factor·límite.
    Resume en un único número la robustez ante el límite de tiempo (estándar en SAT/ML)."""
    xs = _clean(values)
    if not xs:
        return None
    pen = [factor * limite if x >= 0.99 * limite else x for x in xs]
    return sum(pen) / len(pen)


def _bootstrap_ci(values, stat_fn, n_boot: int = 2000, alpha: float = 0.05,
                  seed: int = 12345) -> tuple[float | None, float | None]:
    """IC percentil (1-alpha) por bootstrap para un estadístico (mediana, sgm, ...)."""
    xs = _clean(values)
    if len(xs) < 3:
        return None, None
    rng = random.Random(seed)
    estad = []
    n = len(xs)
    for _ in range(n_boot):
        muestra = [xs[rng.randrange(n)] for _ in range(n)]
        s = stat_fn(muestra)
        if s is not None and not math.isnan(s):
            estad.append(s)
    if not estad:
        return None, None
    estad.sort()
    lo = estad[int((alpha / 2) * len(estad))]
    hi = estad[min(len(estad) - 1, int((1 - alpha / 2) * len(estad)))]
    return lo, hi


def steiger_williams(r_jh: float, r_kh: float, r_jk: float,
                     n: int) -> tuple[float | None, float | None]:
    """Test de Williams (1959) / Hotelling–Williams para dos correlaciones DEPENDIENTES
    solapadas que comparten una variable: r_jh = corr(predictor1, salida),
    r_kh = corr(predictor2, salida), r_jk = corr(predictor1, predictor2).
    Contrasta H0: rho_jh = rho_kh. Devuelve (t, p two-sided), t con n-3 g.l.
    Nota: aplicado a correlaciones de rango (Spearman) es una aproximación estándar."""
    if n is None or n <= 3:
        return None, None
    try:
        det = (1 - r_jh**2 - r_kh**2 - r_jk**2 + 2 * r_jh * r_kh * r_jk)
        if det <= 0:
            return None, None
        prom = (r_jh + r_kh) / 2.0
        num = (r_jh - r_kh) * math.sqrt((n - 1) * (1 + r_jk))
        den = math.sqrt(2 * ((n - 1) / (n - 3)) * det + (prom**2) * (1 - r_jk)**3)
        if den == 0:
            return None, None
        t = num / den
    except (ValueError, ZeroDivisionError):
        return None, None
    if _scipy_stats is not None:
        p = 2.0 * _scipy_stats.t.sf(abs(t), df=n - 3)
    else:                                   # aprox. normal si no hay scipy
        p = math.erfc(abs(t) / math.sqrt(2.0))
    return t, p


def spearman_parcial(x, y, z) -> tuple[float | None, float | None, int]:
    """Spearman parcial entre x e y controlando por z (correlación de rango parcial de
    primer orden). Devuelve (rho_parcial, p, n). p por t con n-3 g.l."""
    trios = [(xi, yi, zi) for xi, yi, zi in zip(x, y, z)
             if xi is not None and yi is not None and zi is not None]
    if len(trios) < 4:
        return None, None, len(trios)
    xs = [t[0] for t in trios]; ys = [t[1] for t in trios]; zs = [t[2] for t in trios]
    r_xy, _ = spearman(xs, ys)
    r_xz, _ = spearman(xs, zs)
    r_yz, _ = spearman(ys, zs)
    # Si el control (z, tamaño) es constante dentro del subconjunto, r_xz/r_yz son indefinidas
    # (None) → la parcial no está definida; típico al pedirla por familia (mismo modelo).
    if any(v is None or (isinstance(v, float) and math.isnan(v))
           for v in (r_xy, r_xz, r_yz)):
        return None, None, len(trios)
    den = math.sqrt((1 - r_xz**2) * (1 - r_yz**2))
    if den == 0:
        return None, None, len(trios)
    rp = (r_xy - r_xz * r_yz) / den
    rp = max(-1.0, min(1.0, rp))
    n = len(trios)
    if abs(rp) >= 1.0 or n <= 3:
        return rp, None, n
    t = rp * math.sqrt((n - 3) / (1 - rp**2))
    if _scipy_stats is not None:
        p = 2.0 * _scipy_stats.t.sf(abs(t), df=n - 3)
    else:
        p = math.erfc(abs(t) / math.sqrt(2.0))
    return rp, p, n


# --------------------------------------------------------------------------- #
# Carga y agrupación (sin tocar las carpetas de origen)
# --------------------------------------------------------------------------- #
def cargar_grupo(nombre: str, carpetas: list[str], base_dir: Path,
                 incluir_errores: bool = False) -> list[dict]:
    """Lee y concatena los CSV; opcionalmente conserva filas no completadas.

    La carga descriptiva histórica mantiene solo ``status=OK``.  La carga cruda
    se usa exclusivamente para construir pares censurados sin premiar abortos
    unilaterales.
    """
    vistos: dict[tuple[str, str], dict] = {}
    for carpeta in carpetas:
        p = Path(carpeta)
        if not p.is_absolute():
            p = base_dir / p
        rs = p / "resumen.csv"
        if not rs.exists():
            print(f"[aviso] sin resumen.csv: {rs}")
            continue
        with rs.open(encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                inst = (row.get("instancia") or "").strip()
                var = (row.get("variante") or "").strip()
                if not inst or not var:
                    continue
                if (not incluir_errores
                        and (row.get("status") or "").strip() != "OK"):
                    continue
                row["grupo"] = nombre
                # Si una instancia/variante aparece en dos batches, gana la última leída.
                vistos[(inst, var)] = row
    return list(vistos.values())


def cargar_todo(grupos: dict[str, list[str]], base_dir: Path,
                incluir_errores: bool = False, anunciar: bool = True) -> list[dict]:
    rows: list[dict] = []
    for nombre, carpetas in grupos.items():
        g = cargar_grupo(nombre, carpetas, base_dir, incluir_errores)
        if anunciar:
            tipo = "filas crudas" if incluir_errores else "filas OK"
            print(f"[grupo] {nombre}: {len(g)} {tipo} "
                  f"({len(set((r['instancia'] for r in g)))} instancias)")
        rows.extend(g)
    return rows


def es_timeout(row: dict, timeout: float) -> bool:
    t = _to_float(row.get("tiempo_solver_s"))
    return t is not None and t >= 0.99 * timeout


def emparejar(rows: list[dict], grupo: str, variante: str):
    """Devuelve (variante_rows, base_rows) alineados por instancia."""
    by_inst: dict[str, dict[str, dict]] = {}
    for r in rows:
        if r.get("grupo") != grupo:
            continue
        by_inst.setdefault((r.get("instancia") or ""), {})[r.get("variante")] = r
    var_rows, base_rows = [], []
    for inst_d in by_inst.values():
        if variante in inst_d and "base" in inst_d:
            var_rows.append(inst_d[variante])
            base_rows.append(inst_d["base"])
    return var_rows, base_rows


# --------------------------------------------------------------------------- #
# Construcción de estadísticas
# --------------------------------------------------------------------------- #
def stats_resumen(rows: list[dict]) -> list[dict]:
    """Una fila por (grupo, variante) con los agregados de la tabla resumen."""
    out = []
    grupos_presentes = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    grupos_presentes += [g for g in {r.get("grupo") for r in rows}
                         if g and g not in grupos_presentes]
    for grupo in grupos_presentes:
        for variante in VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            st = {
                "grupo": grupo,
                "variante": variante,
                "n": len(items),
                "mip_ok": sum(1 for r in items
                              if (r.get("mip_equivalente") or "") in ("OK", "BASE")),
                "csv_ok": sum(1 for r in items
                              if (r.get("equivalente_vs_base") or "") in ("OK", "BASE")),
            }
            for col, key in (("tiempo_total_s", "total"),
                             ("speedup_total_vs_base", "sp_total"),
                             ("speedup_solver_vs_base", "sp_solver"),
                             ("ratio_preproc_solver", "overhead")):
                vals = [_to_float(r.get(col)) for r in items]
                st[f"{key}_med"] = _median(vals)
                st[f"{key}_iqr"] = _iqr(vals)
            out.append(st)
    return out


def _estado_pareado(row: dict | None) -> str:
    """Clasifica una celda cruda como ok, timeout o abort."""
    if not row:
        return "abort"
    if (row.get("status_solver") or "").strip() == "TIME_LIMIT":
        return "timeout"
    if ((row.get("rc") or "").strip() == "0"
            and (row.get("status") or "").strip() != "ERROR"
            and (row.get("status_solver") or "").strip() == "OPTIMAL"):
        return "ok"
    return "abort"


def _valor_pareado(row: dict | None, estado: str, columna: str,
                   timeout: float) -> float | None:
    """Tiempo observado si completa; cap exacto si no completa."""
    if estado != "ok":
        return timeout
    valor = _to_float(row.get(columna) if row else None)
    if valor is None or not math.isfinite(valor) or valor < 0.0:
        return None
    return valor


def stats_wilcoxon(rows: list[dict], timeout: float) -> list[dict]:
    """Wilcoxon pareado con no-finalizaciones unilaterales al cap.

    Usa las filas crudas: excluye instancias uniformemente no disponibles y
    pares donde ambos lados no completan; si solo un lado no completa, lo
    conserva a ``timeout``. Esta es la misma construcción de
    ``scripts/paired_tests.py``.
    """
    out = []
    grupos_presentes = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    grupos_presentes += sorted(g for g in {r.get("grupo") for r in rows}
                               if g and g not in grupos_presentes)
    for grupo in grupos_presentes:
        by_inst: dict[str, dict[str, dict]] = {}
        for row in rows:
            if row.get("grupo") == grupo:
                by_inst.setdefault(row.get("instancia") or "", {})[
                    row.get("variante") or ""] = row
        variantes_campania = ["base"] + VARIANTES_ORDEN
        uniformes = {
            inst for inst, cells in by_inst.items()
            if all(cells.get(v, {}).get("rc") not in (None, "0")
                   for v in variantes_campania)
        }
        for variante in VARIANTES_ORDEN:
            candidatos = []
            doble_timeout = doble_abort = doble_otro = unilaterales = 0
            for inst, cells in by_inst.items():
                if inst in uniformes:
                    continue
                vr, br = cells.get(variante), cells.get("base")
                ve, be = _estado_pareado(vr), _estado_pareado(br)
                if ve != "ok" and be != "ok":
                    if ve == be == "timeout":
                        doble_timeout += 1
                    elif ve == be == "abort":
                        doble_abort += 1
                    else:
                        doble_otro += 1
                    continue
                if ve != "ok" or be != "ok":
                    unilaterales += 1
                candidatos.append((vr, ve, br, be))
            if not candidatos:
                continue
            fila = {
                "grupo": grupo,
                "variante": variante,
                "n_pool_comun": len(by_inst) - len(uniformes),
                "n_uniform_missing": len(uniformes),
                "n_double_timeout": doble_timeout,
                "n_double_abort": doble_abort,
                "n_other_double_noncompletion": doble_otro,
                "n_one_sided_capped": unilaterales,
            }

            for col, key in (("tiempo_solver_s", "solver"),
                             ("tiempo_total_s", "total")):
                pares_validos = []
                for vr, ve, br, be in candidatos:
                    xv_i = _valor_pareado(vr, ve, col, timeout)
                    xb_i = _valor_pareado(br, be, col, timeout)
                    if xv_i is not None and xb_i is not None:
                        pares_validos.append((xv_i, xb_i))
                xv = [a for a, _ in pares_validos]
                xb = [b for _, b in pares_validos]
                w, p = wilcoxon_pareado(xv, xb)
                d, mag = cliffs_delta(_clean(xv), _clean(xb))
                fila[f"n_pares_{key}"] = len(pares_validos)
                fila[f"W_{key}"] = w
                fila[f"p_{key}"] = p
                fila[f"cliff_{key}"] = d
                fila[f"cliff_{key}_mag"] = mag
            # Alias histórico: el manuscrito usa el test de tiempo de solver.
            fila["n_pares"] = fila["n_pool_comun"]
            fila["n_pares_no_censurados"] = fila["n_pares_solver"]
            out.append(fila)

    # Corrección por comparaciones múltiples (Benjamini-Hochberg) sobre toda la familia
    # de tests de cada métrica (todas las parejas grupo×variante a la vez).
    for key in ("solver", "total"):
        ajust = benjamini_hochberg([f.get(f"p_{key}") for f in out])
        for f, q in zip(out, ajust):
            f[f"p_{key}_bh"] = q
    return out


def stats_censura(rows: list[dict], timeout: float) -> list[dict]:
    """Conteo de resueltas/timeouts por (grupo, variante) y pares solo-base/solo-variante."""
    out = []
    grupos_presentes = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    grupos_presentes += [g for g in {r.get("grupo") for r in rows}
                         if g and g not in grupos_presentes]
    for grupo in grupos_presentes:
        for variante in ["base"] + VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            n_to = sum(1 for r in items if es_timeout(r, timeout))
            fila = {
                "grupo": grupo, "variante": variante, "n": len(items),
                "resueltas": len(items) - n_to, "timeouts": n_to,
            }
            if variante != "base":
                var_rows, base_rows = emparejar(rows, grupo, variante)
                solo_var = solo_base = ambos_to = 0
                for vr, br in zip(var_rows, base_rows):
                    vto, bto = es_timeout(vr, timeout), es_timeout(br, timeout)
                    if vto and bto:
                        ambos_to += 1
                    elif bto and not vto:
                        solo_base += 1  # variante resuelve, base no
                    elif vto and not bto:
                        solo_var += 1   # base resuelve, variante no
                fila["solo_variante_resuelve"] = solo_base
                fila["solo_base_resuelve"] = solo_var
                fila["ambos_timeout"] = ambos_to
            out.append(fila)
    return out


def stats_correlacion(rows: list[dict],
                      xcol: str = "matrix_kappa_ratio_vs_base") -> list[dict]:
    """Spearman entre una razón de condicionamiento (xcol) y speedup_solver, por
    grupo/variante. xcol = 'matrix_kappa_ratio_vs_base' (rango de coeficientes) o
    'kappa_solver_ratio_vs_base' (κ real de la base reportado por el solver)."""
    out = []
    grupos_presentes = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    grupos_presentes += [g for g in {r.get("grupo") for r in rows}
                         if g and g not in grupos_presentes]
    for grupo in grupos_presentes + ["(todos)"]:
        for variante in VARIANTES_ORDEN + ["(todas)"]:
            items = [
                r for r in rows
                if (grupo == "(todos)" or r.get("grupo") == grupo)
                and (variante == "(todas)" or r.get("variante") == variante)
                and r.get("variante") != "base"
            ]
            xs = [_to_float(r.get(xcol)) for r in items]
            ys = [_to_float(r.get("speedup_solver_vs_base")) for r in items]
            rho, p = spearman(xs, ys)
            if rho is None:
                continue
            out.append({"grupo": grupo, "variante": variante, "x": xcol,
                        "n": sum(1 for a, b in zip(xs, ys)
                                 if a is not None and b is not None),
                        "spearman_rho": rho, "p": p})
    return out


def stats_condicionamiento(rows: list[dict]) -> list[dict]:
    """Mediana (IQR) de las razones de condicionamiento variante/base por (grupo,
    variante): ρ_κ a partir del rango de coeficientes y ρ_κ^solver a partir del número
    de condición REAL de la base reportado por el solver."""
    out = []
    grupos_presentes = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    grupos_presentes += [g for g in {r.get("grupo") for r in rows}
                         if g and g not in grupos_presentes]
    for grupo in grupos_presentes:
        for variante in VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            rk_mat = _clean([_to_float(r.get("matrix_kappa_ratio_vs_base")) for r in items])
            rk_sol = _clean([_to_float(r.get("kappa_solver_ratio_vs_base")) for r in items])
            rr_mat = _clean([_to_float(r.get("matrix_range_ratio_vs_base")) for r in items])
            rr_rhs = _clean([_to_float(r.get("rhs_range_ratio_vs_base")) for r in items])
            rr_obj = _clean([_to_float(r.get("objective_range_ratio_vs_base")) for r in items])
            rr_bnd = _clean([_to_float(r.get("bounds_range_ratio_vs_base")) for r in items])
            warns = _clean([_to_float(r.get("solver_warnings")) for r in items])
            out.append({
                "grupo": grupo, "variante": variante,
                "n_matrix": len(rk_mat),
                "rho_kappa_matrix_med": _median(rk_mat), "rho_kappa_matrix_iqr": _iqr(rk_mat),
                "n_ksolver": len(rk_sol),
                "rho_kappa_solver_med": _median(rk_sol), "rho_kappa_solver_iqr": _iqr(rk_sol),
                # Razones de rango (variante/base) de las 4 familias de coeficientes.
                "ratio_rango_matrix_med": _median(rr_mat),
                "ratio_rango_rhs_med": _median(rr_rhs),
                "ratio_rango_obj_med": _median(rr_obj),
                "ratio_rango_bounds_med": _median(rr_bnd),
                "warnings_med": _median(warns),
            })
    return out


def _grupos(rows: list[dict]) -> list[str]:
    g = [x for x in GRUPO_ORDEN if any(r.get("grupo") == x for r in rows)]
    g += [x for x in {r.get("grupo") for r in rows} if x and x not in g]
    return g


def stats_equivalencia(rows: list[dict]) -> list[dict]:
    """Equivalencia rigurosa por (grupo, variante): % MIP OK (solución del solver
    desescalada sobre el modelo original), % CSV OK (reproducibilidad), violación
    máxima de factibilidad y diferencia relativa de objetivo contra base."""
    out = []
    for grupo in _grupos(rows):
        for variante in VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            n = len(items)
            mipok = sum(1 for r in items if r.get("mip_equivalente") == "OK")
            csvok = sum(1 for r in items if r.get("equivalente_vs_base") == "OK")
            sv = _clean([_to_float(r.get("solver_max_viol")) for r in items])
            rel = _clean([_to_float(r.get("rel_obj_diff_vs_base")) for r in items])
            # "objetivo distinto de base" = diferencia relativa por encima de la tolerancia
            # de equivalencia de objetivo (1e-3); por debajo es ruido dentro del MIP gap.
            n_obj_dif = sum(1 for r in items
                            if (_to_float(r.get("rel_obj_diff_vs_base")) or 0.0) > 1e-3)
            out.append({
                "grupo": grupo, "variante": variante, "n": n,
                "mip_ok": mipok, "mip_ok_pct": 100.0 * mipok / n,
                "csv_ok": csvok, "csv_ok_pct": 100.0 * csvok / n,
                "viol_med": _median(sv), "viol_iqr": _iqr(sv),
                "viol_max": max(sv) if sv else None,
                "rel_obj_med": _median(rel), "rel_obj_iqr": _iqr(rel),
                "rel_obj_max": max(rel) if rel else None,
                "n_obj_difiere": n_obj_dif,
            })
    return out


def stats_desempeno(rows: list[dict], timeout: float) -> list[dict]:
    """Desempeño computacional por (grupo, variante): estado del solver, gap final,
    nodos B&B, iteraciones símplex, tiempo de presolve y reducción de nonzeros."""
    out = []
    for grupo in _grupos(rows):
        for variante in ["base"] + VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            n = len(items)
            n_opt = sum(1 for r in items if r.get("status_solver") == "OPTIMAL")
            n_to = sum(1 for r in items if r.get("status_solver") == "TIME_LIMIT")
            gap = _clean([_to_float(r.get("gap_pct")) for r in items])
            nodos = _clean([_to_float(r.get("nodos_explorados")) for r in items])
            it = _clean([_to_float(r.get("iter_simplex")) for r in items])
            pre = _clean([_to_float(r.get("presolve_time_s")) for r in items])
            redu = _clean([_to_float(r.get("reduccion_nz_pct")) for r in items])
            out.append({
                "grupo": grupo, "variante": variante, "n": n,
                "n_optimal": n_opt, "n_timeout": n_to,
                "gap_med": _median(gap), "gap_iqr": _iqr(gap),
                "nodos_med": _median(nodos),
                "iter_simplex_med": _median(it),
                "presolve_med": _median(pre),
                "reduccion_nz_med": _median(redu),
            })
    return out


def stats_robustez(rows: list[dict], timeout: float) -> list[dict]:
    """Métricas robustas de eficiencia por (grupo, variante incl. base): media geométrica
    desplazada de T_solver (con IC bootstrap), speedup determinista (work/ticks), PAR10 y
    gap de raíz. Campos None en datos de binarios viejos → '--' en la tabla."""
    out = []
    for grupo in _grupos(rows):
        for variante in ["base"] + VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            tsol = [_to_float(r.get("tiempo_solver_s")) for r in items]
            spdet = [_to_float(r.get("speedup_det_vs_base")) for r in items]
            rgap = [_to_float(r.get("root_gap")) for r in items]
            pi = [_to_float(r.get("primal_integral")) for r in items]
            sgm = _sgm(tsol, 1.0)
            lo, hi = _bootstrap_ci(tsol, lambda v: _sgm(v, 1.0))
            out.append({
                "grupo": grupo, "variante": variante, "n": len(items),
                "sgm_tsol": sgm, "sgm_tsol_lo": lo, "sgm_tsol_hi": hi,
                "speedup_det_med": _median(spdet),
                "par10": _par10(tsol, timeout),
                "pi_med": _median(pi),
                "root_gap_med": _median(rgap),
            })
    return out


def stats_steiger(rows: list[dict]) -> list[dict]:
    """Contraste de correlaciones DEPENDIENTES (Williams/Steiger) por grupo y conjunto:
    ¿corr(ρ_κ^solver, speedup) difiere de corr(ρ_κ, speedup)? Comparten la salida (speedup)
    y se miden sobre las mismas instancias. Reporta además la corr. parcial de
    ρ_κ^solver vs speedup controlando por tamaño (nonzeros cargados)."""
    out = []
    for grupo in _grupos(rows) + ["(todos)"]:
        items = [r for r in rows
                 if (grupo == "(todos)" or r.get("grupo") == grupo)
                 and r.get("variante") != "base"]
        # Tríos completos (ambos predictores + salida) para que las 3 corr. compartan n.
        j, k, h, sz = [], [], [], []
        for r in items:
            a = _to_float(r.get("matrix_kappa_ratio_vs_base"))
            b = _to_float(r.get("kappa_solver_ratio_vs_base"))
            c = _to_float(r.get("speedup_solver_vs_base"))
            if a is None or b is None or c is None:
                continue
            j.append(a); k.append(b); h.append(c)
            sz.append(_to_float(r.get("nz_cargados")) or _to_float(r.get("rows_cargadas")))
        n = len(h)
        if n < 4:
            continue
        r_jh, _ = spearman(j, h)
        r_kh, _ = spearman(k, h)
        r_jk, _ = spearman(j, k)
        t, p = (None, None)
        if None not in (r_jh, r_kh, r_jk):
            t, p = steiger_williams(r_jh, r_kh, r_jk, n)
        rp, pp, npar = spearman_parcial(k, h, sz)
        out.append({
            "grupo": grupo, "n": n,
            "r_proxy_speedup": r_jh, "r_solver_speedup": r_kh, "r_proxy_solver": r_jk,
            "steiger_t": t, "steiger_p": p,
            "parcial_rho": rp, "parcial_p": pp, "parcial_n": npar,
        })
    return out


def stats_arbol_cplex(rows: list[dict]) -> list[dict]:
    """Condicionamiento de árbol (CPLEX KappaStats) por (grupo, variante): razón variante/base
    del κ máximo de árbol, atención mediana y fracciones inestable/mal-condicionada."""
    out = []
    for grupo in _grupos(rows):
        for variante in ["base"] + VARIANTES_ORDEN:
            items = [r for r in rows
                     if r.get("grupo") == grupo and r.get("variante") == variante]
            if not items:
                continue
            rk = _clean([_to_float(r.get("kappa_arbol_max_ratio_vs_base")) for r in items])
            att = _clean([_to_float(r.get("kappa_attention")) for r in items])
            uns = _clean([_to_float(r.get("kappa_unstable_frac")) for r in items])
            ill = _clean([_to_float(r.get("kappa_illposed_frac")) for r in items])
            if not (att or rk):       # grupo sin datos CPLEX: se omite
                continue
            out.append({
                "grupo": grupo, "variante": variante, "n": len(items),
                "rho_kappa_arbol_med": _median(rk),
                "attention_med": _median(att),
                "unstable_frac_med": _median(uns),
                "illposed_frac_med": _median(ill),
            })
    return out


# --------------------------------------------------------------------------- #
# Formato LaTeX
# --------------------------------------------------------------------------- #
def _f(value, digits: int = 2) -> str:
    if value is None:
        return "--"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)
    if math.isnan(v):
        return "--"
    if v != 0 and (abs(v) >= 1e4 or abs(v) < 1e-3):
        return f"{v:.{digits}e}"
    return f"{v:.{digits}f}"


def _med_iqr(med, iqr, digits: int = 2) -> str:
    if med is None:
        return "--"
    return f"{_f(med, digits)} ({_f(iqr, digits)})"


def _p_tex(p) -> str:
    if p is None:
        return "--"
    if p < 1e-4:
        return "$<10^{-4}$"
    return f"{p:.4f}"


def tabla_resumen_tex(stats: list[dict]) -> str:
    by_grupo: dict[str, list[dict]] = {}
    for s in stats:
        by_grupo.setdefault(s["grupo"], []).append(s)

    cuerpo = []
    grupos = [g for g in GRUPO_ORDEN if g in by_grupo] + \
             [g for g in by_grupo if g not in GRUPO_ORDEN]
    for gi, grupo in enumerate(grupos):
        filas = by_grupo[grupo]
        cuerpo.append(f"\\multirow{{{len(filas)}}}{{*}}{{{grupo}}}")
        for j, s in enumerate(filas):
            prefijo = "" if j == 0 else "  "
            cuerpo.append(
                f"{prefijo}  & {VARIANTE_LABEL.get(s['variante'], s['variante'])} "
                f"& {s['n']} & {s['mip_ok']} & {s['csv_ok']} "
                f"& {_med_iqr(s['total_med'], s['total_iqr'], 1)} "
                f"& {_med_iqr(s['sp_total_med'], s['sp_total_iqr'])} \\\\"
            )
        if gi < len(grupos) - 1:
            cuerpo.append("\\addlinespace")

    return r"""\begin{table}[H]
\centering
\caption{Resumen estadístico por variante de preprocesamiento y grupo de instancias.
         Tiempos en segundos. Mediana (IQR).}
\label{tab:resumen-preproc}
\begin{tabular}{llccccc}
\toprule
\textbf{Grupo} & \textbf{Variante}
  & $n$
  & \shortstack{MIP\\OK}
  & \shortstack{CSV\\OK}
  & $T_{\text{total}}$ \small{med.\ (IQR)}
  & $\mathrm{speedup}_{\text{total}}$ \small{med.\ (IQR)} \\
\midrule
""" + "\n".join(cuerpo) + r"""
\bottomrule
\end{tabular}
\end{table}
"""


def tabla_wilcoxon_tex(stats: list[dict], col_key: str, titulo: str, label: str) -> str:
    by_grupo: dict[str, list[dict]] = {}
    for s in stats:
        by_grupo.setdefault(s["grupo"], []).append(s)

    cuerpo = []
    grupos = [g for g in GRUPO_ORDEN if g in by_grupo] + \
             [g for g in by_grupo if g not in GRUPO_ORDEN]
    for gi, grupo in enumerate(grupos):
        filas = by_grupo[grupo]
        cuerpo.append(f"\\multirow{{{len(filas)}}}{{*}}{{{grupo}}}")
        for j, s in enumerate(filas):
            prefijo = "" if j == 0 else "  "
            cuerpo.append(
                f"{prefijo}  & {VARIANTE_LABEL.get(s['variante'], s['variante'])} "
                f"& {_f(s.get(f'W_{col_key}'), 1)} "
                f"& {_p_tex(s.get(f'p_{col_key}'))} "
                f"& {_p_tex(s.get(f'p_{col_key}_bh'))} "
                f"& {_f(s.get(f'cliff_{col_key}'), 3)} \\\\"
            )
        if gi < len(grupos) - 1:
            cuerpo.append("\\addlinespace")

    return r"""\begin{table}[H]
\centering
\caption{""" + titulo + r"""}
\label{""" + label + r"""}
\begin{tabular}{llcccc}
\toprule
\textbf{Grupo} & \textbf{Variante} & $W$ & $p$-valor & $q_{\text{BH}}$ & $\delta$ Cliff \\
\midrule
""" + "\n".join(cuerpo) + r"""
\bottomrule
\end{tabular}
\end{table}
"""


def _tabla_por_grupo(stats, columnas_header, fila_fn, caption, label, colspec):
    """Helper genérico: arma una tabla LaTeX agrupada por 'grupo' con multirow.
    fila_fn(s) devuelve el texto de columnas tras '& Variante ' (sin el '\\\\' final)."""
    by_grupo: dict[str, list[dict]] = {}
    for s in stats:
        by_grupo.setdefault(s["grupo"], []).append(s)
    cuerpo = []
    grupos = [g for g in GRUPO_ORDEN if g in by_grupo] + \
             [g for g in by_grupo if g not in GRUPO_ORDEN]
    for gi, grupo in enumerate(grupos):
        filas = by_grupo[grupo]
        cuerpo.append(f"\\multirow{{{len(filas)}}}{{*}}{{{grupo}}}")
        for j, s in enumerate(filas):
            prefijo = "" if j == 0 else "  "
            cuerpo.append(f"{prefijo}  & {VARIANTE_LABEL.get(s['variante'], s['variante'])} "
                          f"{fila_fn(s)} \\\\")
        if gi < len(grupos) - 1:
            cuerpo.append("\\addlinespace")
    return (r"\begin{table}[H]" "\n\\centering\n\\caption{" + caption + "}\n\\label{" + label +
            "}\n\\begin{tabular}{" + colspec + "}\n\\toprule\n" + columnas_header +
            "\n\\midrule\n" + "\n".join(cuerpo) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def tabla_condicionamiento_tex(stats: list[dict]) -> str:
    """ρ_κ (rango de coeficientes), ρ_κ^solver (κ real de la base), razón del rango de RHS
    y nº de advertencias numéricas. Distingue 'mejora de escala aparente' de 'estabilidad real'."""
    header = (r"\textbf{Grupo} & \textbf{Variante} & $n$"
              "\n  & $\\rho_\\kappa$ \\small{med.\\ (IQR)}"
              "\n  & $\\rho_\\kappa^{\\text{solver}}$ \\small{med.\\ (IQR)}"
              "\n  & $\\rho_{\\text{RHS}}$ \\small{med.}"
              "\n  & warn. \\small{med.} \\\\")
    def fila(s):
        return (f"& {s['n_ksolver']} "
                f"& {_med_iqr(s['rho_kappa_matrix_med'], s['rho_kappa_matrix_iqr'])} "
                f"& {_med_iqr(s['rho_kappa_solver_med'], s['rho_kappa_solver_iqr'])} "
                f"& {_f(s.get('ratio_rango_rhs_med'))} "
                f"& {_f(s.get('warnings_med'), 1)}")
    return _tabla_por_grupo(
        stats, header, fila,
        r"Condicionamiento numérico relativo variante/base. $\rho_\kappa$ del rango de "
        r"coeficientes $(\max|a|/\min|a|)$ y $\rho_{\text{RHS}}$ del rango de RHS miden la "
        r"\emph{escala aparente}; $\rho_\kappa^{\text{solver}}$ (número de condición de la base "
        r"reportado por el solver) mide la \emph{estabilidad real}. \textit{warn.}\ es el número "
        r"de advertencias numéricas de Gurobi. Mediana (IQR); valores $<1$ indican mejora.",
        "tab:condicionamiento-preproc", "llccccc")


def tabla_equivalencia_tex(stats: list[dict]) -> str:
    """Equivalencia: % MIP OK (correctitud) y % CSV OK (reproducibilidad), violación máxima
    de factibilidad y diferencia relativa de objetivo contra base."""
    header = (r"\textbf{Grupo} & \textbf{Variante} & $n$"
              "\n  & \\shortstack{MIP OK\\\\(\\%)}"
              "\n  & \\shortstack{CSV OK\\\\(\\%)}"
              "\n  & \\shortstack{viol.\\ máx.\\\\med.\\ (IQR)}"
              "\n  & \\shortstack{$\\Delta z_{\\text{rel}}$\\\\med.}"
              "\n  & \\shortstack{$\\Delta z_{\\text{rel}}$\\\\máx.}"
              "\n  & \\shortstack{$z\\!\\neq\\!z_b$\\\\($n$)}\\\\")
    def fila(s):
        return (f"& {s['n']} "
                f"& {s['mip_ok']} ({_f(s['mip_ok_pct'], 0)}) "
                f"& {s['csv_ok']} ({_f(s['csv_ok_pct'], 0)}) "
                f"& {_med_iqr(s['viol_med'], s['viol_iqr'])} "
                f"& {_f(s.get('rel_obj_med'))} "
                f"& {_f(s.get('rel_obj_max'))} "
                f"& {s['n_obj_difiere']}")
    return _tabla_por_grupo(
        stats, header, fila,
        r"Equivalencia algebraica y reproducibilidad por variante. \emph{MIP OK}: solución del "
        r"solver desescalada, factible en el modelo original (factibilidad $<10^{-4}$, "
        r"integralidad $<10^{-5}$, $|$obj.\ recomputado$-$reportado$|<10^{-3}$). \emph{CSV OK}: "
        r"coincidencia exacta ($10^{-7}$) del CSV postprocesado con base (solo reproducibilidad). "
        r"\textit{viol.\ máx.}: violación absoluta máxima sobre el original; "
        r"$\Delta z_{\text{rel}}$: diferencia relativa de objetivo (escala original) vs.\ base; "
        r"$z\!\neq\!z_b$: nº de instancias con objetivo distinto de base ($>10^{-6}$).",
        "tab:equivalencia-preproc", "llccccccc")


def tabla_desempeno_tex(stats: list[dict]) -> str:
    """Desempeño computacional: estado, gap, nodos, iteraciones símplex, presolve, reducción nz."""
    header = (r"\textbf{Grupo} & \textbf{Variante}"
              "\n  & \\shortstack{Opt./\\\\TO}"
              "\n  & \\shortstack{Gap \\%\\\\med.}"
              "\n  & \\shortstack{Nodos\\\\med.}"
              "\n  & \\shortstack{Iter.\\ simplex\\\\med.}"
              "\n  & \\shortstack{Presolve\\\\(s) med.}"
              "\n  & \\shortstack{Red.\\ nz\\\\(\\%) med.}\\\\")
    def fila(s):
        return (f"& {s['n_optimal']}/{s['n_timeout']} "
                f"& {_f(s.get('gap_med'), 3)} "
                f"& {_f(s.get('nodos_med'), 0)} "
                f"& {_f(s.get('iter_simplex_med'), 0)} "
                f"& {_f(s.get('presolve_med'), 2)} "
                f"& {_f(s.get('reduccion_nz_med'), 1)}")
    return _tabla_por_grupo(
        stats, header, fila,
        r"Desempeño computacional por variante (incluye \emph{base}). \emph{Opt./TO}: nº de "
        r"instancias resueltas a optimalidad / en límite de tiempo. Gap, nodos del B\&B, "
        r"iteraciones de símplex, tiempo de presolve y reducción porcentual de nonzeros del "
        r"presolve de Gurobi: mediana sobre el grupo.",
        "tab:desempeno-preproc", "llcccccc")


def tabla_robustez_tex(stats: list[dict]) -> str:
    """Métricas robustas de eficiencia: sgm(T_solver), speedup determinista, PAR10, gap raíz."""
    header = (r"\textbf{Grupo} & \textbf{Variante}"
              "\n  & \\shortstack{$\\mathrm{sgm}\\,T_{\\text{sol}}$\\\\[s]}"
              "\n  & \\shortstack{speedup$^{\\det}$\\\\med.}"
              "\n  & \\shortstack{PAR10\\\\[s]}"
              "\n  & \\shortstack{PI\\\\med.}"
              "\n  & \\shortstack{gap raíz \\%\\\\med.}\\\\")
    def fila(s):
        return (f"& {_f(s.get('sgm_tsol'), 2)} "
                f"& {_f(s.get('speedup_det_med'), 2)} "
                f"& {_f(s.get('par10'), 1)} "
                f"& {_f(s.get('pi_med'), 4)} "
                f"& {_f((s.get('root_gap_med') or 0) * 100 if s.get('root_gap_med') is not None else None, 2)}")
    return _tabla_por_grupo(
        stats, header, fila,
        r"Métricas robustas de eficiencia por variante (incluye \emph{base}). "
        r"$\mathrm{sgm}\,T_{\text{sol}}$: media geométrica desplazada del tiempo de solver "
        r"($s=1$); speedup$^{\det}$: cociente de tiempo determinista (\texttt{Work}/\textit{ticks}) "
        r"base/variante; PAR10$_{\rm avail}$: tiempo penalizado (timeouts $\times 10$; "
        r"abortos excluidos); $\bar\gamma_{\rm cb}$: gap relativo medio normalizado por "
        r"el horizonte observado del callback; gap raíz: gap relativo al final del nodo raíz. "
        r"Mediana sobre el grupo.",
        "tab:robustez-preproc", "llccccc")


def tabla_steiger_tex(stats: list[dict]) -> str:
    """Contraste de Williams/Steiger entre correlaciones dependientes proxy vs solver."""
    filas = []
    orden = [g for g in GRUPO_ORDEN if any(s["grupo"] == g for s in stats)]
    orden += [s["grupo"] for s in stats if s["grupo"] not in orden and s["grupo"] != "(todos)"]
    if any(s["grupo"] == "(todos)" for s in stats):
        orden += ["(todos)"]
    by = {s["grupo"]: s for s in stats}
    for g in orden:
        s = by.get(g)
        if not s:
            continue
        etq = "Conjunto" if g == "(todos)" else g
        sep = "\\midrule\n" if g == "(todos)" else ""
        filas.append(
            f"{sep}{etq} & {_f(s.get('r_proxy_speedup'), 3)} "
            f"& {_f(s.get('r_solver_speedup'), 3)} "
            f"& {_f(s.get('r_proxy_solver'), 3)} "
            f"& {_f(s.get('steiger_t'), 2)} & {_p_tex(s.get('steiger_p'))} \\\\")
    header = (r"\textbf{Grupo} & $\rho(\rho_\kappa,s)$ & $\rho(\rho_\kappa^{\text{solver}},s)$"
              r" & $\rho(\rho_\kappa,\rho_\kappa^{\text{solver}})$ & $Z$ & $p$ \\")
    caption = (r"Contraste de correlaciones dependientes (Williams/Steiger): "
               r"$\rho_\kappa^{\text{solver}}$ vs.\ $\rho_\kappa$ como predictores del "
               r"$\mathrm{speedup}_{\text{solver}}$ ($s$). $H_0:\rho(\rho_\kappa,s)="
               r"\rho(\rho_\kappa^{\text{solver}},s)$ para correlaciones solapadas medidas sobre "
               r"las mismas instancias; $Z<0$ con $p$ pequeño indica que el condicionamiento del "
               r"solver predice mejor.")
    return (r"\begin{table}[H]" + "\n\\centering\n\\caption{" + caption +
            "}\n\\label{tab:steiger-preproc}\n\\begin{tabular}{lrrrrr}\n\\toprule\n" + header +
            "\n\\midrule\n" + "\n".join(filas) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def tabla_condicionamiento_arbol_tex(stats: list[dict]) -> str:
    """Condicionamiento de árbol (CPLEX KappaStats): κ_max relativo, atención, % inest./mal cond."""
    header = (r"\textbf{Grupo} & \textbf{Variante}"
              "\n  & \\shortstack{$\\rho(\\kappa^{\\text{arbol}}_{\\max})$\\\\med.}"
              "\n  & \\shortstack{$\\mathcal{A}$\\\\med.}"
              "\n  & \\shortstack{\\% inest.\\\\med.}"
              "\n  & \\shortstack{\\% mal cond.\\\\med.}\\\\")
    def fila(s):
        return (f"& {_f(s.get('rho_kappa_arbol_med'))} "
                f"& {_f(s.get('attention_med'), 3)} "
                f"& {_f((s.get('unstable_frac_med') or 0) * 100 if s.get('unstable_frac_med') is not None else None, 1)} "
                f"& {_f((s.get('illposed_frac_med') or 0) * 100 if s.get('illposed_frac_med') is not None else None, 1)}")
    return _tabla_por_grupo(
        stats, header, fila,
        r"Condicionamiento a lo largo del árbol B\&B reportado por CPLEX (\texttt{KappaStats}). "
        r"$\rho(\kappa^{\text{arbol}}_{\max})$: razón variante/base del máximo número de condición "
        r"sobre las bases muestreadas; $\mathcal{A}\in[0,1]$: atención numérica (mayor es peor); "
        r"\% inest./mal cond.: fracción de bases inestables ($\kappa\!\ge\!10^{10}$) y mal "
        r"condicionadas ($\kappa\!\ge\!10^{14}$). Mediana sobre el grupo.",
        "tab:condicionamiento-arbol-cplex", "llcccc")


# --------------------------------------------------------------------------- #
# Figuras
# --------------------------------------------------------------------------- #
def figura_boxplot(rows: list[dict], out: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[aviso] matplotlib no disponible; se omiten figuras.")
        return False

    grupos = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    if not grupos:
        return False
    fig, axes = plt.subplots(1, len(grupos), figsize=(5 * len(grupos), 4.5),
                             sharey=True, squeeze=False)
    for ax, grupo in zip(axes[0], grupos):
        data, labels = [], []
        for v in VARIANTES_ORDEN:
            vals = _clean([_to_float(r.get("speedup_total_vs_base"))
                           for r in rows
                           if r.get("grupo") == grupo and r.get("variante") == v])
            if vals:
                data.append(vals)
                labels.append(VARIANTE_LABEL.get(v, v))
        if not data:
            continue
        ax.boxplot(data, tick_labels=labels, showfliers=False)
        ax.axhline(1.0, ls="--", color="gray", lw=1)
        ax.set_yscale("log")
        ax.set_title(grupo)
        ax.set_ylabel(r"speedup$_\mathrm{total}$ (log)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"[fig] {out}")
    return True


def figura_scatter(rows: list[dict], out: Path,
                   xcol: str = "matrix_kappa_ratio_vs_base",
                   xlabel: str = r"$\rho_\kappa$ (dispersión variante/base)",
                   estilos: dict | None = None,
                   ref_x: bool = True,
                   xlim: tuple | None = None) -> bool:
    """estilos: kwargs extra de ax.scatter por variante (p.ej. color/marker fijos, para
    redundancia no cromática); ref_x=False quita la línea de referencia x=1; xlim recorta
    el eje x a los datos. Defaults = comportamiento histórico."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    fig, ax = plt.subplots(figsize=(7, 5))
    hay_datos = False
    for v in VARIANTES_ORDEN:
        xs, ys = [], []
        for r in rows:
            if r.get("variante") != v:
                continue
            x = _to_float(r.get(xcol))
            y = _to_float(r.get("speedup_solver_vs_base"))
            if x is not None and y is not None and x > 0 and y > 0:
                xs.append(x)
                ys.append(y)
        if not xs:
            continue
        hay_datos = True
        kw = dict((estilos or {}).get(v, {}))
        ax.scatter(xs, ys, s=18, alpha=0.5, label=VARIANTE_LABEL.get(v, v), **kw)
    if not hay_datos:
        plt.close(fig)
        return False
    ax.axhline(1.0, ls="--", color="gray", lw=1)
    if ref_x:
        ax.axvline(1.0, ls=":", color="gray", lw=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    if xlim is not None:
        ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(r"speedup$_\mathrm{solver}$")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"[fig] {out}")
    return True


def figura_perfil_desempeno(rows: list[dict], out: Path, timeout: float,
                            estilos: dict | None = None) -> bool:
    """Perfil Dolan--Moré sobre un pool común y costos operacionales.

    Para cada grupo se eliminan de todas las curvas los registros uniformemente
    no disponibles (``rc != 0`` en las cinco variantes) y los casos sin ningún
    tiempo de terminación admisible. Un ``OPTIMAL`` con ``status=OK`` y ``rc=0``
    usa su tiempo de solver; timeout, abort, fila ausente o tiempo inválido
    reciben ``10*timeout``. Por tanto, todas las curvas de un panel comparten el
    mismo denominador y ``r_iv = c_iv/min_v(c_iv)`` es siempre finito.

    ``estilos`` contiene kwargs opcionales de ``ax.plot`` por variante.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    grupos = [g for g in GRUPO_ORDEN if any(r.get("grupo") == g for r in rows)]
    grupos += [g for g in {r.get("grupo") for r in rows} if g and g not in grupos]
    if not grupos:
        return False
    variantes = ["base"] + VARIANTES_ORDEN
    fig, axes = plt.subplots(1, len(grupos), figsize=(5 * len(grupos), 4.5),
                             squeeze=False)
    algo = False
    for ax, grupo in zip(axes[0], grupos):
        # Razones r_{i,v}=c_{i,v}/min_v c_{i,v} sobre un denominador común.
        by_inst: dict[str, dict[str, dict]] = {}
        for r in rows:
            if r.get("grupo") != grupo:
                continue
            by_inst.setdefault(r.get("instancia") or "", {})[
                r.get("variante")] = r
        ratios: dict[str, list[float]] = {v: [] for v in variantes}
        excluded_uniform = excluded_no_timing = 0
        for d in by_inst.values():
            uniformly_unavailable = all(
                d.get(v, {}).get("rc") not in (None, "0") for v in variantes)
            if uniformly_unavailable:
                excluded_uniform += 1
                continue

            costs: dict[str, float] = {}
            completed: list[float] = []
            for v in variantes:
                row = d.get(v)
                t = _to_float((row or {}).get("tiempo_solver_s"))
                valid = bool(
                    row
                    and row.get("rc") == "0"
                    and row.get("status") == "OK"
                    and row.get("status_solver") == "OPTIMAL"
                    and t is not None and t > 0)
                if valid:
                    costs[v] = t
                    completed.append(t)
                else:
                    costs[v] = 10.0 * timeout
            if not completed:
                excluded_no_timing += 1
                continue
            best = min(completed)
            for v in variantes:
                ratios[v].append(costs[v] / best)

        all_ratios = [value for values in ratios.values() for value in values]
        max_ratio = max(all_ratios, default=1.0)
        if max_ratio <= 1.0:
            taus = [1.0]
        else:
            log_max = math.log10(max_ratio)
            taus = [10.0 ** (log_max * i / 249.0) for i in range(250)]
        for v in variantes:
            rs = ratios[v]
            if not rs:
                continue
            algo = True
            n = len(rs)
            ys = [sum(1 for x in rs if x <= tau) / n for tau in taus]
            kw = dict((estilos or {}).get(v, {}))
            ax.plot(taus, ys, label=VARIANTE_LABEL.get(v, v), lw=1.6, **kw)
        ax.set_xscale("log")
        ax.set_xlabel(r"$\tau$ (factor of best time)")
        ax.set_ylabel(r"fraction solved $\leq \tau$")
        ax.set_title(grupo)
        ax.set_ylim(0, 1.02)
        ax.legend(fontsize=8)
        print(
            f"[perfil] {grupo}: n={len(next(iter(ratios.values()), []))}, "
            f"uniformes_excluidas={excluded_uniform}, "
            f"sin_tiempo_excluidas={excluded_no_timing}, "
            f"tau_max={max_ratio:.6g}")
    if not algo:
        plt.close(fig)
        return False
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"[fig] {out}")
    return True


# --------------------------------------------------------------------------- #
# Export auxiliar
# --------------------------------------------------------------------------- #
def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    campos = list(dict.fromkeys(k for r in rows for k in r.keys()))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path,
                        help="JSON con {grupo: [carpetas]}. Sobreescribe GRUPOS.")
    parser.add_argument("--grupo", action="append", default=[],
                        help="Grupo extra 'Nombre=carpeta1,carpeta2'. Repetible. "
                             "Si se usa, reemplaza GRUPOS por completo.")
    parser.add_argument("--base-dir", type=Path, default=Path("."),
                        help="Directorio base para rutas relativas (def: cwd).")
    parser.add_argument("--timeout", type=float, default=3600.0,
                        help="Límite de tiempo (s) para clasificar censura (def: 3600).")
    parser.add_argument("--output", type=Path, default=Path("ejecuciones/analisis_tesis"))
    args = parser.parse_args()

    if args.config:
        grupos = json.loads(args.config.read_text(encoding="utf-8"))
    elif args.grupo:
        grupos = {}
        for spec in args.grupo:
            if "=" not in spec:
                raise SystemExit(f"--grupo mal formado: {spec}")
            nombre, carpetas = spec.split("=", 1)
            grupos[nombre.strip()] = [c.strip() for c in carpetas.split(",") if c.strip()]
    else:
        grupos = GRUPOS

    rows = cargar_todo(grupos, args.base_dir)
    if not rows:
        raise SystemExit("No se cargaron filas. Revisá las rutas de GRUPOS/--config.")
    # El resto del pipeline conserva la carga descriptiva histórica status=OK.
    # Solo Wilcoxon necesita las filas crudas para retener abortos unilaterales
    # al cap en lugar de eliminarlos antes del emparejamiento.
    rows_pareados = cargar_todo(
        grupos, args.base_dir, incluir_errores=True, anunciar=False)
    if not rows_pareados:
        raise SystemExit("No se cargaron filas crudas para los tests pareados.")

    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    figs = out / "figs"
    figs.mkdir(exist_ok=True)

    resumen = stats_resumen(rows)
    wilcoxon = stats_wilcoxon(rows_pareados, args.timeout)
    censura = stats_censura(rows, args.timeout)
    correlacion = stats_correlacion(rows, "matrix_kappa_ratio_vs_base")
    correlacion_ksolver = stats_correlacion(rows, "kappa_solver_ratio_vs_base")
    condicionamiento = stats_condicionamiento(rows)
    equivalencia = stats_equivalencia(rows)
    desempeno = stats_desempeno(rows, args.timeout)
    robustez = stats_robustez(rows, args.timeout)
    steiger = stats_steiger(rows)
    arbol_cplex = stats_arbol_cplex(rows)

    if _scipy_stats is None:
        print("[aviso] scipy no disponible: Wilcoxon/Spearman quedan en N/D.")

    # Tablas LaTeX
    (out / "tabla_resumen.tex").write_text(tabla_resumen_tex(resumen), encoding="utf-8")
    (out / "tabla_wilcoxon_solver.tex").write_text(
        tabla_wilcoxon_tex(
            wilcoxon, "solver",
            r"Prueba de rangos con signo de Wilcoxon: $T_{\text{solver}}$ variante vs.\ base. "
            r"Se reportan el estadístico $W$, el $p$-valor, el $p$-valor ajustado por "
            r"Benjamini--Hochberg ($q_{\text{BH}}$) sobre la familia de tests, y el tamaño de "
            r"efecto $\delta$ de Cliff.",
            "tab:wilcoxon-preproc"),
        encoding="utf-8")
    (out / "tabla_wilcoxon_total.tex").write_text(
        tabla_wilcoxon_tex(
            wilcoxon, "total",
            r"Prueba de rangos con signo de Wilcoxon: $T_{\text{total}}$ variante vs.\ base "
            r"($W$, $p$-valor, $q_{\text{BH}}$ y $\delta$ de Cliff).",
            "tab:wilcoxon-preproc-total"),
        encoding="utf-8")

    (out / "tabla_condicionamiento.tex").write_text(
        tabla_condicionamiento_tex(condicionamiento), encoding="utf-8")
    (out / "tabla_equivalencia.tex").write_text(
        tabla_equivalencia_tex(equivalencia), encoding="utf-8")
    (out / "tabla_desempeno.tex").write_text(
        tabla_desempeno_tex(desempeno), encoding="utf-8")
    (out / "tabla_robustez.tex").write_text(
        tabla_robustez_tex(robustez), encoding="utf-8")
    (out / "tabla_steiger.tex").write_text(
        tabla_steiger_tex(steiger), encoding="utf-8")
    if arbol_cplex:
        (out / "tabla_condicionamiento_arbol.tex").write_text(
            tabla_condicionamiento_arbol_tex(arbol_cplex), encoding="utf-8")
    write_csv(equivalencia, out / "equivalencia_por_grupo.csv")
    write_csv(desempeno, out / "desempeno_por_grupo.csv")
    write_csv(robustez, out / "robustez_por_grupo.csv")
    write_csv(steiger, out / "steiger_por_grupo.csv")
    if arbol_cplex:
        write_csv(arbol_cplex, out / "condicionamiento_arbol_por_grupo.csv")

    # CSV auxiliares (trazabilidad)
    write_csv(resumen, out / "resumen_por_grupo.csv")
    write_csv(wilcoxon, out / "wilcoxon_por_grupo.csv")
    write_csv(censura, out / "censura_por_grupo.csv")
    write_csv(correlacion, out / "correlacion_kappa_speedup.csv")
    write_csv(correlacion_ksolver, out / "correlacion_kappa_solver_speedup.csv")
    write_csv(condicionamiento, out / "condicionamiento_por_grupo.csv")

    # Figuras
    figura_boxplot(rows, figs / "boxplot_speedup_total.pdf")
    figura_scatter(rows, figs / "scatter_kappa_speedup.pdf",
                   "matrix_kappa_ratio_vs_base",
                   r"$\rho_\kappa$ (rango de coeficientes, variante/base)")
    figura_scatter(rows, figs / "scatter_kappa_solver_speedup.pdf",
                   "kappa_solver_ratio_vs_base",
                   r"$\rho_\kappa^{\mathrm{solver}}$ (cond. de la base, variante/base)")
    figura_perfil_desempeno(
        rows_pareados, figs / "perfil_desempeno.pdf", args.timeout)

    # Resumen por consola
    print("\n=== CORRELACIÓN ρ_κ (rango coef.) vs speedup_solver (Spearman) ===")
    for c in correlacion:
        print(f"  {c['grupo']:<16} {c['variante']:<14} "
              f"rho={_f(c['spearman_rho'],3)} p={_f(c['p'],4)} n={c['n']}")
    print("\n=== CORRELACIÓN ρ_κ^solver (cond. base) vs speedup_solver (Spearman) ===")
    for c in correlacion_ksolver:
        print(f"  {c['grupo']:<16} {c['variante']:<14} "
              f"rho={_f(c['spearman_rho'],3)} p={_f(c['p'],4)} n={c['n']}")
    print("\n=== STEIGER/WILLIAMS: ρ_κ^solver vs ρ_κ como predictores del speedup ===")
    for s in steiger:
        print(f"  {s['grupo']:<16} n={s['n']:<4} "
              f"r(proxy,sp)={_f(s['r_proxy_speedup'],3)} "
              f"r(solver,sp)={_f(s['r_solver_speedup'],3)} "
              f"Z={_f(s['steiger_t'],2)} p={_f(s['steiger_p'],4)} "
              f"| parcial(solver,sp|tam) rho={_f(s['parcial_rho'],3)} p={_f(s['parcial_p'],4)}")
    print("\n=== CENSURA (resueltas/timeouts) ===")
    for c in censura:
        extra = ""
        if c["variante"] != "base":
            extra = (f" | solo-variante={c.get('solo_variante_resuelve')} "
                     f"solo-base={c.get('solo_base_resuelve')} "
                     f"ambos-TO={c.get('ambos_timeout')}")
        print(f"  {c['grupo']:<16} {c['variante']:<14} "
              f"resueltas={c['resueltas']}/{c['n']} timeouts={c['timeouts']}{extra}")

    print(f"\nSalida en: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
