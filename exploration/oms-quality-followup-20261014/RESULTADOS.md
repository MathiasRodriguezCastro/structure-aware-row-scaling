# Calidad, warm starts y cotas: seguimiento y ablación

**Hay una señal concreta para los contratos, de alcance limitado.** En un modelo
MIPLIB auténtico, Budget-L2 evita resultados L2 de mala calidad y certificaciones
contradichas bajo presolve automático e IntegralityFocus. La ablación separa el
efecto de la representación final del punto inicial. Eso no demuestra ventaja
general frente a Base/IntegralityFocus ni justifica otra contribución en OMS.
Todo permanece en este documento independiente; v1.3.5 no se modifica.

## Seguimiento principal: calidad tras reparar

Se congelaron 48 asignaciones antes de nuevas llamadas MILP: los tres MIPLIB
seleccionados previamente, semillas nuevas 31/47 y ocho tratamientos. Todos
conservan objetivo, dominios y presupuestos. Las dos fases warm tienen límites
1+14 s; los controles en frío, 15 s. Ciclo completo de referencia 20 s, cuatro
hilos, Gurobi 13.0.2, gap 1 %, presolve/escalado internos automáticos salvo el
control presolve-off. Factores L2/Budget diádicos existentes, sin ajuste posterior.

Presupuestos MIPLIB: delta_r=1e-4 max(1,|RHS|), cotas 1e-4 y dominios enteros
exactos. Son objetivos numéricos algebraicos del estudio. Los contratos seleccionan
para el punto crudo; no garantizan uniformemente el redondeo entero. Cada salida
se comprueba en todas las filas, cotas y dominios originales.

| Tratamiento | Entregas | Suma de ciclos, s | Cotas vetadas online | Cotas contradichas en pool |
|---|---:|---:|---:|---:|
| Cold-tight | 6/6 | 71.189 | 1 | 1 |
| Cold-IF1 | 6/6 | 77.904 | 0 | 0 |
| Base-warm-tight | 6/6 | 59.077 | 2 | 2 |
| Base-warm-IF1 | 6/6 | 75.586 | 0 | 0 |
| L2-warm-IF1 | 6/6 | 53.720 | 0 | 1 |
| Budget-warm-IF1 | 4/6 | 63.252 | 0 | 0 |
| Cold-tight-presolve-off | 6/6 | 52.181 | 2 | 2 |
| Witness-warm-tight | 6/6 | 75.652 | 0 | 1 |

Hubo 68 llamadas MILP, 46
entregas y dos abstenciones por los 96 intervalos incompatibles de cinca. Se
proporcionaron 28 Starts y los logs registran la carga
de 27; proporcionar un punto no implica que el
backend lo utilice. No hubo errores ni excesos de la referencia global de 20 s.
Se guardan las etapas y la preparación compartida, esta vez cronometrada.

Los tiempos incluyen exportación, importación/cotejo, MILP, reparación,
verificación y auditoría exacta. La persistencia final del seguimiento se mide
aparte; en la ablación guardar el NPZ final está dentro del total y no se mide
por separado. Se declara esa diferencia de registro; los archivos auxiliares
se incluyen en su etapa. Witness-warm usa información previa: adquirir
sus certificados queda fuera del ciclo y está declarado. Es diagnóstico, no
una mejora de velocidad atribuible al método. No se infiere velocidad general
de sumas sobre modelos con distinta calidad de objetivo.

### ¿Se recupera también calidad?

En control, Base-warm-tight entrega 1,374590/1,400469 y Base-warm-IF1
1,313721/1,313715, recuperando gran parte de la calidad perdida por el LP solo
(antes 26,248128). Pero Cold-IF1 entrega 1,265274/1,313755 y Cold-tight
1,322940/1,433450. El calentamiento no supera sistemáticamente el control robusto.

Las comparaciones siguientes son por modelo y semilla: umbral descriptivo de
1 % del objetivo frío, además de una guarda numérica. No es una prueba estadística
ni un gap certificado. Cada fila tiene seis pares; Budget incluye dos abstenciones.

| Warm contra su control frío | Mejora >1 % | Empeora >1 % | Sin ambas entregas |
|---|---:|---:|---:|
| Base-warm-tight | 1 | 2 | 0 |
| Base-warm-IF1 | 0 | 3 | 0 |
| L2-warm-IF1 | 1 | 3 | 0 |
| Budget-warm-IF1 | 0 | 3 | 2 |
| Witness-warm-tight | 2 | 1 | 0 |

