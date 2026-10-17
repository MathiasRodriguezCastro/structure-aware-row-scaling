# Seguimiento independiente: aceptación, reparación y decisión

Leé [RESULTADOS.md](RESULTADOS.md) o [decision-note.pdf](decision-note.pdf).
Los resultados quedan fuera del artículo OMS v1.3.5. No se publican ni se modifica
el envío. Este seguimiento continúa el piloto de `oms-generalization-20261014`.

El diseño quedó congelado antes de 80 tratamientos con semillas nuevas. Conserva
cinco modelos, ocho alternativas, 78 llamadas MILP y dos abstenciones contractuales.
Hay 71 entregas verificadas, once LP condicionales y dos testigos factibles exactos
en confirmación. La reparación exacta de desarrollo queda separada y excluida de
esos denominadores. Ningún resultado aquí certifica optimalidad global MILP.

Desde la raíz del repositorio o del artefacto extraído:

```bash
python3 exploration/oms-decision-study-20261014/independent_check.py
python3 -m pytest -q exploration/oms-decision-study-20261014/test_repair.py
python3 exploration/oms-decision-study-20261014/write_report.py
```

El checker usa Python 3.10.12 y NumPy 2.2.6 en el entorno registrado (consultar
`environment.json` para las versiones efectivamente instaladas). No importa
Gurobi, HiGHS, SoPlex, Pyomo o el runner. Los tests necesitan pytest. La
regeneración documental solo necesita Python; compilar el PDF requiere pdfLaTeX
con babel español, lmodern, amsmath, booktabs, tabularx y hyperref.

`package_study.py` prepara el ZIP, verifica todos sus hashes desde una extracción
limpia, ejecuta el checker y los tests sin llamadas solver, regenera los documentos
y recompila el PDF. `MANIFEST.json` inventaría archivos y `VALIDATION.json` registra
el resultado de esa comprobación. La licencia del repositorio y la licencia MIT
del generador STN se incluyen en el ZIP; los MPS conservan su atribución MIPLIB.

Para inspeccionar el protocolo y sus límites:

- `PROTOCOL.md`, `INVESTIGACION.md` y `confirmation/design.json`: diseño, decisiones
  y hashes fijados antes de resultados.
- `confirmation/design-pre-source-check-amendment.json` y los snapshots: se
  conserva una enmienda anterior a cualquier llamada MILP para añadir la
  comprobación separada del punto crudo. No cambió selección ni parámetros.
- `audit-deviations.json`: construcción común no cronometrada, persistencia,
  ausencia de LP exacto en confirmación y límites de generalización.
- `confirmation/models`: modelos originales binary64, factores y diagnósticos.
- `confirmation/runs`: los 80 registros, puntos, verificaciones, logs y reparaciones.
- `confirmation/outcomes.csv`, `prior-indicators.csv`, `bound-discrepancies.json`
  y `independent-verification.json`: salidas del checker independiente.
- `development-source-point.npz`, `development-repair-initial` y
  `development-repair`: desarrollo conservado, separado de confirmación.

No se debe reejecutar `prepare` en un diseño existente, sobrescribir desarrollo
ni alterar las fuentes congeladas para reanudar `solve`. Nuevos experimentos
deben usar una carpeta y un diseño nuevos. Los registros existentes hacen que
`solve` omita llamadas ya completas; eso no es una nueva réplica.

Para ejecutar experimentos nuevos hacen falta Gurobi 13.0.2 con licencia, HiGHS
1.15.1, Pyomo 6.10.1 para regenerar STN y SoPlex 8.1.0 con GMP para LP exactos.
La ruta del SoPlex del desarrollo está en `repair.py`; el binario compilado no se
redistribuye. Su versión y SHA-256 quedan en los registros. Los módulos del piloto,
el kernel de factores y las fuentes originales se incluyen como dependencias en
el ZIP. El replay de los datos guardados no necesita esas herramientas.

Los certificados se refieren a la representación canónica binary64. Los
presupuestos son objetivos numéricos experimentales, no estándares operativos.
Los resultados negativos, límites y abstenciones forman parte de la evidencia.
