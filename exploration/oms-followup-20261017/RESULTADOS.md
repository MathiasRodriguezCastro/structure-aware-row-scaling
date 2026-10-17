# Seguimiento científico para OMS — 17 de octubre de 2026

Se completaron las cuatro líneas acotadas del adjunto. Los resultados aportan
validación aplicada fuera del despacho, medición del ciclo nativo completo y
límites explícitos de robustez. No establecen superioridad universal ni hacen
inevitable una aceptación editorial. No se amplían los teoremas ni se incorpora
la extensión conjunta de filas/columnas al manuscrito.

## 1. Transferencia a producción por lotes

Fuente independiente: [STN-Scheduler](https://github.com/jckantor/STN-Scheduler),
commit 3b1d5f3adfb1165c06ca496775047d683886ab52, licencia MIT de Jeffrey Kantor.
Ocho horizontes fijados antes de resolver: 8,10,12,16,20,24,32,40. Dos son anclas
conocidas del piloto negativo; seis son instancias nuevas del mismo ejemplo externo.
No son ocho aplicaciones diferentes ni una muestra aleatoria de modelos industriales.

Tres semillas nuevas, cuatro controles, 96 llamadas: todos comparten IntFeasTol=1e-9,
presolve automático, 4 hilos, 30 s y gap nativo pedido de 1%. Los presupuestos
son objetivos numéricos declarados: masa 1e-5 kg (10 mg), lógica 1e-5 y dinero
1e-3 unidades de la fuente. Las representaciones diádicas son exactamente proporcionales.

| Método | Entregas dentro de todos los presupuestos |
|---|---:|
| L2 diádico | 24/24 |
| Budget-L2 diádico | 24/24 |
| L2-tight | 24/24 |
| L2-NF3 | 23/24 |

El resultado demuestra transferencia del procedimiento, sin recuperación primal
adicional frente al control L2. No se oculta el piloto previo sin ventaja.

En H40, semilla 149, NF3 devuelve B=1.110407442e-4 kg con W=0 para B−200 W≤0.
La violación es 111.041 mg, once veces el presupuesto de 10 mg. El factor L2=2^-8
produce un residuo exportado de 4.337529071e-7, menor que epsilon=1e-6, y los
enteros son exactos. Budget selecciona 2^-3: epsilon/alpha más reserva entera
es 8.2 mg, inferior al objetivo. Sus tres puntos de H40 cumplen. L2 también cumple;
no es un caso de superioridad única frente al control directo.

El trabajo geométrico Budget/NF3 es 0.554 y Budget/L2 es 0.960. Los solves son
cortos, el costo de proceso domina y no se deduce una aceleración general.
Las cotas son otro resultado: ocho referencias NF3 adicionales y ocho intentos
LP exactos producen un testigo y siete resultados desconocidos. Los logs de estos
últimos muestran salida sin solución certificada; no son pruebas de inviabilidad.
Solo 12 de 96 contrastes de cotas tienen ese testigo; los otros 84 quedan desconocidos.
No se buscaron patrones alternativos hasta obtener certificados favorables.

Una comprobación de construcción anterior a la primera optimización detectó
que ConstraintList depende del orden de sets de Python. Se conservó el fallo sin
llamada al optimizer y se verificó la multiconjunto completa de filas, con
multiplicidades, antes de restaurar el orden ya congelado. Se conservaron
modelos, exportaciones, asignaciones, parámetros y la enmienda del código.

## 2. Factores y transición de presupuestos

La auditoría independiente no importa el selector ni el runner. Comprueba 53.280
factores compatibles,7.200 intervalos incompatibles y 319.680 filas no activación
sin cambios. Las únicas diferencias están en las filas de activación.

Entre 30,100,300 y 1.000 m³ cambia el mismo conjunto de 8.640 factores. Por tanto,
el número de filas cambiadas no explica la transición. Si R_i es la reserva
combinada registrada, se verifica directamente en los archivos escritos:

alpha_i = ceil_binary 64(max(1e-9,epsilon/(delta_V−R_i))).

Los umbrales R_i+epsilon/1e-9 que vuelven admisible L2 están entre
1.008,779 y 1.013,068 m³. Al llegar a 3.000 m³ desaparecen las diferencias con L2.
Todos los puntos automáticos de la sensibilidad cumplen la hipótesis exportada,
incluso los que tienen cotas refutadas. Se identifica qué representación cambia,
pero no cuál operación interna de presolve, LP o búsqueda causa la diferencia.
La figura `mechanism/precision-transition.pdf` muestra la relación y todos los
resultados adversos. El rango favorable resume 30 y 100, no todos los valores intermedios.

## 3. Robustez respecto de IntFeasTol

La comparación mantiene modelos, semillas 59/71/89, presolve y demás parámetros.
Los factores se recalculan coherentemente con gamma: se prueba sensibilidad del
procedimiento completo. El control NF3 conserva el mismo LP para aislar su
cambio de parámetro. Se reutilizan 54 llamadas de la frontera y se agregan 36,
con 18 abstenciones; los 12 testigos exactos previos coinciden con las exportaciones.

| gamma | deltaV | Calls | Abstenciones | Presupuestos | B/G | Work/NF3 |
|---|---:|---:|---:|---:|---:|---:|
| 1e-9 |30|18|0|18/18|0/0|0.411|
| 1e-9 |100|18|0|18/18|0/0|0.362|
| 2^-28 |30|0|18|—|—|—|
| 2^-28 |100|18|0|18/18|1/0|0.356|

A 2^-28 la reserva entera supera 30 m³ en todos los modelos. El método debe
abstenerse; ello no implica que el MILP sea inviable. A 100 m³ mantiene precisión
y menor trabajo, pero una cota sigue contradicha. La ausencia de contradicciones
no es robusta a este cambio de tolerancia y tampoco constituye certificación global.

## 4. Ciclo C++ completo

36 procesos nuevos,18 bloques emparejados y aleatorizados, mismo binario con hook
activado/desactivado, metadata original leída dentro del proceso en ambas ramas.
No hubo otra campaña propia de solver en paralelo; la máquina es compartida y
se registró la carga. Startup, generación una vez, selección, exportación, import,
cotejos de datos, solve, verificación física y persistencia están incluidos.
Compilación y adquisición previa de testigos se declaran separadas.

Se verifican todos los datos y el orden de filas/columnas;18/18 pares tienen
idénticos puntos, endpoints y Work. La razón geométrica emparejada C++/Python
de tiempo completo es 0.8241102465:17.6% menos en este equipo. Por modelo va de
0.731 a 0.987. El speedup de preparación 3.7–6.4 no se extrapola al ciclo completo.
Es evidencia de software para el mismo método y no una reducción del trabajo del solver.

## 5. Alcance y cierre

Total nuevo:176 MILP (104 externos,36 de tolerancia,36 de ciclo) y 8 intentos LP.
Se mantienen las 18 abstenciones de tolerancia, el fallo de construcción anterior a
optimizar y los 7 refinamientos desconocidos. Ningún resultado adverso se reejecutó.
El refinamiento materializado de diagnóstico no hizo nuevas llamadas LP.

El artículo conserva dos contribuciones. Se incorpora la transferencia externa con
su control L2 positivo, el ciclo nativo y la limitación de tolerancia. La transición
por filas se describe sin reclamar identificación causal interna. No se abren
DW, cortes, predictores ni escalado conjunto. Las certificaciones Base anteriores
se mantienen; no se anuncia certificación de todos los resultados nativos.

El autor confirmó que CAP no apoyó este trabajo; se conserva la financiación.
Se reduce el abstract por precaución. La página oficial de instrucciones devolvió 403,
por lo que no se declara confirmado el límite de 200 palabras desde una fuente oficial.
DOI y depósito remoto siguen para el final por instrucción del autor.

## Reproducir sin resolver

Desde la raíz del artefacto completo OMS:

```bash
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-followup-20261017/check_mechanism.py
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-followup-20261017/check_external.py
python3 exploration/oms-followup-20261017/external_case.py
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-followup-20261017/check_dispatch.py tolerance
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-followup-20261017/check_dispatch.py cycle
python3 scripts/research/oms_followup_tables.py
```

`make research-oms-check` los incluye junto con los controles históricos; necesita
highspy==1.15.1 para leer LP, no una licencia comercial ni llamadas de optimización.
Generar modelos nuevos requiere Pyomo 6.10.1 y resolver requiere Gurobi 13.0.2;
los intentos exactos usan SoPlex 8.1.0/GMP. Las dependencias y binarios tienen hashes.
La reproducción de resultados guardados no necesita esas instalaciones de solver.
