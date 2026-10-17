#!/usr/bin/env python3
"""Separate report for held-out groups and the posthoc fixed-pattern cost audit."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(p):return json.loads(p.read_text())
def mdrows(rows):return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)
def texrows(rows):return '\n'.join(' & '.join(map(str,r))+r'\\' for r in rows)


def main():
    out=HERE/'confirmation';d=load(out/'design.json');v=load(out/'independent-verification.json')
    cv=load(HERE/'cost-audit/independent-verification.json');fv=load(HERE/'cost-audit/farkas-verification.json')
    records=list(csv.DictReader((out/'outcomes.csv').open()));certs=load(HERE/'cost-audit/certificates.json')
    assert v['assigned_treatments']==80 and v['execution_errors']==0
    assert cv['primal_dual_optimum_certificates']==12 and fv['fixed_pattern_infeasibilities_verified']==4
    source_nive=next(r for r in v['original_mps_checks'] if r['name']=='neos-3083784-nive')
    assert source_nive['decimal_literals_rounded_in_binary64']==0
    acceptance=[]
    for m in d['models']:
        for solver in ('gurobi','highs'):
            suffix='-IF1' if solver=='gurobi' else ''
            cells=[]
            for p in ('Base','L2','Budget','Base-tight'):
                arm=solver+'-'+p+(suffix if p!='Base-tight' else '')
                rs=[r for r in records if r['model']==m['name'] and r['arm']==arm]
                assert len(rs)==2
                cells.append(f"{sum(r['source_budget_met']=='True' for r in rs)}/{sum(r['delivered']=='True' for r in rs)}")
            acceptance.append([m['name']+('*' if m['known_reference'] else ''),solver,*cells])
    costing=[]
    for arm in d['arms']:
        row=[arm]
        for seed in (83,97):
            c=next((r for r in certs if r['arm']==arm and r['seed']==seed),None)
            if c:row.extend([f"{c['numeric_objective']:.3f}",f"{c['pattern_lower_bound']:.0f}"])
            else:row.extend(['0','inviable z'])
        costing.append(row)
    md=f'''# Transferencia, costos comprobables y límites de los contratos

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
'''+mdrows(acceptance)+f'''

Hubo {v['native_calls']} llamadas y {v['delivered_points_checked']} entregas; ocho
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

La auditoría principal detecta {v['bound_discrepancies']} cota contradicha,
{v['gap_discrepancies']} informes al 1 % contradichos y
{v['internally_inconsistent_reports']} gap internamente incompatible, todos en
la referencia. Sus cuentas se solapan. Ausencia de contradicción no valida
los otros informes. Hay {v['accepted_sources_with_nominal_mu_above_one']} fuentes
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
'''+mdrows(costing)+f'''

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
{cv['audit_seconds']:.3f} s para 16 LP; se conservan los cuatro que no tienen primal
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
'''
    (HERE/'RESULTADOS.md').write_text(md)
    t=r'''\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage[spanish]{babel}
\usepackage{lmodern,amsmath,amssymb,booktabs}\usepackage[margin=1.85cm]{geometry}
\usepackage[hidelinks]{hyperref}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\begin{document}\begin{center}{\Large Transferencia y costo comprobable}\\[4pt]
{\large Auditoría de contratos en grupos nuevos y dos solvers}\\[3pt]
14 de octubre de 2026 --- investigación independiente de OMS\end{center}
\textbf{Hallazgo útil.} Una entrega puede satisfacer presupuestos y reportar
costo cero, pero requerir un costo mínimo positivo con sus propios enteros.
La auditoría exacta demuestra 59,631/37,251 en cuatro casos; otros cuatro
patrones no tienen continuación exacta. Se implementó un diagnóstico primal/dual
con efecto de presupuesto. No se reclama como nueva la dualidad débil.
\section*{Diseño y fuentes}
Selección fijada antes de descargar/resolver: cuatro grupos Numerics explícitos
no usados previamente, mixtos I/C, easy, hasta 5000 filas/variables y 50,000 no
ceros, orden por no ceros/nombre. Control es referencia conocida, no evidencia
de transferencia. No hay selección aleatoria o representatividad poblacional.

80 tratamientos: cinco modelos, semillas nuevas 83/97, cuatro métodos por
solver. Gurobi 13.0.2 y HiGHS 1.15.1, cuatro hilos, presolve/escalado normales,
gap 1\%, hasta 15 s MILP y referencia de ciclo 20 s. Gurobi Base/L2/Budget
comparten IntegralityFocus 1; HiGHS no tiene ese control. Base-tight usa
factibilidad/integralidad $10^{-9}$. No hay warm starts.

Presupuestos algebraicos experimentales $\delta_r=10^{-4}\max(1,|b_r|)$,
cotas $10^{-4}$ y dominios enteros exactos. No son tolerancias físicas u
operativas. Kernel diádico existente, ventana $[10^{-9},10^9]$,
hipótesis exportada $\varepsilon=10^{-6}$. Selección para el punto crudo,
entero verificado por separado. No se reajustan tras ver resultados.

El MPS de nive tiene 12,123 no ceros frente a 11,583 de su ficha. Se conservan
todos los datos originales. Cotejo independiente de MPS: coeficientes, RHS,
sentidos, costos, cotas y dominios, con hashes de descarga.
\section*{Aceptación fuente/entrega por dos semillas}
\begin{center}\small\begin{tabular}{@{}llrrrr@{}}\toprule
Modelo & Solver & Base & L2 & Budget & Tight\\\midrule
'''+texrows(acceptance)+r'''
\bottomrule\end{tabular}\end{center}
Cada celda cuenta fuentes enteras verificadas/entregas tras postproceso.
Denominador dos; asterisco identifica referencia conocida. Verificar
presupuestos no certifica factibilidad exacta, costo o optimalidad global.
\newpage
\section*{Transferencia y controles fuertes}
Neos-1112787 traslada la mejora sobre L2 a otro grupo Gurobi: L2-IF1 declara
terminación óptima pero falla el presupuesto en ambas semillas; Budget-IF1
recupera ambas entregas. Base-IF1 y Base-tight ya cumplen. En HiGHS, Base,
L2 y Budget fallan la entrega, mientras Base-tight cumple. No se demuestra
ventaja sobre controles fuertes ni la misma mejora en el segundo solver.

En clasificación Budget obtiene mejores incumbentes que L2; Base-tight
Gurobi iguala su costo 35.767842 en ambas semillas. Lesse da el mismo
objetivo con todos los métodos. Factores modificados: 1640, 683 y 160.
En nive, L2/Budget son idénticos y no se modifica ningún factor: las diferencias
de tiempo o iteraciones bajo límite de reloj no prueban efecto del contrato.

80 llamadas, 72 entregas, ocho abstenciones posteriores sin candidato,
cero incompatibilidades o errores de ejecución. Cuatro ciclos HiGHS/nive
superan 20 s (23.1--23.6 s): importación/cotejo de 7.0--7.4 s más 15 s
de resolución. El límite solicitado antes de importar no se ajustó luego:
limitación temporal del controlador, con todos los casos conservados.
Preparación compartida y persistencia final se miden aparte.

Una cota, dos informes al 1\% y un gap internamente incompatible se
contradicen en la referencia; las cuentas se solapan. No refutar otras cotas
no las valida. En 64 fuentes aceptables, $\mu$ nominal supera uno: no tener
garantía suficiente no predice un fallo.
\section*{El costo cero que no demuestra mejora}
En nive, Gurobi y HiGHS L2/Budget entregan cero dentro de los presupuestos.
Filas big-M con RHS $10^{10}$ permiten residuos hasta $10^6$ bajo esta
especificación. Es demasiado laxa para justificar fidelidad del objetivo.
No contradice el contrato: el punto cumple lo pedido, pero lo pedido no
garantiza costo realizable para esos enteros.

Se congeló después de observarlo una auditoría de los 16 patrones de nive,
todos los tratamientos/semillas. LP exacto hasta 2 s, salidas primal y dual;
sin nuevos MILP ni cambios de factores. Su costo se informa aparte, sin
atribuirlo al algoritmo previamente evaluado.
\begin{center}\small\begin{tabular}{@{}lrrrr@{}}\toprule
Tratamiento & Nominal 83 & Mínimo $z$, 83 & Nominal 97 & Mínimo $z$, 97\\\midrule
'''+texrows(costing)+r'''
\bottomrule\end{tabular}\end{center}
``Inviable $z$'' afecta al patrón entero y no al MILP global. Los doce
pares primal/dual prueban óptimos de LP fijados; cuatro rayos prueban
patrones sin continuación. No se llama cota inferior global a su costo.
Son recuentos de entregas, no patrones únicos; L2/Budget duplican patrones.
La evaluación de $c^\top x$ es correcta; lo que ese precio no respalda
es una continuación exactamente factible de sus enteros con el mismo costo.
\newpage
\section*{Certificado y efecto del presupuesto sobre el costo}
Fije los enteros $z$. Para el LP continuo, un dual factible $\pi$ tiene
signo no positivo en filas $\le$, no negativo en filas $\ge$, libre en
igualdades. Sea $r=c-A^\top\pi$. Si el extremo seleccionado por cada
$r_j\ne0$ es finito (el término con $r_j=0$ vale cero),
\[
L_z=c_I^\top z+\pi^\top b(z)+\sum_j\min\{r_jl_j,r_ju_j\}
\]
es cota inferior del LP de ese patrón. Un primal exacto $q$ que alcanza
$L_z$ certifica su óptimo. El checker verifica todas las filas, cotas,
enteros, signos y costos, sin confiar en el estado del solver.

Si $y$ satisface los presupuestos de filas $\delta_r$ y cotas $\beta_j$,
\[
c_I^\top z+c^\top y\ge L_z-\Delta_z,\qquad
\Delta_z=\sum_r|\pi_r|\delta_r+\sum_{j\in C}|r_j|\beta_j.
\]
Cada fila violada puede reducir su contribución dual a lo sumo
$|\pi_r|\delta_r$; la caja ampliada reduce el término de costo reducido
a lo sumo $|r_j|\beta_j$. Sumarlo da la desigualdad. Es dualidad débil
elemental, sin novedad matemática reclamada. Acota subestimación, no exceso
de costo o gap global. Los doce certificados verifican esa desigualdad.

Gurobi/97 tiene $L_z=37,251$, precio nominal cero y
$\Delta_z\approx1.871\,10^{10}$. El cero es compatible con los presupuestos;
estos no protegen de manera útil el costo. Una $\Delta_z$ grande sola no
predice daño: el déficit observado se prueba por separado con $L_z$.

Los rayos de Farkas combinan filas, con sus signos correctos, de manera que
el RHS supera el máximo de actividad sobre la caja continua. Prueban que
el patrón no puede completarse exactamente. El soporte de la caja ampliada
y los presupuestos explican la aceptación numérica de los mismos puntos.
No prueban inviabilidad del MILP con otros enteros.

\textbf{Representación.} Todos los literales originales de nive son exactos
en binary64: cero redondeos de coeficientes, RHS, costos o cotas. El fenómeno
no procede de reemplazar 0.1 por su aproximación binaria. En los demás
modelos los certificados se refieren a la representación canónica binary64,
con esa limitación explícita frente a decimales racionales ideales.
\section*{Utilidad del diagnóstico}
Permite separar candidato numérico con costo respaldado, subestimación para
el mismo patrón y patrón sin continuación exacta. El controlador que
retiene el menor costo numérico puede preferir un cero sin respaldo a una
reparación exacta positiva. Los datos no se corrigen retroactivamente:
se mantienen separados costo nominal y mejor costo factible exacto.

Los presupuestos relativos al RHS de una formulación big-M no sustituyen
requisitos de aplicación. La precisión física debe especificarse en las
unidades y magnitudes pertinentes antes de atribuir sentido operativo
al error algebraico. MIPLIB no fija tolerancias de planta o del operador.
\newpage
\section*{Alcance para el paper OMS}
Hay un resultado empírico nuevo en esta investigación y un diagnóstico de
software concreto: presupuestos primales cumplidos no bastan para respaldar
el precio declarado de un patrón entero. El costo puede auditarse con
certificados primal/dual y el efecto de los presupuestos puede cuantificarse.
No se reclama inventar dualidad, Farkas, reparación exacta o un nuevo
algoritmo globalmente certificado; tienen antecedentes explícitos.

El seguimiento aporta otro grupo con beneficio frente a L2 en Gurobi,
pero no una ventaja general sobre Base/tolerancias estrictas ni sobre ambos
solvers. Se mantiene OMS v1.3.5 sin cambios. Queda una redacción candidata
acotada, fuera del manuscrito, sin crear una tercera contribución o teorema.
\section*{Evidencia y reproducción}
El checker principal revisa 80 fuentes, 110 candidatos, 20,673 factores,
64 registros de testigos exactos y cinco MPS. Los testigos pueden repetir
puntos; no se cuentan como soluciones únicas. Toda abstención, límite y
exceso de tiempo se conserva. Dos semillas por grupo no sustentan inferencia
poblacional o superioridad de velocidad a calidad equivalente.

La auditoría de costo verifica doce certificados de óptimo de LP y cuatro
rayos de patrones inviables, sobre las 16 entregas fijadas. Seis tests
cubren signos, cotas superiores, variables libres, igualdad racional,
patrones distintos y compatibilidad entre infeasibilidad exacta y presupuesto.
''' + f'''
Las 16 llamadas LP adicionales costaron {cv['audit_seconds']:.3f} s en total,
por separado de los ciclos experimentales.
''' + r'''

El artefacto incluye diseños, protocolos posteriores explícitos, snapshots,
MPS, exportaciones, puntos, logs, duales, rayos, tiempos y hashes. Python y
NumPy bastan para verificación guardada; pytest para tests. No hay llamadas
solver en replay. Ejecutar nuevas optimizaciones requiere las herramientas
declaradas; sus binarios/licencias no se redistribuyen. Los archivos y
diseños anteriores, incluido el envío OMS, conservan sus hashes.
\begin{verbatim}
python3 exploration/oms-transfer-study-20261014/independent_check.py
python3 exploration/oms-transfer-study-20261014/cost_audit.py replay
python3 exploration/oms-transfer-study-20261014/check_cost_rays.py
python3 exploration/oms-transfer-study-20261014/write_report.py
\end{verbatim}
\small
\href{https://miplib.zib.de/tag_numerics.html}{MIPLIB Numerics: colección y fuentes.}\\
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html}{Gurobi: controles, tolerancias y gap.}\\
\href{https://ergo-code.github.io/HiGHS/stable/options/definitions/}{HiGHS: opciones numéricas y límites.}\\
\href{https://soplex.zib.de/doc/html/EXACT.php}{SoPlex: aritmética racional y referencias de LP.}\\
\href{https://arxiv.org/abs/2101.09141}{Eifler y Gleixner: reparación y certificación exacta.}
\end{document}
'''
    (HERE/'transfer-note.tex').write_text(t)
    print('Regenerated held-out study report and posthoc cost audit note')


if __name__=='__main__':main()