En particular Base-warm-IF1 no tiene mejoras superiores a 1 % y empeora en tres
pares. La reparación sí puede servir como inicio, pero este experimento rechaza
la afirmación de una ventaja general de calidad/velocidad del ciclo warm.

## Cotas, gap y consistencia del informe

Tres testigos exactos disponibles **antes** del seguimiento permitieron vetar
5 cotas durante las fases. La auditoría con
el mejor testigo obtenido más tarde contradice 7
cotas y 8 declaraciones de terminación al 1 %.
Estas cuentas se solapan; no se suman como fallos únicos. No encontrar
contradicción deja la optimalidad no verificada.

La revisión posterior utiliza un testigo exacto de control con costo mostrado
1,265277 y uno de ta1-UUM de 7.547.811,68. El checker verifica los vectores
completos y los MPS originales: coeficientes, RHS, sentidos, costos, cotas y
dominios coinciden bajo la interpretación binary64. No se comparan modelos
distintos ni se usan puntos solo factibles dentro de tolerancias como testigos.

En ta1-UUM, tanto Base-warm-tight como presolve-off tienen cotas contradichas
en ambas semillas; Cold-tight falla en 47. Witness-warm-tight/47 solo se detecta
con el testigo mejor obtenido después. Un testigo previo demasiado caro puede
no detectar un informe inválido. Desactivar presolve no elimina todos los casos;
no se atribuye una causa interna específica del solver.

Hay además un informe internamente incompatible con el gap solicitado:
control/L2-warm-IF1/47 conserva etiqueta OPTIMAL con objetivo 5,643361 y cota
−24,177882. El log muestra gap **528,4306 %**, frente al 1 % pedido. El veto
de consistencia no necesita un testigo externo. La condición usa
|C−B| > max(0,01|C|,1e-10) + guarda; respeta el gap absoluto y no confunde
TIME_LIMIT con terminación al objetivo de gap. Ese caso también es contradicho
por un testigo factible mejor, pero su cota negativa no queda refutada por él.

## Ablación: representación final frente al punto inicial

Este caso de control motivó una selección posterior explícita: un estudio de
mecanismo en ese modelo, **no** validación independiente de generalización.
Antes de esas llamadas se congelaron 14 asignaciones con semillas nuevas 59/71:
tres controles fríos y el cruce 2×2 entre origen y destino L2/Budget. Se conservaron
todos los resultados. Presolve automático e IntegralityFocus en la fase final,
misma suma máxima de tiempo MILP, mismos factores y ningún M artificial.

| Tratamiento | Costo 59 | Costo 71 | Ciclo 59/71, s | Fuente final verifica |
|---|---:|---:|---:|---:|
| Cold-Base-IF1 | 1.315834 | 1.391930 | 15.352/15.323 | 2/2 |
| Cold-L2-IF1 | 2.815707 | 33.373658 | 0.301/0.336 | 2/2 |
| Cold-Budget-IF1 | 1.313510 | 1.265136 | 15.330/15.301 | 2/2 |
| Warm-L2-to-L2 | 2.815707 | 6.238235 | 0.625/0.540 | 2/2 |
| Warm-L2-to-Budget | 1.313510 | 1.315735 | 14.528/14.496 | 2/2 |
| Warm-Budget-to-L2 | 3.068627 | 7.875892 | 0.643/0.674 | 2/2 |
| Warm-Budget-to-Budget | 1.313506 | 1.265132 | 14.675/14.539 | 2/2 |

Todas las entregas finales verifican, gracias al filtro y las reparaciones.
Los seis tratamientos cuya representación final es L2 declaran terminación
óptima, pero sus informes al 1 % son contradichos por testigos exactos. Cuatro
tienen además una cota inferior imposible; los otros dos exhiben un gap interno
incompatible. Los seis con destino Budget alcanzan el límite y no declaran
óptimo; entregan objetivos aproximadamente 1,265–1,316. No se certifica su óptimo.

