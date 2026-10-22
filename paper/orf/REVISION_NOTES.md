# Cierre editorial y validación prospectiva — 19 de octubre de 2026

Versión v1.5.0-orf-submission. Se conserva sin cambios el archivo científico
OMS v1.3.17 y se añaden los ZIP identificados del seguimiento prospectivo y de la exploración
de candidatos, precisión y robustez.

## Los dos mensajes de revisión

| Observación | Acción y alcance |
|---|---|
| Suplemento voluminoso y DOI | Archivo completo conservado; depósito local con manifiesto de tamaños y SHA-256, metadatos, licencias e instrucciones. El autor tramita el borrador/DOI al final, como acordó. No se declara un DOI inexistente ni se retiran datos sin acceso persistente. |
| IA en metodología | Referencia breve explícita en el diseño computacional y declaración completa al final. La referencia ya existía en v1.4.0; se simplifica sin ocultar el alcance del uso. |
| ORCID de portada | Se retira el marcador manual del nombre; el identificador completo permanece en la portada separada y los metadatos editoriales. |
| Concisión | Se acortan introducción, contribuciones y discusión, se simplifica el resumen y se añade una figura conceptual. El resumen conserva su extensión breve. La validación prospectiva tiene ahora una tabla integrada y una explicación explícita en el cuerpo; el suplemento desarrolla los estratos y la incertidumbre. |
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

## Última revisión: límites e incertidumbre agrupada

- A/B. Se evita atribuir al contrato una mejora general de eficiencia o recuperación
  primal en esta muestra. Todas las políticas cumplen 72/72 presupuestos. Budget-L2
  reduce trabajo en 24/72 pares semilla, pero en solo 10/24 escenarios al agregar
  las tres semillas. Las razones por horizonte se publican sin inferir una regla.
- C. Se destaca en la sección principal el deterioro candidato máximo de 1,020%
  frente a Base y se define su denominador. El gap solicitado del 1% no limita
  diferencias entre candidatos de políticas distintas ni certifica sus óptimos.
- D. Una nueva tabla principal reúne cumplimiento, contradicciones, razones de
  trabajo/tiempo e intervalos con victorias por escenario. Incluye todos los casos.
- E. Análisis posterior identificado como tal: 100000 remuestras de los 24
  escenarios con las tres semillas juntas, cuatro controles, trabajo y tiempo.
  Frente a L2: trabajo 0,931 [0,702, 1,133], tiempo 0,996 [0,832, 1,119].
  No se establece una ventaja; ambos intervalos incluyen 1. Se conservan 96
  agregaciones y 32 intervalos, todos reconstruidos desde trabajo API y tiempos
  externos por un verificador independiente. No hubo nuevas llamadas al solver.

Los intervalos son marginales, descriptivos y condicionados a los seis padres
conocidos; no incorporan incertidumbre sobre otras familias ni certifican
optimalidad. Las 360 repeticiones técnicas no aumentan los 24 grupos.


## Incorporación selectiva de v1.5.0

- Sección 5.3: selector constructivo con reserva de exportación efectiva, lista
  finita, aritmética racional para certificar y abstención explícita. No se altera
  ninguna política experimental anterior ni se amplían los teoremas heredados.
- Seguimiento breve en la sección prospectiva: 54/72 objetivos primarios Budget-L2
  frente a 51/72 L2; PAR2 de disponibilidad 0,876 [0,441, 1,722]; 44 éxitos comunes
  con razón 0,980. No se establece ventaja temporal general. Los candidatos se
  verifican después del solver, sin presentar el descubrimiento como parada en línea.
- Controles CPLEX/ScaleFlag, márgenes heterogéneos y verificación del selector en
  Online Resource 1. Se conserva el contexto de pequeñas violaciones exactas de
  cotas y la sensibilidad posterior de proyección; no se anuncian nuevas ganancias.
- Online Resource 2 incorpora, sin recomprimir sus contenidos, el ZIP científico
  congelado de la exploración y su auditoría anterior. Esa nota refleja la decisión
  previa a esta incorporación; los documentos actuales identifican la selección.
