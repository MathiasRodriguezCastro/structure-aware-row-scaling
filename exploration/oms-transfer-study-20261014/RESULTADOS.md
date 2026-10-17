# Transferencia, costos comprobables y límites de los contratos

**Resultado nuevo y útil:** una entrega puede cumplir todos los presupuestos de
residuo y aun informar un costo que no es realizable con sus propios enteros.
En nive se comprobó costo nominal cero frente a mínimos exactos de 59.631 y
37.251 para esos patrones. Otros cuatro patrones numéricamente aceptables no
tienen continuación exacta. Se implementó y verificó un diagnóstico primal/dual
que distingue estos estados y cuantifica el efecto de los presupuestos sobre
la posible subestimación del costo. Es nuevo en esta investigación, no se
reclama como nuevo el teorema de dualidad débil o la idea general de reparar.

El seguimiento también traslada la señal Budget frente a L2 a otro grupo en
Gurobi. No demuestra superioridad general frente a Base/tolerancias estrictas,
ni una ventaja de aceptación en HiGHS. OMS v1.3.5 permanece sin modificaciones.

## Diseño prospectivo y fuentes

Cuatro grupos no usados previamente, elegidos antes de descargar y resolver:
neos-1112787, breastcancer-regularized, neos-3083784-nive y neos-3661949-lesse.
Se conservan los primeros cuatro grupos explícitos distintos del inventario
Numerics archivado, easy, mezcla I/C, <=5000 filas/variables y <=50000 no ceros,
orden por no ceros/nombre. Grupos desconocidos no se cuentan como independientes.
La referencia control30-3-2-3 es conocida y no se incluye como evidencia retenida.
No es una muestra aleatoria ni representativa de todo MILP.

Cinco modelos × semillas nuevas 83/97 × cuatro alternativas por solver = 80
asignaciones; 64 de grupos nuevos y 16 de referencia. Gurobi 13.0.2, HiGHS 1.15.1,
cuatro hilos, gap 1 %, presolve y escalado interno habituales, sin warm starts.
Base/L2/Budget Gurobi comparten IntegralityFocus=1 y tolerancias ordinarias;
HiGHS no tiene ese parámetro. Base-tight usa tolerancias de factibilidad e
integralidad 1e-9 en ambos. Límites MILP 15 s, referencia de ciclo 20 s y orden
aleatorio fijo. No se cambian modelos, factores o presupuestos tras ver resultados.

Presupuestos algebraicos experimentales delta_r=1e-4 max(1,|RHS|), cotas 1e-4,
dominios enteros exactos. No son tolerancias físicas u operativas. Las reglas
L2/Budget usan el mismo kernel diádico existente, ventana [1e-9,1e9] e hipótesis
exportada epsilon=1e-6. Los contratos cubren el punto crudo; el entero se verifica
por separado. El MPS de nive tiene 12.123 no ceros frente a 11.583 de la ficha;
se conserva el archivo original y todos sus coeficientes.

## Aceptación y comparación con controles

Cada celda es fuente entera verificada/entrega después del postproceso, de dos
semillas. Fuente/entrega 2/2 no indica optimalidad. Asterisco: referencia conocida.

| Modelo | Solver | Base | L2 | Budget | Base-tight |
|---|---|---:|---:|---:|---:|
| neos-1112787 | gurobi | 2/2 | 0/0 | 2/2 | 2/2 |
| neos-1112787 | highs | 0/0 | 0/0 | 0/0 | 2/2 |
| breastcancer-regularized | gurobi | 2/2 | 2/2 | 2/2 | 2/2 |
| breastcancer-regularized | highs | 2/2 | 2/2 | 2/2 | 2/2 |
| neos-3083784-nive | gurobi | 2/2 | 2/2 | 2/2 | 2/2 |
| neos-3083784-nive | highs | 2/2 | 2/2 | 2/2 | 2/2 |
| neos-3661949-lesse | gurobi | 2/2 | 2/2 | 2/2 | 2/2 |
| neos-3661949-lesse | highs | 2/2 | 2/2 | 2/2 | 2/2 |
| control30-3-2-3* | gurobi | 2/2 | 2/2 | 2/2 | 2/2 |
| control30-3-2-3* | highs | 2/2 | 2/2 | 2/2 | 2/2 |

Hubo 80 llamadas y 72 entregas; ocho
abstenciones a posteriori por falta de candidato verificado, sin incompatibilidades
de factores o errores de ejecución. Se guardan todas. Cuatro ciclos HiGHS/nive
superaron 20 s y duraron aproximadamente 23,1–23,6 s: la importación y su cotejo
tomaron 7,0–7,4 s, además de los 15 s de resolución. El límite del solver se
había solicitado antes de esa importación, sin descontarla posteriormente.
Es una limitación del control temporal implementado; no se excluyen esos casos.

