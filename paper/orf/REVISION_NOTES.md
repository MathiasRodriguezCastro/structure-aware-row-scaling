# Cierre editorial y validación prospectiva — 19 de octubre de 2026

Versión v1.4.1-orf-submission. Se conserva sin cambios el archivo científico
OMS v1.3.17 y se añade un ZIP identificado para el seguimiento prospectivo.

## Los dos mensajes de revisión

| Observación | Acción y alcance |
|---|---|
| Suplemento voluminoso y DOI | Archivo completo conservado; depósito local con manifiesto de tamaños y SHA-256, metadatos, licencias e instrucciones. El autor tramita el borrador/DOI al final, como acordó. No se declara un DOI inexistente ni se retiran datos sin acceso persistente. |
| IA en metodología | Referencia breve explícita en el diseño computacional y declaración completa al final. La referencia ya existía en v1.4.0; se simplifica sin ocultar el alcance del uso. |
| ORCID de portada | Se retira el marcador manual del nombre; el identificador completo permanece en la portada separada y los metadatos editoriales. |
| Concisión | Se acortan introducción, contribuciones y discusión, se simplifica el resumen y se añade una figura conceptual. El resumen tiene 209 palabras. Los nuevos resultados se presentan brevemente en el cuerpo y se desarrollan en el suplemento. |
| Nuevas instancias | Política y protocolo fijados antes de 360 MIP principales sobre 24 escenarios nuevos, tres horizontes y tres semillas. Una enmienda posterior repite las 360 asignaciones para activar las trazas nativas, silenciadas por error inicialmente; ambas campañas se conservan. Son perturbaciones de seis padres conocidos: no se presentan como una aplicación independiente ni como datos operativos reservados. |
| Budget-L2 frente a L2 | Mismo núcleo y límites; solo cambia el contrato. Se comprueban 8.448 factores modificados y todos los residuos. La ventaja temporal incremental sobre L2 no se confirma y se declara. |
| Calidad y cotas independientes | 96 intentos LP; 72 testigos enteros de las representaciones resueltas y 17 cotas LP globales verificadas. Doce referencias Base quedan certificadas al 1%; siete intentos globales son desconocidos y no se ocultan. Ningún nuevo óptimo MILP exacto se demuestra. |
| Contradicciones | La nueva muestra detecta 7 cotas L2 refutadas y 1 Budget-L2, aunque todos cumplen los presupuestos. NF3 no presenta contradicciones. Se conservan resultados brutos, análisis filtrado e indicador PAR10 descriptivo. |
| Segunda aplicación | Batch scheduling y los estudios separados de redes/MIP nativos ya aportan resultados con factores activos, pero no prueban una ventaja conjunta frente a todos los controles fuertes. No se anuncian como la generalización que aún falta. |
| Exportación finita | Se añade al suplemento la cota suficiente con errores reales de coeficientes/RHS y reserva entera, explicando las cotas finitas requeridas y su dependencia del factor. Se comprueba racionalmente en 20.000 casos; no se retoca el algoritmo congelado ni se presenta como un gran teorema nuevo. |
| Entradas defectuosas | La lectura principal distingue los escenarios históricos con demanda invertida de los seis correctos y de los 24 nuevos. Se conserva la evidencia histórica con su limitación operativa; no se reescriben datos antiguos. |
| Financiación | Se conserva la declaración vigente: el autor confirmó que CAP no apoyó este trabajo. Los recursos históricos de ClusterUY siguen reconocidos. |

## Evidencia y comprobación

[Informe completo del seguimiento](../../exploration/orf-confirmatory-20261018/RESULTADOS.md).
Los verificadores leen datos guardados y usan aritmética racional; no requieren
Gurobi ni SoPlex. El paquete final incluye el archivo heredado y el seguimiento,
sin depender del repositorio mutable para obtener los insumos científicos.

La evidencia nueva amplía el diagnóstico dentro de la familia, pero conserva
una limitación científica real: no demuestra una ventaja general sobre L2 ni
certifica todos los gaps. Las cotas racionales y los testigos son referencias
reparadas, no certificados de cada candidato flotante entregado por el solver.

Pendientes externos: DOI/deposición persistente y carga efectiva en el portal.
No se ha publicado ni enviado el manuscrito mediante estos scripts.
