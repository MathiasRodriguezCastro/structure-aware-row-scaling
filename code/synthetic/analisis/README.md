# Análisis de la grilla sintética

Análisis reproducible de la grilla de MIPs sintéticos bloque-estructurados. Es un paso
**separado** del generador: solo **lee** los CSV de resultados (no los modifica) y produce
tablas + figuras paper-ready. No toca el C++ ni el flujo hidrotérmico.

## Comando exacto

```bash
cd Implementacion_Cpp/Codigo_Cpp
LC_ALL=C python3 synthetic/analisis/analizar_grilla_sintetica.py
# opcional: --results-dir <carpeta_con_metrics.csv>   (default: synthetic/resultados/grilla_inicial_gurobi)
```

Dependencias: `pandas`, `numpy`, `scipy`, `matplotlib` (probado con pandas 2.3, numpy 2.2,
scipy 1.15, matplotlib 3.10).

### Nota de locale (`LC_ALL=C`)

El script lee los CSV con `decimal='.'` explícito, así que **no** depende de `LC_NUMERIC`.
Aun así, conviene correrlo con `LC_ALL=C` para que cualquier post-proceso shell (awk/sort)
sea consistente: en locales con coma decimal (es_*), `awk '{print $n+0}'` trunca
`"1.8e-12"` a `1` y corrompe el análisis. Los CSV en sí están bien (C++ escribe con punto).

## Inputs esperados

En `--results-dir` (default `synthetic/resultados/grilla_inicial_gurobi/`):

- `metrics.csv` — una fila por `(instancia, variante)`. **Requerido.**
- `summary_by_pattern_severity_variant.csv` — resumen del runner (no es necesario para el análisis;
  el script recomputa todo desde `metrics.csv`).

## Outputs generados (en `<results>/analysis/`)

### Tablas

| Archivo | Contenido |
|---|---|
| `synthetic_summary_table.csv` / `.tex` | Por `(pattern, S, variante)`: `n`, `n_feasible`, `n_status_ok`, medianas de κ antes/después, factor de reducción, reducción en log10, ρ antes/después, tiempos, y violaciones máximas. El `.tex` es para apéndice. |
| `synthetic_conditioning_reduction.csv` | Comparaciones **vs Base** por `(pattern, S, variante≠Base)` para `log10(κ_post)` y `log10(ρ_post)`: `n_pairs`, `median_diff_log10_vs_base` (tamaño de efecto), `wilcoxon_stat`, `p_value`, `p_value_bh` (Benjamini–Hochberg por métrica). Wilcoxon signed-rank pareado por instancia (misma seed). |
| `synthetic_objective_feasibility_checks.csv` | Por `(pattern, S)` + fila `TOTAL`: `max_rel_obj_spread` (entre variantes, por instancia), `n_instancias_over_mipgap`, `max_original_row_violation`, `max_integrality_violation`, `n_infeasible_rows`. |

### Figuras (`.pdf` + `.png`)

| Archivo | Qué muestra |
|---|---|
| `fig1_boxplot_log10_kappa_despues` | Distribución de `log10(κ_post)` por variante, grilla `pattern × S`. Detalle de dispersión. |
| `fig2_bars_log10_reduction` | Reducción mediana de condicionamiento `log10(κ_pre) − log10(κ_post)` por variante, grilla `pattern × S`. Resultado principal. |
| `fig3_kappa_antes_vs_S` | `κ_pre` (mediana, escala log) vs `S`, una línea por `pattern`. Valida que el desbalance lo controlan `pattern` y `S`. |
| `fig4_feasibility_violations` | Violaciones máximas (fila + integralidad) por `pattern/S`, escala log, con la tolerancia 1e-5. |

## Métricas / método

- **Reducción de condicionamiento** se mide en `log10` (escala apropiada para κ que abarca
  ~10³–10¹⁴). El tamaño de efecto reportado es la **mediana de la diferencia pareada** en
  `log10` respecto de Base.
- **Significancia**: Wilcoxon signed-rank pareado por instancia, con ajuste **BH** por familia
  de comparaciones (una familia por métrica).
- **Equivalencia**: se controla que el objetivo entre variantes no difiera más que el `mipgap`
  y que las violaciones en escala original queden bajo tolerancia.

> Enfoque deliberado: las instancias son chicas (resuelven en ms). El análisis **no** mide
> speedup; se enfoca en control del desbalance, recuperación del condicionamiento y
> preservación de factibilidad/objetivo.