En neos-1112787, Gurobi/L2-IF1 declara terminación óptima en ambas semillas,
pero el punto falla el presupuesto y no se recupera una entrega. Budget-IF1
pasa ambas, igual que Base-IF1 y Base-tight. En HiGHS, Base/L2/Budget fallan
la entrega y Base-tight sí pasa. La mejora sobre L2 se traslada a otro grupo,
pero no supera los controles fuertes ni se repite como ventaja en el segundo solver.

En el modelo de clasificación, Budget tiene mejores incumbentes que L2 en ambos
solvers; Base-tight Gurobi iguala su costo 35,767842 en ambas semillas. Lesse
entrega el mismo objetivo con todas las políticas. No se concluye superioridad
poblacional de dos semillas ni se agregan costos de modelos distintos como si
midieran velocidad a igual calidad.

Los contratos cambian 1.640, 683 y 160 factores en esos tres modelos. En nive
no cambian ninguno: los archivos L2/Budget son idénticos, un control negativo.
Una diferencia de tiempos/iteraciones bajo límite de reloj con esos mismos
datos no puede atribuirse a una modificación contractual inexistente.

La auditoría principal detecta 1 cota contradicha,
2 informes al 1 % contradichos y
1 gap internamente incompatible, todos en
la referencia. Sus cuentas se solapan. Ausencia de contradicción no valida
los otros informes. Hay 64 fuentes
aceptables con mu nominal >1: no tener garantía suficiente no predice un fallo.

## El cero que no es una mejora de costo

En nive, L2 y Budget informan cero en Gurobi y HiGHS, y las entregas pasan los
presupuestos. Sería incorrecto contarlas sin más como mejoras sobre Base.
Las filas big-M tienen RHS de hasta 1e10: el presupuesto relativo permite hasta
1e6 de residuo en algunas filas. Esta especificación es demasiado laxa para
justificar fidelidad del costo. El contrato no se contradice: cumple lo pedido;
es lo pedido lo que no controla el significado del valor objetivo informado.

Se fijó **después de observarlo** una auditoría de los 16 patrones de nive, todos
los métodos y ambas semillas, con LP exacto hasta 2 s y salidas primal/dual.
No se repitió ningún MILP ni se reajustaron presupuestos. El costo de esta
auditoría se mide aparte y no se atribuye al algoritmo de 15 s.

| Tratamiento | Nominal 83 | Mínimo con z, 83 | Nominal 97 | Mínimo con z, 97 |
|---|---:|---:|---:|---:|
| gurobi-Base-IF1 | 27851.000 | 27851 | 27851.000 | 27851 |
| gurobi-L2-IF1 | 0.000 | 59631 | 0.000 | 37251 |
| gurobi-Budget-IF1 | 0.000 | 59631 | 0.000 | 37251 |
| gurobi-Base-tight | 27851.000 | 27851 | 27851.000 | 27851 |
| highs-Base | 31651.000 | 31651 | 27850.999 | 27851 |
| highs-L2 | 0 | inviable z | 0 | inviable z |
| highs-Budget | 0 | inviable z | 0 | inviable z |
| highs-Base-tight | 34250.997 | 34251 | 29650.998 | 29651 |

Los 12 pares primal/dual certifican el óptimo del LP con sus enteros fijados.
Cuatro ceros Gurobi subestiman ese mínimo por 59.631/37.251 unidades. Cuatro
ceros HiGHS tienen rayos de Farkas comprobados: ese patrón no tiene continuación
exacta; el MILP global sí puede tenerla con otros enteros. No se usa el costo
del patrón como cota inferior global. Las ocho políticas Base/tight conservan
costos cercanos o iguales al mínimo de su propio patrón.
Los recuentos son de entregas/tratamientos, no de patrones únicos: L2/Budget
comparten entrada y duplican patrones en este caso.

La evaluación de c^T x del punto numérico es correcta: no se está denunciando
un error de producto escalar. Lo que no respalda ese valor es una continuación
exactamente factible de sus enteros con el mismo costo.

En nive **todos los literales originales se representan exactamente en binary64**:
el checker encuentra cero redondeos en coeficientes, RHS, costos y cotas. El
resultado de costo no es un artefacto de sustituir 0,1 decimal por su aproximación
binaria. En otros modelos se mantiene explícita la interpretación canónica
binary64 y no se anuncian certificados del modelo decimal ideal.

## Diagnóstico de costo desde la dualidad

