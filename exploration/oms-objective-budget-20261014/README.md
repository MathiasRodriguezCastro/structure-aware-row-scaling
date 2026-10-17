# Sensibilidad del objetivo y presupuestos con certificado

Investigación independiente del envío OMS v1.3.5. Leé `objective-note.pdf`
(cuatro páginas), `RESULTADOS.md` y la figura `objective-sensitivity.pdf`.
No hay nuevos MILP, publicaciones, DOI ni modificaciones al manuscrito.

El diseño reutiliza todas las 72 entregas de los 80 tratamientos anteriores,
agrupadas en 41 patrones enteros únicos. Los protocolos distinguen selección
retrospectiva, sensibilidad inicial, umbrales condicionados y extensión selectiva
posterior. Los coeficientes originales no se modifican; se estudia la región
que permiten los presupuestos de aceptación de filas y cotas continuas.

El resultado es una garantía unilateral sobre un patrón ya certificado:
existe una continuación exactamente factible con costo no mayor que el nominal
más epsilon. No es optimalidad global, protección para enteros desconocidos,
estándar económico del operador o prueba de mayor velocidad frente a reparación.

Desde la raíz del repositorio o del ZIP extraído:

```bash
python3 exploration/oms-objective-budget-20261014/independent_check.py
python3 -m pytest -q exploration/oms-objective-budget-20261014/test_rational_lp.py exploration/oms-objective-budget-20261014/test_policy.py
python3 exploration/oms-objective-budget-20261014/write_report.py
```

El replay requiere Python/NumPy; los seis tests, pytest; el informe y figura,
Matplotlib. No se importan ni ejecutan solvers para esas comprobaciones.
Los adaptadores aritméticos anteriores se incluyen fijados por sus manifests;
no hay dependencia de servicios externos para la verificación almacenada.
`independent_check.py` reconstruye cada LP desde las filas, costos, cotas y
enteros originales sin importar su constructor; comprueba sus primales/duales
y rayos mediante aritmética racional.

`curves.csv`, `endpoints.csv` y `feasibility-thresholds.csv` contienen la medida
ajustada del costo y los umbrales. `protected-budgets.csv` compara con el dual
fijo. `selective-budgets.csv` valida la primera variante selectiva con LP exacto.
`row-only-proofs.json` demuestra después que basta reducir 40 presupuestos de
fila y mantener todos los presupuestos de cotas, sin otra llamada solver.
Ese último archivo contiene una cota suficiente, no una nueva afirmación de
óptimo del LP selectivo. `policy-outcomes.csv` separa aceptación, corrección,
abstención y cumplimiento de los presupuestos restringidos.

Se conservan las 208 llamadas LP, incluida una con error numérico. Su umbral
cero se demuestra directamente con un punto exacto anterior y lambda>=0;
`derived-feasibility-proofs.json` separa esa prueba de la ejecución fallida.
El constructor se corrigió antes de la primera llamada al detectar una pérdida
de coeficientes en las cotas de lambda. `design-before-first-lp.json` y
`pre-solve-correction.json` conservan ese cambio, sin alterar muestras o parámetros.

`sensitivity.py prepare` no sobrescribe diseños. Las fases de resolución omiten
registros completos; repetir una orden sobre esta carpeta no es otra réplica.
Para un experimento nuevo hay que crear un diseño y carpeta distintos. Las
nuevas llamadas requieren SoPlex 8.1.0/GMP en la ruta documentada del repositorio
completo; su hash se conserva por llamada, y su binario no se distribuye.

`package_study.py` crea `objective-artifact.zip` y valida una extracción limpia:
hashes antes/después, checker, seis tests, texto y figura regenerados, PDF
recompilado y hashes de OMS y de los cuatro paquetes previos. `MANIFEST.json`
de la raíz del ZIP inventaría el paquete; los manifests anteriores solo fijan
dependencias. `VALIDATION.json` registra el hash del ZIP y los resultados.

El código mantiene la licencia MIT de `LICENSE`; los MPS de terceros mantienen
la procedencia MIPLIB y no se relicencian mediante la licencia del código.
Las fuentes y antecedentes se enlazan en el informe. Los certificados son del
modelo canónico binary64; en nive todos los literales MPS son exactos en esa
representación. Los presupuestos experimentales también se contabilizan como
racionales binary64, sin confundirlos con tolerancias operativas oficiales.
