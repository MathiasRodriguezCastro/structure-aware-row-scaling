# Transferencia y costo comprobable

Leé `transfer-note.pdf` (cuatro páginas) o `RESULTADOS.md`. Esta investigación
se conserva aparte del envío OMS v1.3.5, sin publicación ni cambios al paper.
`INCORPORACION_CANDIDATA.md` contiene una posible redacción breve para revisión.

Se separan dos diseños:

- `SELECTION.json`, `PROTOCOL.md`, `confirmation/design.json`: 80 tratamientos
  fijados antes de resolver; cuatro grupos MIPLIB no usados y una referencia
  conocida, semillas 83/97, Gurobi y HiGHS, controles fuertes y sin warm starts.
- `COST_AUDIT_PROTOCOL.md`, `cost-audit/design.json`: auditoría posterior de
  los 16 patrones enteros de nive, fijada antes de sus LP adicionales. No es
  un endpoint prospectivo de los 80 tratamientos. Los cuatro rayos ya guardados
  se verifican después, sin nuevas llamadas de optimización.

Se conservan modelos originales, factores, exportaciones, parámetros efectivos,
puntos, intentos sin entrega, logs, tiempos, certificados primales/duales y
rayos de inviabilidad del patrón. La transformación escala filas y RHS por el
mismo factor; conserva objetivo, coordenadas, cotas y dominios.

Desde la raíz del repositorio o del ZIP extraído:

```bash
python3 exploration/oms-transfer-study-20261014/independent_check.py
python3 exploration/oms-transfer-study-20261014/cost_audit.py replay
python3 exploration/oms-transfer-study-20261014/check_cost_rays.py
python3 -m pytest -q exploration/oms-transfer-study-20261014/test_cost_certificate.py exploration/oms-transfer-study-20261014/test_farkas_certificate.py
python3 exploration/oms-transfer-study-20261014/write_report.py
```

La verificación guardada requiere Python 3.10 y NumPy; los seis tests requieren
pytest. No importa solvers ni los ejecuta. El checker aritmético anterior está
fijado por su manifest. El adaptador MPS de este estudio vuelve a cotejar todos
los coeficientes, RHS, costos, cotas y dominios. Los certificados de costo y
Farkas usan únicamente aritmética racional sobre los datos originales canónicos.
Los recuentos son de tratamientos, no de patrones únicos: las entradas idénticas
L2/Budget en nive duplican patrones y no constituyen réplicas independientes.

El costo certificado es el mínimo del LP **con los enteros de esa entrega
fijados**. Su cota inferior no es global para el MILP; un rayo tampoco prueba
inviabilidad global. Verificar presupuestos primales, verificar factibilidad
exacta y certificar optimalidad global son resultados diferentes. `outcomes.csv`
separa costo nominal y mejor costo factible exacto obtenido en cada tratamiento;
la auditoría posterior añade los mínimos de cada patrón, sin cambiar las entregas.

`environment.json` fija las versiones y el equipo. Nuevas resoluciones necesitan
Gurobi con licencia, HiGHS y SoPlex/GMP; no se redistribuyen binarios ni licencias.
El módulo de reparación conserva la ruta de SoPlex del repositorio completo.
`transfer.py solve` y `cost_audit.py solve` omiten registros completos; repetir
esas órdenes no produce otra réplica. Para otra réplica se necesita una carpeta
y un diseño nuevos, sin sobrescribir fuentes o resultados congelados.

`package_study.py`, desde el repositorio completo, produce `transfer-artifact.zip`
y valida una extracción limpia: todos los hashes antes/después, los tres
checkers, seis tests, regeneración del texto y recompilación del PDF. El
`MANIFEST.json` de la raíz del ZIP inventaría ese archivo; el manifest del
estudio anterior solo fija la dependencia aritmética. `VALIDATION.json` registra
el hash del ZIP y las comprobaciones realizadas.

El código conserva la licencia MIT de `LICENSE`. Los MPS son de terceros y
mantienen su procedencia MIPLIB en `sources/miplib-models/provenance.json`;
la licencia del código no los relicencia. Las fuentes primarias se enlazan en
el informe. No hay datos operativos nuevos ni presupuestos físicos de planta:
los presupuestos del experimento son algebraicos y quedan explícitos.
