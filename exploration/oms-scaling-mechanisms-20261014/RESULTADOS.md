# Escalamiento interno y valor del generador: resultados

**Decisión: conservar este trabajo como exploración independiente; no modificar
OMS v1.3.5.** Hay beneficios del escalamiento externo en algunos casos con
parámetros normales, pero no una ventaja atribuible a presupuestos físicos o
roles en este banco, ni una regla predictiva validada. No se incorpora otra tabla
al artículo por una evidencia que aún no cumple ese objetivo.

## Alcance y calidad del experimento

Seis SG-Ter-Mer reales de 360 períodos, 6120 variables,
10080 filas y 1440 enteras cada uno. Se mantienen
las variables enteras del generador. Descubrimiento retrospectivo: 001, 014,
042; reserva fijada antes de optimizar: 002, 003, 004. No son una muestra
aleatoria ni seis familias independientes. No se usan para este ensayo los tres
MPS continuos de la exploración Benders. El diagnóstico LP–DW permanece pendiente.

126 brazos planificados, **108 llamadas MILP reales**
tras deduplicar matrices idénticas; 42 relajaciones LP y
42 diagnósticos presolve separados. Un intento LP racional
posterior se informa aparte. No se ejecutaron resoluciones en paralelo.
Gurobi 13.0.2, cuatro hilos, tres semillas nuevas (307,331,353), 12 s / 12 unidades
de trabajo, gap 0.1 %, tolerancias 1e-6/1e-5, sin starts. Los límites pueden
rebasarse ligeramente por granularidad del solver. La preparación, diagnóstico
y verificación están fuera del tiempo del optimizador, con costos registrados.

Los MPS se exportaron desde el ejecutable C++ existente y se importaron una sola
vez como datos canónicos binary64. Los resultados no replican los LP antiguos
DummyLp: hubo otro exportador y otro orden de construcción, además de gap,
semillas y factor dyádico diferentes. No se atribuye una diferencia respecto
del experimento anterior exclusivamente a una de esas decisiones.

## 1. La información adicional no cambia decisiones en este banco

Algebraic propone GM en todas las filas. Structural usa el mismo selector y L2
en acoplamientos. Generator proyecta Structural sobre los intervalos físicos.
La banda identidad y la selección dyádica hacen **Algebraic = Structural** en
las 60,480 filas preparadas. En los acoplamientos ambos candidatos
quedan en la banda identidad; el resto usa GM. Generator también coincide para
los tres presupuestos autorizados. Ruiz es un control distinto de cuatro
medias iteraciones, sin escalar columnas.

| Escenario | MW / m³ | Admisibles | Modificados | Incompatibles | Máx. residuo / presupuesto |
|---|---:|---:|---:|---:|---:|
| Exigente | 0.01 / 100 | 100 % | 0 | 0 | 9.699e-05 |
| Referencia | 0.1 / 1000 | 100 % | 0 | 0 | 9.699e-06 |
| Permisivo | 1.0 / 10000 | 100 % | 0 | 0 | 9.699e-07 |

Admisibilidad y modificación se calculan para Structural/Generator en las filas
físicas reconocidas; el máximo observado abarca **todos los puntos finales y
políticas** del estudio, evaluados racionalmente. Cada escenario cubre
17,280
filas físicas en seis modelos; el denominador no incluye otras restricciones.
Se convierten MW/m³ a unidades algebraicas por los coeficientes del generador.
Son objetivos de precisión del estudio, no tolerancias de UTE.

La garantía es condicional: residuo exportado <=1e-6 implica residuo original
<=1e-6/alpha. Esa cota no es el residuo observado; este se verifica por separado.
La coincidencia permite deduplicar MILP, pero **impide identificar una ventaja
operacional de la información física**. Tampoco demuestra que nunca aporte.

## 2. El escalamiento externo sí puede afectar condiciones normales

| Caso | Etapa | Base: termina / trabajo | GM: termina / trabajo | Ruiz: termina / trabajo |
|---|---|---:|---:|---:|
| instance001 | discovery | 0/3; 12 | 3/3; 7.805 | 0/3; 12.01 |
| instance014 | discovery | 3/3; 0.453 | 3/3; 0.3963 | 3/3; 0.4278 |
| instance042 | discovery | 3/3; 0.3291 | 3/3; 0.4943 | 3/3; 0.3913 |
| instance002 | holdout | 0/3; 12.04 | 0/3; 12.13 | 0/3; 12 |
| instance003 | holdout | 0/3; 12 | 2/3; 4.931 | 0/3; 12 |
| instance004 | holdout | 3/3; 0.2682 | 3/3; 0.3541 | 3/3; 0.2581 |

Cada celda: corridas que declaran OPTIMAL al gap solicitado / mediana de trabajo
de las tres corridas, incluidas las censuradas. GM significa Algebraic=Structural.
No es una tabla de aceleraciones: alcanzar un límite con peor incumbente/cota
no equivale a resolver más rápido. Estado OPTIMAL es la declaración numérica
del solver, sujeta a comprobación. Todos los estados, cotas, objetivos, gaps,
tiempos y puntos están archivados en runs y runs-summary.csv.