Tras fijar enteros z, escriba el LP continuo con filas A_r y=b_r(z), o sus sentidos
<=/>=, y cotas l<=y<=u. Un dual factible pi cumple los signos de cada fila.
Los costos reducidos son r=c-A^T pi. Incluyendo el costo fijo c_I^T z,

L_z = c_I^T z + pi^T b(z) + sum_j min(r_j l_j,r_j u_j)

es cota inferior de **ese LP**, cuando el extremo requerido es finito (r_j=0 no
necesita cotas). Un primal exacto q que alcanza L_z certifica su mínimo. El checker
comprueba todas las filas, cotas, enteros, signos y esa igualdad, sin confiar en
la etiqueta del solver.

Si y pasa los presupuestos de filas delta_r y cotas beta_j, entonces

c_I^T z + c^T y >= L_z - Delta_z,
Delta_z = sum_r |pi_r| delta_r + sum_continuas |r_j| beta_j.

La prueba multiplica las violaciones permitidas por sus multiplicadores y usa
el soporte de las cotas ampliadas. Es dualidad débil elemental, no novedad
matemática reclamada. Acota subestimación, no exceso de costo ni gap global.
Los 12 certificados verifican también esa desigualdad exactamente. En el ejemplo
Gurobi/97, L_z=37.251 y Delta_z aproximadamente 1,871e10: el cero es compatible
con los presupuestos, pero estos no proporcionan una protección útil del costo.
Una Delta grande sola no predice daño; el déficit observado se prueba aparte.

Los cuatro rayos combinan filas para producir un RHS superior al máximo de su
actividad sobre la caja continua original. Prueban inviabilidad del patrón,
con los signos y soporte calculados exactamente. La ampliación por los presupuestos
explica por qué los mismos puntos son aceptables numéricamente. No prueban
inviabilidad global MILP. Los seis tests cubren duales con límites superiores,
variables libres, signos, igualdad racional y patrones diferentes.

## Qué es útil y qué no se afirma

El resultado útil es una distinción verificable entre precisión primal, precio
nominal y costo factible de la asignación entera. El prototipo ahora puede
diagnosticar: candidato numérico aceptable con costo respaldado; costo subestimado
para el mismo patrón; o patrón sin continuación exacta. No se publica un nuevo
algoritmo MILP globalmente certificado ni se reclama inventar la dualidad o
la reparación exacta, que tienen antecedentes explícitos.

La selección automática del menor costo entre candidatos meramente numéricos
puede preferir ceros sin respaldo a reparaciones exactas positivas. Se conserva
el experimento sin corregirlo retroactivamente; la recomendación para un controlador
futuro es mantener separados el mejor costo nominal y el mejor costo exacto
factible, según la precisión que solicite el usuario. Los CSV ya separan ambos.

También se confirma por qué un presupuesto ligado al RHS de una formulación
big-M no sustituye un requisito de aplicación. Para defender precisión física
debe especificarse en las unidades y magnitudes que importan a la aplicación,
antes de atribuir sentido operativo al error algebraico. MIPLIB aquí aporta
diagnóstico, no estándares de planta o del operador eléctrico.

**Decisión para OMS:** hay una observación nueva y un diagnóstico concreto de
valor; no hay evidencia de ventaja general sobre controles fuertes. El paper
v1.3.5 se conserva. Queda una redacción candidata breve en
INCORPORACION_CANDIDATA.md; no se agrega una tercera contribución, otro teorema
o una afirmación de optimalidad global a partir de esta auditoría posterior.

## Reproducción

El checker principal reprocesa 80 fuentes, 110 candidatos, 20.673 factores,
64 registros de testigos exactos y los cinco MPS. El costo auditado aparte fue
5.131 s para 16 LP; se conservan los cuatro que no tienen primal
factible y sus rayos. La ausencia de candidato, fallos y excesos forman parte del
artefacto. Las verificaciones guardadas no llaman solvers:

```bash
python3 exploration/oms-transfer-study-20261014/independent_check.py
python3 exploration/oms-transfer-study-20261014/cost_audit.py replay
python3 exploration/oms-transfer-study-20261014/check_cost_rays.py
python3 -m pytest -q exploration/oms-transfer-study-20261014/test_cost_certificate.py exploration/oms-transfer-study-20261014/test_farkas_certificate.py
python3 exploration/oms-transfer-study-20261014/write_report.py
```

Fuentes primarias:
[MIPLIB Numerics](https://miplib.zib.de/tag_numerics.html),
[Gurobi, controles y gap](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html),
[HiGHS, opciones](https://ergo-code.github.io/HiGHS/stable/options/definitions/),
[SoPlex exacto](https://soplex.zib.de/doc/html/EXACT.php) y
[Eifler–Gleixner, reparación y certificación](https://arxiv.org/abs/2101.09141).