- Los 630 MIP más una repetición técnica no agregan escenarios independientes.
  El total ORF desde el padre OMS es 1.351 llamadas, incluidas las 360 confirmaciones
  previas. Se reproducen los seis verificadores sin nuevas optimizaciones comerciales.


## Revisión editorial v1.5.1 (22 de octubre de 2026)

- El resumen prioriza los 24 escenarios prospectivos: razones geométricas
  emparejadas 0,422 en trabajo y 0,797 en tiempo frente a Base. Conserva el
  resultado dirigido previo (0,317), los límites frente a L2, la contradicción
  de cota y el deterioro candidato máximo de 1,02%.
- La tabla principal y la del suplemento separan presupuestos físicos de dominio
  exacto: Base 69/72 y Base-tight 66/72 en dominios; todas las políticas pasan
  72/72 presupuestos físicos. Las otras tres pasan ambos criterios en 72/72.
- Análisis descriptivo posterior: eliminar cada padre y sus cuatro escenarios
  deja 20 escenarios y 60 pares por control. Frente a Base, trabajo 0,355–0,504
  y tiempo 0,724–0,841. Frente a L2, trabajo 0,883–1,041: retirar instance001
  invierte el promedio. Se incluyen los cuatro controles sin filtrar resultados.
- La reproducción independiente reconstruye 56 cocientes desde métricas nativas
  y tiempos externos. No se añaden llamadas al optimizador ni nuevos intervalos.
- Se acorta la discusión y se centra la carta de una página en la especificación
  de precisión, la selección verificable y el software reproducible.
- Las instrucciones oficiales de ORF se verificaron nuevamente; las fuentes
  editables se suministran como archivo separado para su carga. El depósito y
  DOI permanecen diferidos por el autor. No se afirma haber enviado el trabajo.
- La campaña posterior de 3.840 ejecuciones conserva su informe independiente;
  no se incorpora selectivamente ni cambia los totales de esta entrega.


## Incorporación de la confirmación amplia, v1.6.0

- Se incorpora el resultado primario completo de las 3.840 asignaciones,
  conservando 3.816 evaluables y 24 diagnósticas. PAR2 Budget-L2/L2: Gurobi
  0,995 [0,923, 1,062] y CPLEX 1,000 [0,963, 1,030]. No se infiere equivalencia
  ni una ventaja temporal general. El tiempo completo Gurobi aumenta 7,9%.
- El resumen conserva el resultado prospectivo favorable frente a Base y añade
  el resultado nulo de la muestra más grande. No se combinan sus gaps nativos,
  semillas o muestras ni se confunden padres generados con datos independientes.
- Un párrafo y una tabla principales; cuatro tablas adicionales en el suplemento
  conservan los seis controles globales, los catorce estratos primarios y las
  ocho filas de precisión/dominio. Las 48 comparaciones completas y 80 intervalos
  permanecen disponibles como datos reproducibles, sin selección por signo.
- Se explicita el efecto del criterio de cotas exactas en CPLEX y la ausencia
  de contrastes aplicables de cotas en las representaciones escaladas.
- El archivo nuevo preserva todos los bytes sellados de la campaña final, piloto
  corregido y adquisición/recuperación de referencias, con deduplicación mediante
  enlaces duros tar. Los intentos de infraestructura excluidos conservan su
  historia y manifiestos; sus archivos crudos separados no se agregan a la muestra.
- El archivo se inició por sbatch; se canceló ese trabajo de archivo cuando la
  deduplicación local comprobada permitió usar la copia local completa y su caché.
  La compresión se ejecuta localmente con prioridad reducida. No se usa CPU
  intensiva del login ni se resuelven nuevos MIP.
- La versión anterior y sus PDFs/ZIP permanecen inmutables. El DOI y la carga
  efectiva del envío continúan diferidos hasta el cierre final autorizado.

- Las conclusiones se reescriben de forma más breve para reflejar la evidencia
  nueva; se conserva el alcance heredado y se añade su límite explícito de
  población histórica, cotas exactas y contrastes no aplicables. Los resultados
  anteriores y sus controles adversos permanecen en el cuerpo y el suplemento.
- La sección de reproducción identifica ahora v1.6.0 y documenta el archivo
  nuevo; se verifica automáticamente que esa identidad coincida con el paquete.
