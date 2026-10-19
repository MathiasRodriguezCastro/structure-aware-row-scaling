# Seguimiento científico para evaluar una posible v1.5

La versión de envío sigue siendo **v1.4.2-orf-submission**. Este directorio
contiene una investigación separada, no una nueva versión lista para enviar.

Leer [RESULTADOS.md](RESULTADOS.md), [research-note.pdf](research-note.pdf) y
[MATH_NOTE.md](MATH_NOTE.md). Las decisiones y los resultados desfavorables se
conservan. La campaña no establece una aceleración general de soluciones
verificadas frente a L2 ni recuperación adicional de precisión en los cuatro
requisitos ensayados. El prototipo sí incorpora la exportación efectiva a la
selección y permite comprobar las incompatibilidades de la condición suficiente.

## Evidencia y procedencia

- `PROTOCOL.md` y `design.json`: 630 asignaciones, fijadas antes de los nuevos
  MIP. Se reutilizan 24 escenarios conocidos; las semillas nuevas no son
  problemas nuevos ni otra aplicación.
- `runs/`: todos los eventos y vectores de candidatos, puntos finales, trazas
  nativas, parámetros y costos de etapas.
- `models/` y `EXPORTS.json`: exportes inmutables e identidad con los hashes
  realmente importados. Cada fila tiene un coeficiente original +/-1, que
  permite recuperar exactamente el factor del producto escrito. Los exportes
  reconstruidos se vuelven a escribir y contrastar con todos los hashes nativos.
- `original-study.py`, `original-timing.json`, `AMENDMENT_01.json` y
  `failed-before-optimization/`: un fallo de lectura de filas escaladas antes
  de crear el optimizador y su corrección; se conserva la primera llamada
  completada. El filtro exacto de calidad evita comprobaciones residuales de
  candidatos que no pueden cumplir ninguno de los dos objetivos.
- `TECHNICAL_REPEAT_PLAN.json`, `technical-repeat/`, `TECHNICAL_REPEAT.json`:
  una repetición predeterminada del primer caso Base para unificar los tiempos
  del verificador. Vectores, trabajo, endpoints e índices de primer éxito son
  idénticos; no añade observaciones independientes. Total: 630 MIP principales
  más una repetición técnica. Las dos pruebas sintéticas de licencia de CPLEX
  se identifican aparte; una no pudo resolver por el límite Community.
- `projection_sensitivity.py`: sensibilidad posterior identificada como tal,
  motivada por desviaciones diminutas de cotas de CPLEX. Proyecta los puntos
  sobre sus cotas y vuelve a comprobarlos. No altera el criterio primario ni
  atribuye tiempos medidos de disponibilidad a ese posprocesamiento nuevo.
- `export_selector.py`: prototipo exhaustivo usado en las resoluciones.
  `export_selector_fast.py` y `SELECTOR_BENCHMARK.json`: ordenación posterior
  que conserva todos los exportes completos; solo compara costo de selección.
- `selection-certificates.csv`, `precision-by-family.csv`,
  `incompatible-contracts.csv`: reservas efectivas, márgenes y las 8.256 filas
  en 22 modelos que agotan el contrato suficiente con activación de 1 m3.
  Esto no es un certificado de infactibilidad del modelo.

## Reproducción de datos guardados

Desde la raíz del repositorio, con los escenarios prospectivos y la evidencia
heredada de v1.4.2 disponibles, sin Gurobi ni CPLEX:

```sh
python3 exploration/orf-v15-verified-20261019/check.py
python3 exploration/orf-v15-verified-20261019/check_selector.py
python3 exploration/orf-v15-verified-20261019/precision.py
python3 exploration/orf-v15-verified-20261019/analyze.py
python3 exploration/orf-v15-verified-20261019/check_statistics.py
python3 exploration/orf-v15-verified-20261019/projection_sensitivity.py
python3 exploration/orf-v15-verified-20261019/write_report.py
```

Usa Python, NumPy y los lectores abiertos de la evidencia heredada. El replay
certifica presupuestos y condiciones para los números guardados, no óptimos
MILP. La referencia de calidad es un testigo racional factible de cada modelo.
La verificación registrada requiere presupuesto físico crudo y redondeado,
distancia entera <=1e-9, cotas exactas después de redondear y error hacia atrás
<=1e-6 para filas sin unidad física. El cumplimiento de esa definición no es
factibilidad exacta de todas las filas.

Los intervalos primarios agrupan los 24 escenarios con sus tres semillas
juntas. Los controles de robustez tienen 12 o 6 grupos. Todos son intervalos
marginales condicionados a padres conocidos, no validación externa. PAR2
penaliza fallos; no es un tiempo real observado ni una prueba de superioridad.

Para compilar el informe, ejecutar dos veces pdfLaTeX sobre `research-note.tex`.
`benchmark_selector.py` permite repetir el perfil de compilación en procesos
nuevos y exige identidad de los exportes; no llama a un optimizador.

## Nuevas resoluciones

Requieren Gurobi 13.0.2, CPLEX 22.1.2 completo y el generador C++ heredado.
La API CPLEX Community instalada por defecto no admite los modelos mayores.
El corredor usa la biblioteca completa indicada y hasheada en `design.json`,
sin distribuir software propietario ni archivos de licencia. Registrar una
nueva campaña en otro directorio y preservar esta evidencia; las enmiendas y
la repetición técnica de aquí documentan solo la campaña histórica.

Las unidades de trabajo de Gurobi y CPLEX no son comparables entre solvers.
Los presupuestos son escenarios numéricos, no estándares oficiales del operador.
Las licencias generales del repositorio siguen aplicándose; no se ha publicado
un DOI nuevo ni enviado un manuscrito mediante estos scripts.

Referencias de implementación: [callbacks de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/callbacks.html)
y [parámetros](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html).
