# Realimentación de certificados exactos: ensayo cerrado

Exploración independiente de OMS v1.3.5 y del C++ de la tesis. Leer primero
`feedback-note.pdf` (cuatro páginas) o `RESULTADOS.md`. **No apareció una ventaja
de las dos C sobre reparar o reiniciar sin cortes; no se amplía esta campaña.**
El alcance es un modelo seleccionado por anomalías anteriores, dos solvers,
tres semillas nuevas y máximo tres fases. No es evidencia poblacional.

## Contenido y significado

- `PROTOCOL.md`, `design.json`, cinco `snapshot-*`: procedimiento y hashes fijados
  antes de las nuevas optimizaciones; colas aleatorias y límites explícitos.
- `inputs/`: modelo original cotejado con el MPS y factores diádicos archivados.
- `initial/`, `branches/`: 60 llamadas MIP y logs; auditorías exactas, testigos,
  duales/rayos, Starts, cortes aprendidos y mejores testigos retenidos.
- `preflight-verification.json`: 24 pruebas de validez global heredadas, y cotejo
  de ambos importadores/Starts sin optimizar. No se importan esos cortes o sus
  testigos en los brazos; solo se comparte el escalar de calidad previo 27851.
- `outcomes.csv`: 42 resultados de estrategia (A/B comparten una llamada).
  Costos vacíos significan que no se obtuvo testigo, no inviabilidad global.
- `paired-comparisons.csv`: comparación emparejada de las C con cuatro controles.
- `global-cut-proofs.json`: 24 cortes nuevos con prueba global y exportación segura.
- `cut-observations.csv`: 36 observaciones de cortes activos; cero violaciones
  observadas, tanto agregados como parciales. Una cota suficiente débil no es
  evidencia de una violación real.
- `reported-gaps.json`, `bound-discrepancies.json`: estados nativos y contrastes.
  Este último está vacío. El MILP global **no está certificado óptimo**.
- `independent_check.py`, `verify_cuts.py`: reconstrucción de LP, aritmética racional,
  pruebas globales por cono/caja, exportación e importación y orden de información.
- `test_cuts.py`, `test_verifier.py`: seis tests sobre proyección, conflictos,
  exportación no diádica, una alteración que fortalece y pruebas inválidas.
- `NOTA_PREVENTIVA.md`: condiciones uniformes bajo familias **completas**; existencia
  no implica cálculo eficiente o presupuestos útiles. No es una novedad establecida.
- `QUE_SIGUE.md`: propuesta delimitada para un maestro Benders real del despacho,
  todavía no ejecutada. No se tocó la implementación C++.

Todas las filas originales, objetivo, cotas y dominios se preservan. Los cortes
agregados son redundantes en el MILP monolítico en aritmética exacta; esto **no es
un solver Benders completo**. Los cortes parciales usan técnicas conocidas de
Benders lógico/entero. La validez para otros patrones se comprueba por identidad
y soporte de caja, no por probar solo una lista de patrones conocidos. El banco
de cortes no tiene una prueba de cobertura de todos los patrones desconocidos.

## Reproducir las comprobaciones almacenadas, sin solvers

Desde la raíz del repositorio o de la extracción del ZIP:

```sh
python3 exploration/oms-certificate-feedback-20261014/independent_check.py
python3 -m pytest -q exploration/oms-certificate-feedback-20261014/test_cuts.py exploration/oms-certificate-feedback-20261014/test_verifier.py
python3 exploration/oms-certificate-feedback-20261014/write_report.py
```

El replay necesita Python/NumPy; los tests pytest; la figura Matplotlib. Versiones
en `environment.json`. No se importan interfaces nativas en el replay. Se
reconstruyen los CSV y JSON derivados, de contenido idéntico a lo archivado.
Comprueba 51 LP nuevos (18 óptimos, 33 inviabilidades), nueve usos de cache,
44 patrones distintos (30 inviables), las 48 pruebas de cortes (24 heredadas y
24 nuevas), preservación de modelo/Starts y disponibilidad temporal de certificados.

