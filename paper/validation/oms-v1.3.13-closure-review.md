# Estado final de OMS — 17 de octubre de 2026

El trabajo científico y técnico solicitado está cerrado en `v1.3.13-oms-submission`.
La entrega aún no fue enviada a la revista ni depositada públicamente en Zenodo.
Este registro de cierre es posterior a la congelación y no modifica sus archivos.

Seguimiento editorial: los textos del formulario y las copias de comparación se
conservan como preparación local, fuera del árbol versionado. El estado vigente
está en el [checklist de envío](../submission/oms/SUBMISSION_CHECKLIST.md) y en las
[notas de preparación](../oms/OMS_NOTES.md). Las guías secundarias se contrastaron
sin convertirlas en confirmación oficial de los requisitos particulares de OMS.

| Línea solicitada | Cierre y alcance |
|---|---|
| Aplicación independiente | Ocho horizontes de programación de lotes, con dos anclas del piloto previo. Budget-L2 y L2 cumplen 24/24; no se afirma beneficio primal adicional frente a L2. Tabla S20. |
| Mecanismo del régimen favorable | Factores y reservas comprobados de forma independiente. Se identifica la familia de activaciones y cómo cambian sus factores; no se identifica una causa interna del solver. Sección 7.9 y suplemento. |
| Tolerancia entera | Comparación emparejada completada. Conserva las 18 abstenciones y una cota contradicha con la tolerancia mayor; no demuestra robustez universal. Tabla S21. |
| Ciclo completo con C++ | 18 pares con iguales modelos, puntos y resultados del solver. Razón geométrica de tiempo C++/Python de 0,824 en el equipo utilizado. Tabla S18. |

La validación completa desde una extracción limpia aprobó los cuatro comandos
documentados, reprodujo las 37 tablas y las tres figuras, e incluyó la prueba C++
sin omisiones. El reempaquetado posterior solo corrigió en un README la cantidad de
páginas del suplemento; su validación conserva la prueba de identidad de todos los
datos, programas, pruebas y PDF respecto de la auditoría completa.
La comprobación adicional de cierre está en
[oms-v1.3.13-closure-review.json](oms-v1.3.13-closure-review.json).

Se revisaron visualmente la primera página del manuscrito, la carta y las páginas
con las tablas S18, S20 y S21, sin detectar recortes o desbordamientos. La entrega
contiene 36 páginas de manuscrito, 28 de suplemento y una de carta. El resumen
extraído tiene 191 palabras y el manuscrito declara seis palabras clave.

## Pendientes externos para el envío

1. **DOI y depósito de Zenodo**, reservados para el final por indicación del autor.
   Los archivos del depósito ya están preparados y corresponden al artefacto congelado.
   Al disponer del DOI, actualizar la disponibilidad y los metadatos y validar una nueva
   entrega; conservar esta versión intacta. El DOI histórico no identifica los datos nuevos.
2. **Portal de OMS:** comprobar categorías de archivo, estilo de referencias, límites
   de resumen, palabras clave y extensión; completar las declaraciones personales y
   el formulario de financiación. El autor ya confirmó que CAP no apoyó este trabajo.
   Las [instrucciones específicas](https://www.tandfonline.com/action/authorSubmission?journalCode=goms20&page=instructions)
   volvieron a devolver HTTP 403. No se declara conformidad con requisitos inaccesibles.
   El artefacto ocupa 383.795.912 bytes; su admisión debe comprobarse en el portal.
3. **Realizar el envío editorial** una vez completados esos pasos.

La [guía general del editor sobre suplementos](https://authorservices.taylorandfrancis.com/publishing-your-research/writing-your-paper/enhancing-your-article-with-supplementary-material/)
indica que los materiales científicos destinados a evaluación deben estar accesibles
a los revisores y distingue los datos de investigación de los suplementos. También
describe alojamiento de suplementos sin límite de tamaño; esto no confirma las
restricciones de carga del portal concreto de OMS ni sustituye el depósito de datos.

Los siete refinamientos exactos externos sin testigo y la falta de identificación
causal interna siguen declarados como límites del estudio concluido. No son pruebas
de inviabilidad ni certificados generales de optimalidad. No queda una campaña
experimental pendiente dentro del alcance acordado.

Entrega: [oms-delivery.zip](../submission/oms/releases/v1.3.13-oms-submission/oms-delivery.zip).
Prueba de validación congelada: [VALIDATION.json](../submission/oms/releases/v1.3.13-oms-submission/VALIDATION.json).
