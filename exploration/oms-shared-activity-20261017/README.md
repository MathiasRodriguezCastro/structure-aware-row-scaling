# Actividades normalizadas con contratos de precisión

Investigación separada del manuscrito OMS, iniciada el 17-10-2026. No sustituye
la versión congelada v1.3.14 ni declara prioridad de SOS1/holguras compartidas.

## Pregunta

¿Puede una selección exacta de escalas para actividades SOS extender los
contratos redondeados por filas y mejorar la entrega de soluciones verificadas
frente a normalización convencional, indicadores y tolerancias estrictas?

`THEORY.md` deriva la equivalencia y el intervalo necesario y suficiente de
radios diádicos. `centered-followup/THEORY.md` deriva el mejor centrado relativo
dentro del intervalo. Ambas son garantías condicionales de transferencia:
las hipótesis efectivas de la salida se verifican, no se deducen de parámetros.

## Campañas

- Primaria: cinco modelos, cinco representaciones coherentes de unidades,
  nueve políticas compatibles y tres semillas. 225 asignaciones, 65
  exportaciones/parámetros únicos y 195 ejecuciones válidas. 25 abstenciones de
  Budget-row. Los aliases están fijados antes de optimizar; no son réplicas.
  `PRIMARY_RESULTS.md` contiene las comparaciones en unidades originales.
- Seguimiento: cinco modelos sin sustitución, ocho políticas, presupuestos de
  activación 1e-4/1e-6/1e-8 y semillas nuevas 197/199/211. El diseño fija 360
  procesos nuevos, con selección, exportación, cotejo nativo, solve y verificación
  incluidos en el reloj exterior. No incluye el generador C++ ni FBBT común.
  Las políticas coincidentes se identifican en `IDENTICAL_VARIANTS.json`;
  son llamadas reales repetidas y no métodos independientes en esas celdas.

Las reglas de descarga, selección y evaluación están en `PROTOCOL.md`,
`EVALUATION_ADDENDUM.md`, `PRE_SOLVE_AMENDMENT.json` y el protocolo del seguimiento.
Los presupuestos son sensibilidad algebraica declarada, no tolerancias físicas
establecidas por un operador. Los modelos de aplicación desconocida conservan
esa clasificación. Las redes beasleyC3/k16x240b proceden de MIPLIB.

## Verificación sin licencia comercial

Desde la raíz del repositorio, con Python 3 y NumPy:

```bash
python3 exploration/oms-budget-reformulation-20261017/verify.py
python3 exploration/oms-shared-activity-20261017/test_activity.py
python3 exploration/oms-shared-activity-20261017/test_boundary_certificates.py
python3 exploration/oms-shared-activity-20261017/verify_scope.py
python3 exploration/oms-shared-activity-20261017/verify_certificates.py
python3 exploration/oms-shared-activity-20261017/verify.py
python3 exploration/oms-shared-activity-20261017/analyze_primary.py
python3 exploration/oms-shared-activity-20261017/centered-followup/test_method.py
python3 exploration/oms-shared-activity-20261017/centered-followup/verify_results.py
python3 exploration/oms-shared-activity-20261017/centered-followup/summarize.py
python3 exploration/oms-shared-activity-20261017/centered-followup/check_nonmonotonicity.py
python3 exploration/oms-shared-activity-20261017/check_manifest.py
```

`--partial` permite auditar un seguimiento en curso, sin declararlo completo.
La comprobación de soluciones usa racionales exactos de los valores binary64
guardados, redondea todas las variables enteras originales y revisa todas las
filas, cotas y dominios. Un presupuesto satisfecho no equivale a factibilidad
exacta ni a un certificado global de optimalidad. No se verifican aquí cotas
globales a partir de estados nativos.

## Reejecución con Gurobi

Los resultados corresponden a Gurobi 13.0.2. `study.py prepare` y
`centered-followup/campaign.py prepare` rechazan sobrescribir un piloto existente.
Para una nueva campaña usar una copia aislada del árbol con sus fuentes de
modelos, preservando este resultado y retirando **solo en la copia** los pilotos
y artefactos derivados. Preparar el diseño antes de llamar a `solve`.
`solve` reanuda llamadas sin un registro válido de terminación; el seguimiento
archiva intentos incompletos y nunca reemplaza un proceso terminado con fallo.
No borrar resultados adversos para repetirlos.

`RECOVERY-1.json` y `RECOVERY-2.json` documentan interrupciones de la primaria.
La segunda conserva un log nativo terminado cuya solución/metadatos quedaron
vacíos; se repitió esa configuración una vez para recuperar la verificación.
No se cuenta como réplica independiente. Los archivos truncados se preservan.

`inspect_presolve.py` solo inspecciona cuatro representaciones nativas de
control30. Registra cambios de coeficientes de actividades y sus cotas, sin
llamar a optimize ni afirmar una identificación causal completa.
`LITERATURE.md` enumera los antecedentes que impiden atribuir novedad a una
normalización SOS convencional.
