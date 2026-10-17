# Decisión de alcance para OMS — 14 de octubre de 2026

La continuación autorizada encontró una contribución práctica que merece
incorporación acotada: contratos activos en filas de activación, mejora de
precisión comprobada frente a un control de factores y testigos factibles exactos
para separar ese resultado de la validez de las cotas de optimalidad.

Se prepara v1.3.3 conservando intacta v1.3.2 y los resultados originales.
El detalle completo, incluyendo todos los controles y la sensibilidad que
limita la mejora, está en
[RESULTADOS.md](../../exploration/oms-followup-20261014/RESULTADOS.md).
Se conserva la garantía condicional primal, no se añade un teorema ni se
presentan los objetivos de precisión como estándares físicos del operador.

## Revisión editorial v1.3.4

Se aplican las observaciones del revisor sin ampliar experimentos: tabla compacta de
activación en el cuerpo, antigua discusión exploratoria en el suplemento, aporte de
precisión integrado y sensibilidad de rendimiento sobre los seis escenarios sin
defecto visible en artículo y carta. Las reducciones de trabajo siguen siendo
condicionales y no constituyen certificaciones de optimalidad. v1.3.3 se conserva
intacta; la nueva entrega se compila y verifica extraída antes de congelarla.

## Final checks v1.3.5

Table 11 English corrected; Section 7.9 explicitly states the higher presolve-off
solver work and remaining bound discrepancies. Cover letter unchanged. The final
package is checked from clean extractions, including PDF identity across archives
and upload files, manuscript/supplement/metadata version consistency, file inventory
checksums before and after numerical replay, and table regeneration. No new solves.

## Incorporación de inicialización v1.3.6 — 15 de octubre de 2026

Se aplica la nota del autor: un párrafo en 7.3 y el protocolo, la tabla S14,
los costos de adquisición y las verificaciones en el suplemento. El diagnóstico
es explicativo y no constituye una tercera contribución. El banco auxiliar
MPS/potencias de dos no se confunde con la campaña histórica LP. Los puntos
iniciales se obtuvieron fuera de línea y no son un algoritmo gratuito. Dos
continuaciones LP desconocidas se conservan. Se distribuyen todos los registros
necesarios para el replay en Supplementary Material 2, sin añadir llamadas de
optimización durante la incorporación. Abstract, introducción y carta intactos;
la nueva entrega se verifica extraída antes de congelar v1.3.6.

## Matched IF control and workflow v1.3.7

Section 7.9 adds a short matched IntegralityFocus=1 control. Supplementary
Material 1, Table S15 reports original-unit accuracy, bound/gap discrepancies
and full fresh-process prototype costs. Twelve principal calls and a retained
twelve-call instrumentation pass have identical native endpoints and saved points;
the import checker was made linear in vector access without changing its checks.
Both passes and independent replay are supplied under
`exploration/oms-if1-workflow-20261015/`. This is one known case on a shared machine,
with no new reference LPs or general performance claim. Abstract, introduction,
two contributions and cover letter are unchanged; v1.3.6 remains frozen.

## Editorial reconciliation v1.3.8 — 16 October 2026

No new optimization calls. Main Table 11 and Supplementary Table S12 use the
geometric mean of Budget-L2 Work (4.4847271866, displayed 4.485); Table S15 and
the workflow note use the median (4.9754950464, displayed 4.975). The per-seed
values and native settings match; the explanation is now explicit in all three
documents. `scripts/research/reconcile_oms_work.py` checks the native provenance.
The cover letter is shorter and centers the two methodological/software contributions.
All prior frozen releases and research archives are retained. The author will create
a new-version Zenodo draft and provide its reserved DOI before final deposition.

## 16 October 2026 — fully matched accuracy/remedy confirmation, v1.3.9

144 terminal comparisons on six known clean-demand models, with 145 native attempts
including one preserved reboot interruption. Exact reader-only replay checks all
points and twelve existing witnesses. Primal recovery versus L2 remains confined
to instance046 with presolve disabled. NF3 meets every primal budget with no
detected bound/gap contradiction; Budget has lower geometric-mean Work but retains
one/three bound discrepancies under auto/off presolve. Main Section 7.9 and Table
S16 state that tradeoff without claiming a generally preferred policy. Full process
stages are supplied. No new principal contribution, external generalization, full
precision–cost frontier, corrected-demand campaign or optimality certificate is
claimed. The independent-generator pilot remains negative for added primal utility.
See exploration/oms-matched-accuracy-20261016/DECISION.md for the complete scope audit.
The abstract and two principal contributions remain unchanged; the introduction
explains the workflow earlier and the cover explicitly identifies the known
presolve-off contrast. DOI/deposition remain deferred.

## Reproducibility and presentation revision v1.3.10 — 16 October 2026

