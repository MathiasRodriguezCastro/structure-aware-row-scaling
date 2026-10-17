# Garantías preventivas y filtrado de cortes del despacho

Continuación de **las otras dos líneas** solicitadas, separada de OMS v1.3.5,
de la prueba de realimentación ya cerrada y del código C++ de la tesis.
Leer `preventive-dispatch-note.pdf` (cuatro páginas) o `RESULTADOS.md`.

## Qué se obtuvo

1. **Envolvente preventiva computable.** Una cota por menores enteros/Hadamard
   evita enumerar todos los vértices duales y rayos. Combina protección de costo
   para patrones factibles y exclusión de patrones enteros inviables. Se verifican
   familias completas en tres sistemas pequeños y las hipótesis duales de ocho
   modelos. Sus factores suficientes son muy conservadores; no se establece
   novedad ni utilidad práctica. No se calculó la constante óptima de Hoffman.
2. **Benders temporal y comparación de filtros en datos reales.** Tres LP de
   ocho períodos, cinco políticas y tres repeticiones: 45 brazos. Todos los
   filtros necesitaron más iteraciones que agregar todos los cortes, sin reducir
   el número final de filas. La etiqueta física fue constante: no se identificó
   el beneficio de diferenciar familias. No se experimentó con el MILP completo.

Esto es un avance más allá de las dos notas anteriores, pero no resuelve aún
cómo conseguir presupuestos uniformes útiles para los modelos grandes ni un
selector que mejore el despacho. No se incorporó material a OMS.

## Archivos

- `PROTOCOL.md`, `design.json`, tres `snapshot-*`: fijados por hash antes de
  optimizaciones nuevas; protocolo, fuentes de decisión y colas de trabajos.
- `DERIVACION.md`: hipótesis, prueba, escalado racional exacto, límites y
  contraejemplo para un parámetro continuo. No afirma novedad del argumento.
- `preventive.py`, `preventive-results.*`, `complete-small-checks.json`: cota
  suficiente para los ocho modelos y familias completas de tres casos pequeños.
- `inputs/`: tres MPS/JSON reales y escalas archivadas; procedencia de fuentes.
  Los cinco modelos canónicos previos se incluyen en su ruta original al empaquetar.
- `inputs/preventive-assumptions/`, `assumptions-provenance.json`: cinco pruebas
  anteriores copiadas, sin modificar sus originales, con patrón y hashes.
- `composed-duals.json`: tres pruebas de dual común no vacío, obtenidas sumando
  duales exactos de pisos horarios y cotas finitas del costo del maestro.
  No afirman factibilidad primal de los tres LP.
- `source-audit/`, `AUDITORIA_DESPACHO.md`: implementación DW/B&P inspeccionada y
  distinción entre igualdad de relajaciones y predicciones de tiempo.
- `dispatch.py`, `preparation/`, `references/`, `runs/`: LP horarios, pisos
  exactos, nueve referencias compactas y las 45 corridas completas. Se conservan
  cada punto maestro, solución horaria, dual, corte exacto/exportado y elección.
- `exact-references/`, `exact-reference-summary.json`: tres intentos racionales
  **posteriores** al experimento, no usados para inicializar o seleccionar.
  SG y RN-base tienen certificado de óptimo LP. RN tiene estado `unknown` de
  SoPlex; no se lo interpreta como inviabilidad ni óptimo y se conserva el intento.
- `independent_check.py`: parser MPS independiente, reconstrucción de partición,
  pruebas racionales de cortes/pisos, exportación y decisiones de filtrado.
- `dispatch-summary.csv`, `independent-verification.json`: resultados derivados.
- `test_math.py`: seis tests de cobertura de familias, denominadores completos,
  cálculo disperso, corte/exportación racional, proyección y ancla de separación.
- `helpers/`: dos auxiliares copiados de la investigación anterior para los LP
  racionales. No se modifican las fuentes de las investigaciones cerradas.

## Reproducir sin resolver optimizaciones

Desde la raíz del repositorio o la extracción limpia del ZIP:

