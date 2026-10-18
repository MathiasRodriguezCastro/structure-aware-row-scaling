# Diagnóstico estructural de escalado en redes multicommodity

El estudio terminó: 12 modelos nativos, 84 ejecuciones piloto y 126 ejecuciones
de réplica. El manuscrito OMS v1.3.14 no se modificó.

**Resultado:** las 773 filas de acoplamiento sí se transforman y el presupuesto
1e-5 modifica sus 773 factores. En esta colección, Role-Hybrid = Coupling-only.
Sin embargo, todas las soluciones de todos los controles ya cumplen 1e-7.
La réplica confirma una reducción de trabajo frente a L2, pero no una reducción
del ciclo completo medido, ni una ventaja general frente a Base.

## Procedencia y alcance

- [CommaLAB](https://commalab.di.unipi.it/datasets/mmcf/): R01.1,...,R06.1,
  seis modelos dirigidos de cargos fijos, y seis modelos de expansión de capacidad
  Günlük, con las dos primeras demandas por orden lexicográfico de cada grupo.
- La formulación de expansión usa capacidades **bidireccionales**, dos instalaciones
  enteras de capacidad 1 y lambda compartidas por los dos sentidos. Esa interpretación
  coincide con la clasificación de Bienstock–Günlük/Günlük en
  [Atamtürk y Günlük, secciones 1 y 3](https://arxiv.org/html/1711.10147).
  No se suman los dos sentidos como si fuera capacidad no dirigida.
- [SIPLIB SSLP](https://www2.isye.gatech.edu/~sahmed/siplib/sslp/sslp.html):
  los diez modelos presentes en el ZIP se inspeccionan y excluyen del mecanismo de
  filas entre bloques de recurso. En su equivalente determinista nativo, cada fila
  toca a lo sumo un escenario más las columnas compartidas de primera etapa.

Las dos colecciones de redes tienen distinta procedencia y formulación, pero
pertenecen a una misma área de aplicación. Las parejas Günlük conservan la misma
matriz y cambian las demandas: son seis modelos sobre tres topologías, no seis
matrices independientes. Los encabezados reales del archivo, no las dimensiones
aproximadas de la página web, definen las dimensiones utilizadas.
El rango de coeficientes es 613--2640 en R y solo 4 en Günlük: allí la densidad
de las filas, no un rango extremo de coeficientes, activa el núcleo L2.

La selección se fijó localmente antes de resolver; no es un registro externo con
fecha certificada. `PROTOCOL.md`, `pilot-design.json` y `replication-design.json`
conservan las reglas y las identidades de sus entradas. La réplica utiliza la
colección R completa, sin elegir instancias individuales por sus resultados.

## Qué se comprobó

La matriz conserva todas las ecuaciones de conservación, incluidas sus dependencias.
Los bloques locales son matrices de incidencia, no identidades; por tanto **no se
aplica el teorema triangular** del artículo. El condicionamiento informado utiliza
los valores singulares positivos de la matriz rectangular completa, no una base LP.
La reducción por simetría de las mercancías se contrastó con 120 SVD completas.
Las diez pasadas de equilibración diádica son un sustituto declarado de diagnóstico;
no revelan el escalado interno propietario de Gurobi.

Las políticas son adaptadores Python con los núcleos declarados y banda de identidad
cerrada [1/2,2]. No se afirma identidad binaria con el exportador C++. Las 60
exportaciones se importaron y comprobaron por completo: coeficientes, RHS, objetivo,
nombres, cotas y dominios enteros. La multiplicación por factores reales redondea
los coeficientes exportados; el verificador mide su defecto puntual exactamente.
No se afirma exportación diádica exacta para estos factores.

El verificador de soluciones reconstruye balances, capacidades, objetivo y cotas
desde los arcos y las demandas nativos con aritmética racional. No usa los atributos
de factibilidad del solver ni su matriz exportada. Separa el punto bruto de las
variables enteras redondeadas y comprueba las hipótesis de transferencia, incluido
el defecto de exportación. Un presupuesto es una meta experimental en unidades de
flujo de la fuente, no una tolerancia operativa reconocida.

A 1e-7 hay 256 contratos uniformes incompatibles en la colección R. Eso no implica
que los modelos sean inviables o que sus soluciones violen el presupuesto: las
soluciones observadas de esos modelos lo cumplen. El límite uniforme de redondeo
es suficiente y conservador.

## Comparación y decisión

El piloto usa una semilla, límites Work=0.25 y 10 s; los modelos de expansión llegan
al límite de trabajo sin cerrar la brecha. Sus incumbentes no son óptimos certificados.
La réplica usa las seis R y semillas 227,229,233. Cada política busca el mismo costo
objetivo: 1.01 veces un costo factible exacto obtenido en el piloto. Esa referencia
**no es un óptimo certificado**. Todas las 126 entregas cumplen la meta y los
presupuestos; se reportan también las terminaciones por gap y por límite.

Razones geométricas Budget/control en 18 pares:

| Control | Trabajo | Preparación + carga + resolución |
|---|---:|---:|
| Base | 1.009 | 1.129 |
| Flat-L2 | 0.884 | 1.071 |
| Flat-L2-tight | 0.884 | 1.067 |
| Flat-L2-NF3 | 0.599 | 0.970 |

Los tiempos son cortos y descriptivos en una máquina compartida. La preparación se
midió por separado en orden mezclado, incluyendo construcción, selección y exportación;
la verificación posterior se excluye del ciclo. `process.json` conserva además el
tiempo de cada proceso nuevo. La comparación a objetivo común evita atribuir a
velocidad una diferencia en el trabajo dedicado a cerrar cotas distintas.
El ciclo medido parte de los datos nativos ya cargados; excluye arranque del
intérprete, lectura inicial de esos datos e inicialización de la licencia.

**Decisión:** conservar estos resultados fuera del manuscrito. La selección por
estructura fue pertinente y permite aislar el acoplamiento; por sí sola no genera
una recuperación de precisión ni una ventaja computacional generalizable.
Para buscar una recuperación de precisión hacen falta además dificultades numéricas
en los datos nativos. Que un contrato restrinja el factor propuesto no demuestra
que la solución sin contrato vaya a incumplir el presupuesto.

## Reproducir y verificar

Desde la raíz del repositorio, con NumPy y SciPy; los comandos siguientes
no requieren licencia comercial ni ejecutan optimización:

```bash
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-structure-screen-20261018/verify_screen.py
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-structure-screen-20261018/verify_points.py
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-structure-screen-20261018/verify_points.py --replication
python3 exploration/oms-structure-screen-20261018/analyze.py
python3 exploration/oms-structure-screen-20261018/manifest.py
```

`sources/manifest.json` documenta archivos nativos, URL, miembros y SHA-256.
`MANIFEST.json` vincula el código, los datos, los diseños, las exportaciones y los
registros. Los registros completados no se sobrescriben. Para nuevas ejecuciones,
usar otra copia de trabajo y otro diseño; `pilot.py` y `replicate.py` conservan los
intentos incompletos y requieren diagnosticarlos antes de reanudar.

`structure.csv`, `contracts.csv` y `conditioning.csv` son el diagnóstico anterior
a los resultados. `pilot-results.csv`, `replication-results.csv`, `comparisons.csv`
y `summary.json` contienen la evaluación y todos sus límites.