No new research solver calls. The fully matched 144-call comparison replaces the
old mixed-panel main Table 11; S11–S12 and S15 retain the earlier results and
geometric-mean/median reconciliation. The abstract and conclusions explicitly
localize primal recovery versus L2 to instance046 with presolve disabled. The
two principal contributions are retained. Zero detected bound/gap discrepancies
is not an optimality certificate.

The same independent stress verifier now runs on both the HiGHS/Gurobi archive
and the byte-identical-model CPLEX archive: 5,184 configurations, 432 abstentions,
4,752 historical optimizer calls and 1,152 exact dyadic export checks. S3 now
records recent local campaign hardware/timing scope. S2 calls floating-point upper
endpoints diagnostic estimates and retains rational certification for lower bounds.
The four standard audit/analysis commands are checked from a clean Material 2
extraction. Historical basis reconstruction/precision reruns additionally need
fixed-basis-exports.tar.zst from baseline DOI 10.5281/zenodo.23145294.
Earlier frozen versions and closed research archives are preserved. DOI and
remote deposition remain deferred at the author's request.

The expanded four-command audit caught two omitted stopped-campaign analysis CSVs.
They are now explicitly included and inventoried despite the bulk-directory filter.
The certificate-table generator raises on missing inputs, with two regression tests;
targeted clean replay preserves both historical tables and their counts. This is
a packaging/replay correction, not new solver evidence or exact certification of
the historical numerically screened points.

## Nueva autorización y resultados — 16-10-2026, v1.3.11

La propuesta adjunta de Mathias reabrió la búsqueda acotada. Se completaron 330
MILP de frontera, 30 abstenciones, 31 LP testigo, 336 preparaciones cronometradas
(con ambas pasadas conservadas), 54 MILP únicos del prototipo conjunto/ablación,
seis LP de testigo Base, seis LP globales y 13 LP de refinamiento.

El criterio prospectivo de frontera se cumple en los seis modelos para 30 y
100 m3 con presolve auto. Se incorpora brevemente; no extiende la recuperación
primal a otro modelo. La integración C++ y los intervalos globales se documentan
en el suplemento con límites explícitos. La extensión conjunta obtiene efectos
de trabajo reales y certificados matemáticos, pero permanece separada: su
novedad y validez externa no están establecidas. No se retoman DW, cortes ni
predictores. Ninguno de estos resultados vuelve innegable una publicación.

## Revisión de presentación — 16-10-2026, v1.3.12

Se atiende la corrección editorial indicada por Mathias sin ejecutar otra campaña.
El abstract y la introducción destacan la banda de 30–100 m3 ya observada. La nueva
Tabla 12 principal resume los siete presupuestos con presolve automático y conserva
abstenciones, contradicciones y representaciones repetidas. La S17 completa permanece
en el suplemento; ambas tablas se derivan del mismo CSV verificado. Se corrige la
afirmación desactualizada sobre optimalidad exacta: hay un certificado del modelo
Base instance031, que no certifica todas las salidas nativas.

La validación en una familia independiente sigue siendo un límite. Las prioridades
exploratorias del adjunto (mecanismo por fila, tolerancia entera, ciclo C++ completo y
refinamiento específico) no se declaran realizadas por esta revisión ni se usan para
ampliar sus afirmaciones. Los pilotos externos anteriores conservan sus resultados
adversos. La extensión conjunta permanece separada, en particular por usar un
22,2 % más de trabajo emparejado que Budget-L2 en el control fuerte disponible.
Se conservan las versiones congeladas y se pospone el DOI según la preferencia del autor.

## Seguimiento científico acotado — 17-10-2026, v1.3.13

Se completaron las cuatro líneas solicitadas. La fuente STN externa aporta ocho
horizontes prefijados (dos anclas previas), 96 comparaciones y ocho referencias;
Budget-L2 y L2 cumplen 24/24, NF3 23/24. La violación NF3 de 111 mg frente a
10 mg tiene residuo exportado menor que epsilon. Es transferencia y trazabilidad,
no recuperación exclusiva sobre L2. Siete refinamientos exactos permanecen
desconocidos y 84 contrastes de cotas no tienen testigo.

La sensibilidad gamma agrega 36 llamadas y 18 abstenciones a 54 reutilizadas.
A2^-28 se agota30m3 en seis modelos; a100m3 hay una cota contradicha. La
ausencia de flags no es robusta al cambio. La inspección directa identifica
53.280 factores compatibles y ninguna modificación fuera de activación, sin
atribuir una causa a operaciones internas del solver.

El ciclo C++/Python agrega36 llamadas con18 pares idénticos en todos los datos,
puntos, endpoints y Work. Razón de tiempo total0.824; no hubo otra campaña propia
de solver simultánea. Se documenta como evidencia de software del mismo método.
Se incorporan estas evidencias brevemente, con S18 ampliada y S20–S21 nuevas.
No se agrega un teorema ni una tercera contribución. El autor confirmó que CAP
no apoyó este trabajo. Se reduce el abstract; DOI y publicación quedan para el final.