| Caso | Pares comparables | Mediana GM/Base de trabajo |
|---|---:|---:|
| instance001 | 0/3 | -- |
| instance014 | 3/3 | 0.8703 |
| instance042 | 3/3 | 1.538 |
| instance002 | 0/3 | -- |
| instance003 | 0/3 | -- |
| instance004 | 0/3 | -- |

Se exige que ambos terminen y sus objetivos difieran <=1e-6 max(1,|U1|,|U2|).
No se inventa una razón de aceleración para pares censurados o de calidad distinta.
Con un presupuesto de 12 unidades esto solo es una comparación acotada, no una
afirmación asintótica ni de tiempos a optimalidad exacta.

## 3. Presolve e interacciones

La huella exacta de filas normalizadas, dominios y objetivo coincide entre
Base y GM después del diagnóstico de presolve en **6/6** casos con
parámetros normales. Las magnitudes sí cambian y el trabajo puede cambiar.
Por tanto, conservar la misma geometría normalizada no basta para anticipar
el esfuerzo; reducir rangos tampoco garantiza una ventaja. La relajación LP
normal es numéricamente la misma entre esas formulaciones.

| Caso | Interno | Presolve | Base: termina / trabajo | GM: termina / trabajo |
|---|---|---|---:|---:|
| instance001 | auto | auto | 0/3; 12 | 3/3; 7.805 |
| instance001 | auto | off | 0/3; 12 | 2/3; 6.954 |
| instance001 | off | auto | 1/3; 11.56 | 2/3; 11.19 |
| instance001 | off | off | 3/3; 2.237 | 0/3; 12.07 |
| instance014 | auto | auto | 3/3; 0.453 | 3/3; 0.3963 |
| instance014 | auto | off | 3/3; 0.3539 | 3/3; 0.2236 |
| instance014 | off | auto | 1/3; 12 | 3/3; 0.9157 |
| instance014 | off | off | 2/3; 7.38 | 3/3; 0.4709 |
| instance042 | auto | auto | 3/3; 0.3291 | 3/3; 0.4943 |
| instance042 | auto | off | 3/3; 0.1575 | 3/3; 0.393 |
| instance042 | off | auto | 0/3; 12 | 3/3; 0.9463 |
| instance042 | off | off | 0/3; 12.01 | 3/3; 0.227 |

Las desactivaciones son intervenciones diagnósticas, no configuraciones
operativas recomendadas. Las declaraciones de completamiento con ScaleFlag=0
deben leerse junto con las verificaciones y la siguiente comprobación.

Una comprobación posterior con SoPlex produjo un punto **racionalmente factible** del MILP canónico 001, de costo 0. El verificador independiente comprueba todas sus filas, cotas e integridad sin tolerancias. Ese testigo refuta 4 cotas inferiores reportadas en el factorial (todas con ScaleFlag=0); 4 de esas corridas tenían estado OPTIMAL. No prueba el óptimo del MILP. El costo del testigo no es una referencia óptima.

No se localizaron ni atribuyeron internamente cortes, pivotes o factores de
escalado responsables. La API Model.presolve puede devolver un modelo distinto
del usado por optimize; no expone la matriz realmente escalada internamente.
Véanse [Gurobi: Model.presolve](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.presolve)
y [ScaleFlag](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:ScaleFlag).
Para la comprobación posterior se usó el [modo racional de SoPlex](https://soplex.zib.de/doc/html/EXACT.php),
con parsing exacto de decimales que representan los datos binary64 originales.

## 4. Qué se concluye y qué sigue pendiente

Se completaron las dos preguntas priorizadas: interacción con mecanismos
internos y atribución de valor a información del generador. Se fijaron
discovery-conclusions.json y hashes de descubrimiento antes de optimizar reserva.
No surgió una regla predictiva defendible con tres casos y no se entrenó ni
reajustó una regla con los reservados. La igualdad de factores es un resultado
determinista de identificabilidad, no un predictor nuevo de rendimiento.

El ensayo confirma que el escalamiento algebraico externo puede aportar aun
con parámetros normales, y que desactivar el interno puede dar resultados
numéricos engañosos en estas formulaciones. No demuestra una ventaja nueva
generator-aware, un mecanismo interno específico, generalización a otros
solvers ni una contribución predictiva. Las mejoras no se atribuyen a fortalecer
la relajación matemática. No justifica ampliar el artículo todavía.

Pendientes separados: diagnóstico compacto LP–DW del MILP original; eventual
frontera precisión–trabajo frente a controles fuertes; límites conjuntos del
escalamiento. No se declaran investigados por este experimento. La selección
por error de exportación tampoco se reabre: los productos ya son exactos aquí.

## Reproducción

README.md contiene comandos de replay sin solver y de nuevas corridas con
licencia. independent-verification.json comprueba importaciones MPS, factores,
presupuestos y residuos racionales. El paquete incluye modelos, puntos, logs,
protocolo, conclusiones fijadas, scripts y manifiesto. Los siete paquetes
anteriores y la entrega OMS se comprueban por SHA256, sin modificarlos.
