# Ampliación confirmatoria: preparación, piloto y referencias

Se preserva `v1.5.0-orf-submission` (`2fbb5f14`) y también v1.4.2. El artículo
y su ZIP de envío no se modifican. Esta investigación está en una rama separada.

## Campaña confirmatoria enviada

Se enviaron las **3.840 asignaciones** del `CONFIRMATION_PLAN.json`: 480 bloques
de modelo/semilla, ocho ejecuciones por bloque y una sola resolución simultánea.
Los 3.816 objetivos de calidad usan las referencias comunes; las 24 ejecuciones
del modelo infactible permanecen diagnósticas. El protocolo de ejecución y
análisis está en `CONFIRMATION_EXECUTION_PROTOCOL.md`; todas sus dependencias
quedaron identificadas por hash antes del primer resultado comparativo.

El intento de admisión `6071896` se detuvo en Bash antes de Python o cualquier
solver. Se preservaron su plan, recepción, registros y cancelación de trabajos
pendientes. La enmienda de portabilidad conserva exactamente las asignaciones,
su orden, los límites y el análisis. El envío corregido consta de admisión
`6071904`, primer bloque `6071905`, array restante `6071906`, consolidación
`6071907`, análisis `6071908` y sellado `6071909`.

La admisión comprueba referencias, hashes, aritmética sobre candidatos guardados
y ambas licencias completas. El primer bloque integra las 3.840 ejecuciones;
su reproducción habilita los otros 479. No se evalúa qué política gana para
autorizar esa continuidad. Cada bloque guarda los vectores y ejecuta su propia
verificación independiente. El análisis final exige la campaña completa y
remuestrea padres enteros; no se publican comparaciones parciales de políticas.

La admisión corregida pasó. El primer bloque terminó sus ocho ejecuciones sin
fallos y habilitó el array restante. Se descargaron sus artefactos completos y
se reprodujo localmente el informe con bytes idénticos a los del clúster:
28 vectores, 22 auditorías completas y una referencia exacta comprobada.
`CONFIRMATION_INITIAL_LOCAL_REPLAY.json` conserva ese control, que no constituye
un resultado comparativo de eficiencia ni certifica toda la campaña pendiente.

`CONFIRMATION_SUBMISSION.json` contiene los recibos y dependencias Slurm.
`CONFIRMATION_PROGRESS.json` es una captura operacional fechada, no el estado en
tiempo real. Para actualizarla sin resolver ni modificar el plan:

```sh
python3 exploration/orf-confirmatory-extension-20261019/monitor_confirmation.py --copy --snapshot
```

El monitor distingue los informes verificados en el clúster y descargados de
las auditorías realmente reproducidas con los vectores en la copia local.
Para descargar y revisar localmente todos los bloques terminados disponibles:

```sh
python3 exploration/orf-confirmatory-extension-20261019/audit_completed_confirmation.py --download
```

El auditor fija primero una instantánea de los bloques completos disponibles;
descarga sus artefactos y cronómetros por el puerto 10022, reproduce los informes
sin optimizadores y exige que coincidan byte a byte. Comprueba además parámetros,
versiones, importaciones de matrices y el nodo común de cada bloque. Conserva
un manifiesto SHA-256 de los archivos usados en `setup-evidence/confirmation-local/`
y resume el último control en `CONFIRMATION_LOCAL_AUDIT.json`. Este control
adicional no modifica fuentes congeladas, políticas, límites ni resultados.

El primer control ampliado pasó en 136 ejecuciones de 17 bloques y 16 modelos
distintos: 1.330 vectores, 524 auditorías completas y 17 comprobaciones de
referencias. Cubre las tres familias y nueve combinaciones de familia/horizonte.
Los 1.309 archivos usados quedaron identificados por SHA-256 (227.843.301 bytes).
La coincidencia de informes verifica su reproducción, no implica que todos los
candidatos satisfagan los objetivos de precisión/calidad ni anticipa eficiencia.

La consolidación, el análisis y el sellado están programados al terminar el
array. Los registros voluminosos quedan fuera de Git y se conservan en el
directorio aislado del clúster. El artículo no recibe cambios automáticamente.
Las referencias a las asignaciones «sin lanzar» en los informes de preparación
describen sus cierres históricos, anteriores a esta autorización y envío.

## Continuación de recursos y referencias

