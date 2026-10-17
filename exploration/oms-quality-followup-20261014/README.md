# Seguimiento de calidad y ablación de representación

Leé `RESULTADOS.md` o `quality-note.pdf`. Son investigación independiente del
envío OMS v1.3.5. No hay publicación, nuevo DOI ni modificaciones al paper.

Dos diseños separados y conservados:

- `PROTOCOL.md`, `confirmation/design.json`: 48 tratamientos, tres MIPLIB
  previamente seleccionados, semillas nuevas 31/47, controles en frío, Starts
  reparados y testigos previos. Fuentes congeladas antes de esas llamadas MILP.
- `ABLATION_PROTOCOL.md`, `ablation/design.json`: 14 tratamientos con semillas
  59/71. La selección posterior de control30-3-2-3 investiga una señal observada;
  es un estudio de mecanismo, no validación independiente de generalización.

Cada diseño conserva sus snapshots, modelos, factores, logs, puntos, tiempos y
resultados desfavorables. La representación entre fases escala filas/RHS
equivalentes sin cambiar objetivo, coordenadas o dominios. Todos los controles
usan igual suma máxima de límites MILP; el costo completo se registra.

Desde la raíz del repositorio o del ZIP extraído:

```bash
python3 exploration/oms-quality-followup-20261014/independent_check.py
python3 exploration/oms-quality-followup-20261014/check_ablation.py
python3 -m pytest -q exploration/oms-quality-followup-20261014/test_controller.py exploration/oms-quality-followup-20261014/test_report_gate.py
python3 exploration/oms-quality-followup-20261014/write_report.py
```

Replay: Python 3.10.12 y NumPy 2.2.6; los nueve tests requieren pytest.
Los checkers no importan runners, controladores, módulos de reparación o solvers.
Reutilizan el checker aritmético independiente anterior, fijado por su manifest,
y cotejan los MPS originales sin llamadas de optimización. La regeneración
documental usa Python; compilar el PDF necesita pdfLaTeX con español, lmodern,
amsmath, booktabs, tabularx y hyperref. Versiones y CPU en `environment.json`.

`package_study.py`, desde este repositorio completo, crea `quality-artifact.zip`
y valida una extracción limpia: hashes antes/después, ambos checkers, nueve
tests, regeneración del texto y recompilación del PDF. `MANIFEST.json` es su
inventario y `VALIDATION.json` registra los resultados. El manifest del estudio
anterior se incluye únicamente para fijar la dependencia aritmética; el inventario
del ZIP actual es el `MANIFEST.json` de su raíz.

Fuentes y antecedentes del piloto se incluyen como dependencias, con la licencia
MIT de STN y atribuciones MIPLIB. Los binarios de solvers y sus instalaciones no
se redistribuyen. Para llamadas nuevas se requieren Gurobi 13.0.2 con licencia,
HiGHS 1.15.1 y SoPlex 8.1.0/GMP. La ruta SoPlex del repositorio se conserva en
el módulo de reparación, y los registros fijan su hash. Repetir datos almacenados
no necesita ninguna de esas herramientas.

No se sobrescriben diseños existentes, fuentes congeladas ni puntos de desarrollo.
`solve` omite registros completos; ejecutarlo de nuevo así no es una nueva
réplica. Experimentos adicionales requieren un diseño y una carpeta nuevos.

`GARANTIAS.md` distingue aceptación, retención, veto de cotas y optimalidad.
`report_gate.py` añade un filtro de consistencia del gap; se aplica a posteriori
sin modificar las fuentes experimentales congeladas. `INCORPORACION_CANDIDATA.md`
deja una redacción acotada para revisión futura, fuera del manuscrito.

Los certificados corresponden al modelo canónico binary64. Los presupuestos
son numéricos algebraicos, no estándares físicos. Testigos exactos, entregas
flotantes y cotas/optimalidad permanecen separados, también cuando un solver
declara terminación óptima. No se concluye superioridad general por un caso.