Para el PDF, desde esta carpeta:

```sh
pdflatex -halt-on-error -interaction=nonstopmode feedback-note.tex
pdflatex -halt-on-error -interaction=nonstopmode feedback-note.tex
```

Las fuentes del informe y la figura se regeneran exactamente con el entorno
registrado. La recompilación puede cambiar metadatos PDF; se coteja el texto,
las cuatro páginas y la ausencia de desbordamientos o referencias indefinidas.

## Volver a ejecutar optimizaciones

Es distinto del replay. Se requieren Gurobi con licencia, HiGHS y SoPlex racional;
los binarios/licencias no se incluyen. La ruta SoPlex está en `infra.py`. La
ejecución archivada usó SoPlex 8.1.0/GMP 6.2.1; hash en `environment.json`.
`run_feedback.py --help` muestra `prepare`, `initial`, `branches`.
Los resultados completos se saltan al reejecutar: **no borrar ni sobrescribir
los resultados archivados para intentar reproducirlos**. En una copia separada,
conservar diseño/entradas y retirar exclusivamente sus carpetas `initial/` y
`branches/` permite ejecutar los niveles `initial` y `branches` con el protocolo
fijado. La duración y las trayectorias numéricas no tienen por qué ser idénticas.
`prepare` solo sirve antes de crear un diseño nuevo; no sustituye al diseño fijado.
`preflight.py` tampoco es necesario para el replay: volver a ejecutarlo cambia
metadatos de importación fijados por hash y exige interfaces nativas.

## Contabilidad y límites

Los tiempos incluyen exportar/importar y cotejar cada llamada, auditoría exacta,
construir/comprobar/exportar cortes, preparar Starts y cache local. El prefijo
compartido se cobra por completo a cada estrategia que lo usa; sus dependencias
se comprueban. A solo cobra su llamada numérica: la auditoría retrospectiva de
su resultado es evaluación externa. Preparar entradas compartidas tarda 0.014 s,
informado aparte. Preflight, tests y replay son validación fuera de los tiempos
del procedimiento. Guardar el JSON final de resultados sucede al cerrar el reloj.

Hasta 30 s solicitados al solver (una llamada o tres de 10 s) no implica igual
trabajo realizado: hay parada por objetivo nominal 28129.51. Solo un testigo
exacto bajo la meta declara éxito del procedimiento. La referencia de ciclo
45 s se ajusta después de importar y no garantiza tiempo real. No hubo excesos.
LP exactos hasta 2 s con watchdog hasta 4 s, sin retuning posterior.

Los presupuestos originales son algebraicos: fila 1e-4 max(1,abs(RHS)), cotas
1e-4; no son tolerancias de UTE/ADME. Residuo exportado del contrato y observado
en cada punto se registran por separado. Presolve/escalado interno normales,
cuatro hilos, gap 1%; Gurobi IF1 en todos los brazos. Base-tight reduce ambas
tolerancias de factibilidad/integralidad a 1e-9. No se generaliza que reducirlas
sea siempre favorable: HiGHS tight fue peor que Base habitual en esta prueba.

## Paquete e integridad

`package_study.py` crea `feedback-artifact.zip` y un `MANIFEST.json` inventariado.
Extrae en una carpeta temporal, verifica todos los hashes antes y después,
ejecuta replay y seis tests, regenera informe/figura y recompila el PDF. Finalmente
coteja OMS v1.3.5 y los cinco ZIP de investigaciones anteriores. El resultado se
escribe **fuera del ZIP** en `VALIDATION.json` para evitar una referencia circular
al hash del propio archivo. El manifiesto raíz del ZIP es el inventario actual;
los manifiestos antiguos solo fijan dependencias importadas.

Código propio bajo MIT (`LICENSE` en la raíz); los datos MIPLIB conservan
procedencia y condiciones de sus autores. No se relicencian como código.
No se incluyeron binarios de solvers ni sus licencias. No se publicó el paquete
ni se modificó la versión de envío OMS.