El 20 de octubre se registró `PENDING_VALIDATION_PLAN.json` para completar los
pendientes del piloto cerrado. La admisión `6070373` pasó con los 160 Base
originales. La calibración `6070374` terminó nueve resoluciones Base: siete a
120 s y dos a 300 s. Propone 120 s para Full/360/CPLEX y SG-Ter-Mer/360/Gurobi,
y el techo de 300 s para Full/360/Gurobi. En este último estrato el criterio
operativo sigue incumplido (1/2 casos), con censura explícita. Los demás estratos
conservan 60 s. No se usan resultados de políticas para decidir recursos.

El array `6070375` completó los 160 modelos: 149 referencias factibles exactas,
diez casos desconocidos y el caso certificado como inviable. Usó 171 MIP Base y
171 LP racionales, separados de los nueve MIP de calibración. Los trabajos
`6070376` y `6070377` consolidaron y reprodujeron sus resultados. El verificador
independiente de biblioteca estándar (`6070447`) comprobó todas las filas,
cotas finitas escritas e integralidad, sin paquetes externos ni optimizadores.

Los identificadores y dependencias se guardan en
`PENDING_VALIDATION_SUBMISSION.json`; el protocolo y fuentes quedan congelados
por hash. Se mantienen una sola resolución simultánea, cuatro hilos y 8 GiB.

La recuperación registrada en `REFERENCE_FEASIBILITY_RECOVERY_PROTOCOL.md`
terminó en el array `6071776`: **diez referencias recuperadas con diez LP y cero
MIP nuevos**. Reutilizó los patrones guardados, con objetivo de factibilidad y
techo de costo explícito. La reproducción `6071778` pasó y se repitió localmente
con resultado idéntico. Los informes y el sellado iniciales se conservan intactos.

El [informe de referencias y recursos](INFORME_REFERENCIAS_Y_RECURSOS.md)
documenta el cierre: **159 referencias factibles verificadas, un diagnóstico
inviable y cero desconocidos**. Los registros completos se descargaron y sus
hashes se comprobaron localmente. `CONFIRMATION_PREREQUISITES_FROZEN.json`
congela límites y máscara común antes de comparar políticas: 3.816 asignaciones
con calidad evaluable y 24 diagnósticas. **En ese cierre todavía no se habían
lanzado las 3.840 asignaciones.** Las referencias no son óptimos MILP certificados
y esta etapa no demuestra una ventaja de Budget-L2.

Con los archivos completos presentes, el cierre se reproduce sin optimizadores:

```sh
python3 exploration/orf-confirmatory-extension-20261019/seal_pending_validation.py --check
python3 exploration/orf-confirmatory-extension-20261019/verify_reference_witnesses_stdlib.py
python3 exploration/orf-confirmatory-extension-20261019/verify_recovered_references_stdlib.py
python3 exploration/orf-confirmatory-extension-20261019/seal_reference_recovery.py --check
python3 exploration/orf-confirmatory-extension-20261019/summarize_pending_validation.py --freeze
```

El checkout contiene fuentes, entradas, informes y manifiestos. Los LP, vectores,
registros y testigos voluminosos permanecen fuera de Git, identificados en ambos
sellados y conservados en la copia local y el directorio aislado del clúster.
El checkout solo no constituye un archivo íntegro de resultados.

## Estado del piloto cerrado

El array corregido `6069328` completó **256/256 asignaciones**, sin fallos de
infraestructura ni resultados faltantes. La reproducción independiente pasó en
el clúster y en la copia local: 1.821 vectores, 692 auditorías completas y 31
referencias exactas. Las ocho ejecuciones del modelo Simple certificado como
inviable permanecen como diagnóstico; no son timeouts ni comparaciones de calidad.

El [informe del piloto](INFORME_PILOTO.md) explica estados, memoria, tiempos y
la propuesta de recursos. `PILOT_ASSIGNMENTS.csv` contiene las 256 asignaciones;
`PILOT_RAW_MANIFEST.json` identifica todos sus artefactos, incluidos vectores,
exports y referencias. `close_resource_pilot.py` verifica los hashes y reproduce
el cierre sin optimizadores. No se usó el piloto para elegir políticas ganadoras.

Las siete calibraciones Base a 120 s propuestas para tres estratos de 360 h
**no se lanzaron dentro del cierre**: aquel informe conserva las 256 asignaciones.
Su continuación posterior se registra por separado en la sección anterior.
Los recursos confirmatorios se fijaron en la continuación descrita arriba; el
envío posterior de las 3.840 ejecuciones está registrado al principio. El resto
conserva la historia de preparación; las frases sobre tareas pendientes del piloto corresponden a ese
estado previo, no reemplazan el informe de cierre.

## Procedencia que efectivamente se comprobó