```sh
python3 exploration/oms-preventive-dispatch-20261014/preventive.py
python3 exploration/oms-preventive-dispatch-20261014/independent_check.py
python3 -m pytest -q exploration/oms-preventive-dispatch-20261014/test_math.py
python3 exploration/oms-preventive-dispatch-20261014/write_report.py
```

El cálculo de cotas requiere SymPy; el verificador, NumPy; los tests, pytest.
Los tests importan también el paquete Python de Gurobi para acceder a funciones
puras del conductor, pero **no construyen modelos ni llaman al solver**. No
requieren licencia de resolución. El empaquetador bloquea esa construcción
durante los tests. El replay independiente no importa ninguna interfaz nativa.
Versiones exactas en `environment.json`; no se usa Matplotlib en este reporte.

Para el PDF, desde la carpeta de la exploración:

```sh
pdflatex -halt-on-error -interaction=nonstopmode preventive-dispatch-note.tex
pdflatex -halt-on-error -interaction=nonstopmode preventive-dispatch-note.tex
```

El informe/CSV/JSON se regeneran idénticos con el entorno registrado. Se verifica
el texto del PDF recompilado, sus cuatro páginas y ausencia de desbordamientos;
metadatos como fecha del PDF pueden variar.

## Contabilidad y garantías

Hay 1896 LP horarios, 237 LP maestros, 24 LP para pisos compartidos, nueve LP
compactos y tres intentos racionales de referencia posteriores: 2169 llamadas
LP nativas en total. No hubo llamadas MIP. Se agregaron 810 filas entre todos
los brazos. Cada brazo conserva todos sus datos; no se descartan tratamientos.

Los tiempos de los brazos incluyen construir y resolver, la reconstrucción
racional con cache local, selección y exportación. Preparación/pisos compartidos
se cobran íntegros a cada brazo. No incluyen importar bibliotecas/crear el
entorno compartido ni la escritura final de resultados. La referencia compacta
incluye construir y resolver su modelo. Los tres intentos racionales posteriores
son validación externa y sus tiempos se informan aparte. No hubo retuning de
políticas, nuevas semillas o modelos después de observar resultados.

La geometría proyectada es una heurística numérica; no certifica validez. Esta
procede de duales racionales y soporte de caja para el redondeo de coeficientes.
El gap de parada sigue siendo numérico. Dos certificados exactos del LP no
certifican el MILP entero del despacho ni la fidelidad de la aproximación hidráulica.
RN y RN-base están relacionados; tres repeticiones del mismo LP no son modelos
independientes. El banco tiene pocos cortes y etiquetas físicas constantes.

Los presupuestos preventivos son algebraicos (referencia 1e-4 max(1,abs(RHS)),
cotas 1e-4, costo 1 unidad, margen 1/2). No son tolerancias de UTE/ADME.
En los tres LP sin enteros, no hay una familia de patrones enteros diferentes;
se incluyen para medir dimensión/conservadurismo y acotación común.

## Reejecutar solvers y paquete

Requiere instalaciones/licencias nativas. No se incluye ningún binario.
`dispatch.py prepare` crea un diseño antes de resolver; se niega a sobrescribirlo.
`dispatch.py run` valida hashes y se niega a sobrescribir resultados archivados.
No ejecutar sobre el estudio cerrado: usar una copia separada retirando únicamente
sus carpetas de resultados/preparación/referencias. Tiempos y bases pueden cambiar.
`audit_references.py` necesita SoPlex en la ruta documentada de su fuente y se
niega a sobrescribir cada intento; no es necesario para el replay.

`package_study.py` crea `preventive-dispatch-artifact.zip` y `MANIFEST.json`.
Verifica desde extracción limpia, bloquea llamadas nativas durante replay/tests,
recalcula las cotas/familias, regenera el informe y recompila el PDF. Coteja OMS
v1.3.5 y los seis paquetes anteriores. `VALIDATION.json` queda fuera del ZIP
para evitar un hash circular del propio archivo. El README raíz del ZIP es
una portada generada; no sustituye al README del repositorio.

MIT se aplica al código propio de esta investigación. Los modelos MIPLIB y las
copias de fuentes/datos de tesis conservan procedencia y condiciones originales;
no se relicencian por aparecer en el paquete. No se publica ni envía a terceros.