Usar un inicio procedente de Budget no rescata L2: Budget→L2 entrega
3,068627/7,875892. Cambiar el destino L2→Budget sí evita esos resultados y entrega
1,313510/1,315735. Esto identifica un efecto de la representación final dentro
de la configuración probada; no revela qué operación interna del solver lo causa.
El checker cotejó los cuatro pares de Starts: tienen exactamente los mismos
valores binary64, parámetros y exportación de la primera fase para cada origen
y semilla, cambiando solamente el destino indicado.

En frío, Budget entrega 1,313510/1,265136 frente a L2 2,815707/33,373658.
Base/IF1 entrega 1,315834/1,391930: su calidad es cercana y sus cotas no están
contradichas. El precio de evitar el falso cierre rápido L2 es usar casi todo el
presupuesto, aproximadamente 15 s frente a menos de 1 s. Es una recuperación
de calidad/fiabilidad, no aceleración. La comparación usa un modelo seleccionado
tras observar el problema; cuatro semillas acumuladas no prueban generalidad.

## Propiedades del controlador y límites

Cada candidato entra en S solo si verifica V_delta en las restricciones originales.
Las etapas no borran candidatos y la salida minimiza el costo original en S.
Por inclusión S_k⊆S_(k+1), el costo retenido no puede empeorar con otra etapa.
Si S queda vacío, se abstiene. El checker comprueba aceptación y retención en
todos los registros. Esto no garantiza mejora estricta o superar otro tratamiento.

Un testigo racional factible q proporciona U=cᵀq. Cualquier cota inferior válida
satisface B≤z*≤U; B>U contradice esa cota. Se exige el mismo modelo y factibilidad
exacta en todas las filas, cotas y dominios, con guarda max(1e-6,8 ulp(B)). La
conversión a float se verifica aparte. La ausencia de contradicción no certifica
optimalidad. El estado se mantiene **no verificado** y ningún gap se transfiere
gratuitamente después de reparar un punto.

Se añade un filtro de consistencia del informe con el gap solicitado, aplicado
posteriormente y declarado como tal. No altera el diseño experimental ya congelado
ni se presenta su veto como una nueva resolución o certificado dual. Los nueve
tests cubren retención, dominios, importación, modelo incorrecto, testigo racional
sin entrega flotante, gap relativo/absoluto y ausencia de inferencias de optimalidad.

## Decisión para el paper

Hay un resultado tangible más fuerte que modificar factores: en una instancia
auténtica y con controles normales, la proyección contractual evita resultados
de L2 de mala calidad y certificaciones inconsistentes; el cruce confirma el
papel de la representación final. Puede apoyar una discusión futura sobre el
uso verificable de representaciones exportadas.

Todavía no alcanza el umbral para una contribución general adicional: solo un
modelo muestra ese mecanismo; en los otros el contrato no gana frente a controles
fuertes o se abstiene; Base/IF1 ya proporciona resultados competitivos. La fase
warm no aporta ventaja general. Se mantiene OMS v1.3.5 sin cambios y se deja una
redacción candidata acotada en INCORPORACION_CANDIDATA.md, sin afirmar que los
contratos certifiquen cotas, óptimos o superioridad universal.

## Evidencia y reproducción

En total hay 62 asignaciones nuevas, 90 llamadas MILP, 60 entregas verificadas y
dos abstenciones contractuales. Los checkers independientes comprueban todos los
puntos, la retención, los testigos y las fuentes, sin importar runners/controladores
ni llamar solvers. Los 61
registros de nuevos testigos pueden repetir el mismo punto; no se anuncian como
soluciones únicas. Los diseños, fuentes, log, datos adversos y presupuestos quedan
conservados. Certificados del modelo canónico binary64, no de decimales racionales
ideales del MPS ni de estándares operativos.

```bash
python3 exploration/oms-quality-followup-20261014/independent_check.py
python3 exploration/oms-quality-followup-20261014/check_ablation.py
python3 -m pytest -q exploration/oms-quality-followup-20261014/test_controller.py exploration/oms-quality-followup-20261014/test_report_gate.py
python3 exploration/oms-quality-followup-20261014/write_report.py
```

Warm starts y reparación exacta tienen antecedentes explícitos. No se reclama
su idea general como novedad:
[Start](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html#attrstart),
[MIPGap e IntegralityFocus](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html),
[Eifler–Gleixner](https://arxiv.org/abs/2101.09141),
[SoPlex exacto](https://soplex.zib.de/doc/html/EXACT.php) y
[MIPLIB Numerics](https://miplib.zib.de/tag_numerics.html).