ClusterUY contiene 100.000 y 10.000 entradas Simple, además de 500 Simple,
500 SG-Ter-Mer y 500 Full en los bancos de la tesis. El recuento y la selección
corrieron en un nodo de cómputo, no en login. Las rutas y hashes están en
`REMOTE_INVENTORY.json`; `SOURCE_AUDIT.json` contrasta las 1.500 entradas del
inventario auditable y los 48 padres elegidos con sus copias locales.

Los bancos pequeños recombinan componentes históricos; el generador del Simple
grande añade rotaciones cíclicas. No son 40 conjuntos nuevos de observaciones
operativas independientes. El estudio principal usa una población generada
definida y conocida, con procedencia compartida explícita. La selección no usa
resultados de políticas. El banco grande se reserva para sensibilidad separada.

La campaña antigua `solver-robustness-v1` también aplicó políticas de escalado
sin contratos al banco. Su tabla parcial documenta exposición para 17 de los
48 padres seleccionados (3 de piloto, 14 de confirmación); los restantes no se
declaran inéditos por faltar en esa tabla. `PRIOR_POLICY_EXPOSURE.json` registra
la procedencia sin sustituir padres. La auditoría de texto limpio no encuentra
coincidencias exactas con las 73 entradas guardadas de exploraciones anteriores.
La ampliación evalúa contratos y configuraciones fijados previamente sobre esta
población generada conocida; no constituye validación externa independiente.

Confirmación: 14 Simple, 13 SG-Ter-Mer y 13 Full. Piloto disjunto: 3, 3 y 2.
Los horizontes 24/72/168/360 dan 160 modelos de confirmación y 32 de piloto.
Se mantienen estados iniciales, valores decimales y unidades horarias. En Full
se conserva la misma función matemática de continuación Bellman: es una
sensibilidad de dimensión, no un nuevo pronóstico operativo recalibrado.

## Comprobaciones terminadas

- 62 fuentes de políticas coinciden con el commit del artículo congelado.
- Los 192 modelos conservan la integralidad original y la demanda coherente.
- Se hicieron 8.984.864 comprobaciones de productos escritos; objetivo, cotas y
  dominios enteros permanecen idénticos al escalar filas. Los errores binario64
  se registran, sin afirmar proporcionalidad exacta de los productos redondeados.
- El contrato modifica 0 factores Simple, 39.936 SG-Ter-Mer y 37.440 Full en
  el conjunto de preparación. Estos conteos no miden una ventaja del solver.
- Gurobi 13.0.2 y CPLEX 22.1.2.0 pasaron pruebas de 1.100 variables en cómputo.
  Los paquetes tienen hashes fijados; CPLEX carga una biblioteca compartida
  construida, en cómputo, desde la biblioteca estática completa ya instalada.
  No se distribuyen bibliotecas comerciales en el repositorio o archivo público.
- La prueba inicial de Gurobi resultó insuficiente para detectar una licencia
  limitada. Se canceló el primer array de referencias y sus dependientes antes
  de cualquier comparación del piloto. Los intentos se conservan íntegramente.
  Después, ambos solvers pasaron pruebas de 2.501 variables con la ruta de
  licencia explícita dentro del contenedor (trabajo 6068574). El relanzamiento
  conserva modelos, políticas, parámetros y orden y registra sus costos previos.
- Dos MIP diminutos locales verifican importación, callbacks y controles
  numéricos; se repetirán en el entorno de ejecución como puerta de despliegue.
  No son observaciones del piloto ni evidencia de rendimiento.

El primer piloto de recursos terminó incompleto: 98 workers llegaron al solver,
20 se detuvieron por diferencias de hashes antes de resolver y 138 quedaron sin
intentar. Todos se conservan en el archivo de infraestructura del trabajo
6068582. El núcleo automático de OpenBLAS producía una diferencia de un bit en
la norma y de dos ULP en un factor L2. Fijar `OPENBLAS_CORETYPE=Haswell` reproduce
64/64 exports originales, sin modificar políticas ni datos. El piloto se repite
íntegro con ese entorno fijado; no se usan sus resultados para elegir políticas.
Python también requiere `PYTHONINTMAXSTRDIGITS=0` para verificar algunos
testigos racionales largos. La recuperación de referencias usa exclusivamente
la adquisición Base y procedimientos registrados por separado.

## Secuencia de cómputo

