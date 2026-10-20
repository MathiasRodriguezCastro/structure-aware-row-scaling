# Cierre del piloto de recursos ORF

Investigación separada de `v1.5.0-orf-submission`. Se completó exclusivamente
el piloto registrado: **256/256 asignaciones, cero fallos de infraestructura
y cero asignaciones faltantes**. El artículo, el generador original y las
instancias registradas permanecen intactos. No se seleccionaron políticas
ganadoras ni se lanzaron las 3.840 asignaciones confirmatorias.

## Qué se completó

Los mismos ocho padres, 32 modelos, dos solvers y cuatro políticas se repitieron
íntegramente con semilla 401 y cuatro hilos. El array `6069328` terminó sus
32 bloques con código 0; consolidación `6069330`, reproducción independiente
`6069331` y evaluación Base `6069367` terminaron correctamente.

| Clasificación de las 256 asignaciones | Cantidad |
| --- | ---: |
| Terminación nativa por el criterio de gap solicitado | 232 |
| Límite de tiempo nativo, con incumbente guardado | 16 |
| Modelo certificado inviable, conservado como diagnóstico | 8 |
| Fallo de infraestructura o asignación faltante | 0 |

La terminación por gap es una declaración del optimizador, no una prueba
independiente de optimalidad. El estado `completed` del ejecutor significa que
el proceso y su persistencia terminaron correctamente; no implica éxito primal
ni optimalidad. Los estados numéricos originales se conservan por asignación.

`simple-v1_simple_000127-h168` permanece con sus ocho combinaciones. Su
inviabilidad está probada exactamente; su calidad primal es **no aplicable**.
No cuenta como timeout y no se propone aumentar su límite. La salida original
del colector conserva la etiqueta histórica de referencia desconocida; este
informe la interpreta junto al certificado, sin sobrescribir aquella evidencia.
Los otros 31 modelos disponen de referencias factibles verificadas, sin afirmar
que sean óptimos MILP certificados. Esto no completa las referencias de los
160 modelos previstos para confirmación.

## Reproducibilidad y verificaciones

- `OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`
  y `PYTHONINTMAXSTRDIGITS=0`; los solvers conservan sus cuatro hilos registrados.
- Los 64 exports escalados del piloto coinciden byte por byte con los fijados.
  La puerta ampliada verificó 192 Base y reprodujo 384 exports escalados.
  Cada worker volvió a comprobar sus fuentes, Base, representación e importación.
- La reproducción independiente verificó 1,821 vectores guardados,
  692 auditorías completas de candidatos elegibles o finales y
  31 referencias exactas, sin resolver otro problema.
- Los 24 pares L2/Budget-L2 de la familia Simple tienen exports idénticos.
  Son controles de estabilidad; no prueban un beneficio del contrato.
- El inventario `PILOT_RAW_MANIFEST.json` identifica 2,962 archivos y
  582,346,740 bytes. Se verifica íntegramente contra la copia local.
  Los intentos anteriores siguen conservados en `infrastructure-attempts/`:
  no se sustituyeron por estos resultados ni se mezclaron en el piloto válido.

## Recursos medidos y propuesta

El máximo RSS informado por un worker fue **690,528 KiB
(0.659 GiB)**. Slurm muestrea memoria y registró un máximo
de 613,700 KiB; se conservan ambas medidas.
No representan una garantía de memoria para todos los modelos confirmatorios.
El proceso completo más largo duró 76.59 s,
incluida preparación, resolución, verificación y persistencia. La mediana fue
4.70 s. El bloque más largo duró
581 s. Estos tiempos excluyen cola, instalación
del entorno y adquisición separada de referencias. Se registraron los nodos
node09.datos.cluster.uy, node28.datos.cluster.uy; los inventarios del scheduler se adjuntan.

Propongo conservar **4 hilos, 8 GiB por trabajo, una resolución simultánea y
45 minutos de pared por bloque**. Son los recursos efectivamente ensayados;
no se infiere capacidad adicional de licencias ni concurrencia a partir del RSS.

Para decidir límites de resolución se usó exclusivamente Base. Entre los 62
casos Base con referencia factible, 58 llegaron al criterio nativo de gap y
cuatro alcanzaron 60 s. Tras separar el diagnóstico inviable, solo tres estratos
quedan por debajo del 80% operativo registrado:

| Familia | Horizonte | Solver | Base con parada nativa por gap / modelos factibles |
| --- | ---: | --- | ---: |
| completo | 360 | cplex | 1/2 |
| completo | 360 | gurobi | 0/2 |
| sgtm | 360 | gurobi | 2/3 |

El siguiente candidato es **120 s**, mediante siete calibraciones exclusivamente
Base que cubran todos los casos factibles de esos estratos, también los que
terminaron a 60 s. Es una propuesta, **todavía no una calibración validada ni un
límite confirmatorio congelado**. No se lanzan esas siete resoluciones dentro
del cierre de las 256 asignaciones solicitadas. Los restantes estratos cumplen
el criterio a 60 s dentro de este piloto pequeño; eso no garantiza ausencia de
timeouts en la confirmación. Cualquier comparación futura usará el mismo límite
para todas las políticas de un estrato.

El colector original devuelve `confirmation_may_be_frozen=false`, y se conserva
ese resultado. Completar el piloto no equivale a habilitar la confirmación:
faltan validar los límites superiores y adquirir/clasificar las referencias
comunes de los modelos confirmatorios. Los padres y horizontes no se sustituyen.

## Cómo reproducir este cierre

Desde la raíz del repositorio, con los artefactos inventariados presentes:

```sh
PYTHONINTMAXSTRDIGITS=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 exploration/orf-confirmatory-extension-20261019/replay_pilot.py
python3 exploration/orf-confirmatory-extension-20261019/close_resource_pilot.py
```

La primera orden usa NumPy y los lectores científicos del repositorio; no llama
a optimizadores. La segunda usa solo la biblioteca estándar, verifica todos
los hashes, identidades y estados y genera `PILOT_CLOSURE.json`, la tabla de
256 asignaciones `PILOT_ASSIGNMENTS.csv` y este informe. No regenera ni
sobrescribe el inventario remoto al verificar la transferencia.

El archivo original del repositorio y este informe por sí solos no sustituyen
los vectores/exports identificados en el inventario. Esos archivos están
preservados en la copia local y en la copia aislada del clúster; los materiales
comerciales y las credenciales no forman parte de los archivos de distribución.

El piloto responde una pregunta de recursos y reproducibilidad. No estima una
ventaja de Budget-L2, no añade resultados al manuscrito y no habilita una
afirmación de validación externa sobre nuevos datos operativos independientes.