`PILOT_PLAN.json` fija 256 asignaciones: ocho padres, cuatro horizontes, dos
solvers y cuatro políticas. Cada bloque mantiene juntas las ocho combinaciones
de un modelo, ejecutadas secuencialmente en el mismo nodo y en procesos nuevos.
Usa cuatro hilos, gap pedido 0,1%, límite piloto de 60 segundos y semilla 401.
La memoria inicial es la predeterminada por el sitio, 2 GiB/CPU; el piloto mide
RSS para decidir la reserva siguiente. La concurrencia global inicial es una.

Antes se intentan 32 referencias comunes: Base a 120 segundos y gap 0,1%,
seguida de reparación LP racional y comprobación de todas las filas/dominios.
Un resultado desconocido permanece desconocido; no se elimina ese modelo del
perfilado de recursos ni se afirma que su calidad haya pasado. El objetivo común
de calidad usa la referencia factible verificada, nunca un supuesto óptimo.

Gurobi usa L2-NF3 y CPLEX L2-NumEmphasis, identificados por separado. Las otras
tres políticas son Base, L2 y Budget-L2. Se conserva cada vector candidato,
estado, error, registro nativo, parámetros, preparación y auditoría. La medida
de disponibilidad verificada es posterior al solver, no una parada certificada
en línea. El tiempo completo del proceso incluye persistir el resultado; se
registra aparte de la preparación inicial del entorno y de la cola Slurm.

La consolidación se ejecuta automáticamente después del array. Informa recursos,
censura Base, intentos sin referencia y fallos; no elige políticas ganadoras.
Después, `replay_pilot.py` recalcula costos, decisiones de calidad, aceptación
primal y comprobaciones de referencias a partir de los vectores guardados, sin
llamar a optimizadores. Su aritmética independiente se contrastó con seis
candidatos históricos; el piloto nuevo todavía debe pasar su propia reproducción.
Las 3.840 asignaciones confirmatorias siguen sin lanzar hasta fijar sus recursos
y satisfacer sus puertas de admisión. El piloto no se usa como evidencia
confirmatoria ni se mezcla con los tres seeds de la campaña siguiente.

Los identificadores de envío efectivos se guardan en `SLURM_SUBMISSION.json`.
Todos los trabajos pesados usan sbatch. Las transferencias usan `cluster.uy`,
puerto 10022, sin compresión en login. La instalación, las pruebas y la eventual
descompresión de archivos también corren en cómputo.

`PRE_EXECUTION_AMENDMENT.json` conserva el plan inicial y registra únicamente
la incorporación del cronómetro exterior, antes de iniciar referencias o
comparaciones nuevas. Las asignaciones y su orden permanecen idénticos.
`PRIOR_EXPOSURE_AMENDMENT.json` documenta después la historia de políticas
anteriormente aplicada al banco, también antes de nuevas resoluciones. Conserva
el plan previo y no modifica padres, políticas ni asignaciones. El despliegue
inicial pasó en el trabajo 6068542; una nueva puerta revisa los hashes enmendados.
`TRANSFER_CONTENTS.sha256` identifica todos los archivos del despliegue inicial;
el trabajo de admisión comprueba sus hashes en cómputo.

El envío se reproduce con `launch_cluster.py deployment` y, después de recuperar
las comprobaciones remotas satisfactorias, `launch_cluster.py pilot`. Si hay una
enmienda, se ejecuta antes `launch_cluster.py recheck` y se recupera su informe.
El envío del piloto exige que Slurm haya terminado satisfactoriamente el primero. El controlador
guarda cada identificador inmediatamente y no duplica trabajos ya registrados.

## Reproducir la preparación sin optimizadores comerciales

Desde la raíz del repositorio:

```sh
python3 exploration/orf-confirmatory-extension-20261019/freeze.py
python3 exploration/orf-confirmatory-extension-20261019/audit_sources.py
python3 exploration/orf-confirmatory-extension-20261019/check_preparation.py
```

La última orden usa los LP regenerables presentes en `models/`. Si se parte
solo del checkout, generar antes con `prepare_models.py`, el binario Dummy del
artículo y las entradas del banco; no resuelve MIP. Los insumos originales y los
exports quedan identificados por hash. Las interfaces comerciales solo se
requieren para repetir las resoluciones y los dos tests nativos.

Documentación técnica consultada: [énfasis numérico de CPLEX](https://www.ibm.com/docs/en/icos/22.1.2?topic=difficulties-numerical-emphasis-settings).
La exploración de [datos públicos ADME](https://adme.com.uy/datosabiertos.html)
no se presenta como adquisición de los datos usados aquí. Los bancos realmente
utilizados son los identificados por el usuario y auditados en el clúster.
