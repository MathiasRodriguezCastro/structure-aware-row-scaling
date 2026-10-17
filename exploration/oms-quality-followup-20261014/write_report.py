#!/usr/bin/env python3
"""Regenerate a separate working report from audited primary and crossover data."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(path):return json.loads(Path(path).read_text())
def table(rows):return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)
def texrows(rows):return '\n'.join(' & '.join(map(str,r))+r'\\' for r in rows)


def main():
    out=HERE/'confirmation';ab=HERE/'ablation'
    audit=load(out/'independent-verification.json');aa=load(ab/'independent-verification.json')
    design=load(out/'design.json')
    records=[load(out/'runs'/t['model']/f"{t['arm']}-s{t['seed']}"/'run.json') for t in design['queue']]
    ars=list(csv.DictReader((ab/'outcomes.csv').open()));pairs=list(csv.DictReader((out/'paired-comparisons.csv').open()))
    assert audit['assigned_treatments']==48 and aa['assigned_treatments']==14
    assert audit['execution_errors']==aa['execution_errors']==0
    overview=[]
    pooled=load(out/'pooled-bound-discrepancies.json')
    for arm in design['arms']:
        rs=[r for r in records if r['arm']==arm]
        overview.append([arm,f"{sum(r['delivered'] for r in rs)}/6",f"{sum(r['total_seconds'] for r in rs):.3f}",
                         sum(r.get('online_bound_contradictions',0) for r in rs),sum(r['arm']==arm for r in pooled)])
    paired=[]
    for arm in ('Base-warm-tight','Base-warm-IF1','L2-warm-IF1','Budget-warm-IF1','Witness-warm-tight'):
        ps=[r for r in pairs if r['warm_arm']==arm]
        paired.append([arm,sum(r['better_by_one_percent']=='True' for r in ps),sum(r['worse_by_one_percent']=='True' for r in ps),
                       sum(r['objective_comparison']=='not_both_delivered' for r in ps)])
    crossed=[]
    order=('Cold-Base-IF1','Cold-L2-IF1','Cold-Budget-IF1','Warm-L2-to-L2','Warm-L2-to-Budget','Warm-Budget-to-L2','Warm-Budget-to-Budget')
    for arm in order:
        a=next(r for r in ars if r['arm']==arm and r['seed']=='59');b=next(r for r in ars if r['arm']==arm and r['seed']=='71')
        crossed.append([arm,f"{float(a['objective']):.6f}",f"{float(b['objective']):.6f}",
                        f"{float(a['total_seconds']):.3f}/{float(b['total_seconds']):.3f}",
                        str(sum(r['final_source_budget_met']=='True' for r in (a,b)))+'/2'])
    final_l2=[r for r in ars if r['final_representation']=='Dyadic-L2']
    final_budget=[r for r in ars if r['final_representation']=='Budget-dyadic-L2']
    assert len(final_l2)==len(final_budget)==6
    ab_gaps=load(ab/'pooled-gap-discrepancies.json');ab_bounds=load(ab/'pooled-bound-discrepancies.json')
    l2_gap_final=sum(r['phase']==(0 if r['arm'].startswith('Cold') else 1) and r['arm'] in {v['arm'] for v in final_l2} for r in ab_gaps)
    assert l2_gap_final==6 and aa['pooled_bound_contradictions']==4
    md=f'''# Calidad, warm starts y cotas: seguimiento y ablación

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
'''+table(overview)+f'''

Hubo {audit['native_mip_calls']} llamadas MILP, {audit['delivered_points_checked']}
entregas y dos abstenciones por los 96 intervalos incompatibles de cinca. Se
proporcionaron {audit['mip_starts_supplied']} Starts y los logs registran la carga
de {audit['mip_starts_loaded_in_logs']}; proporcionar un punto no implica que el
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
'''+table(paired)+f'''

En particular Base-warm-IF1 no tiene mejoras superiores a 1 % y empeora en tres
pares. La reparación sí puede servir como inicio, pero este experimento rechaza
la afirmación de una ventaja general de calidad/velocidad del ciclo warm.

## Cotas, gap y consistencia del informe

Tres testigos exactos disponibles **antes** del seguimiento permitieron vetar
{audit['online_bound_contradictions']} cotas durante las fases. La auditoría con
el mejor testigo obtenido más tarde contradice {audit['pooled_bound_contradictions']}
cotas y {audit['pooled_gap_contradictions']} declaraciones de terminación al 1 %.
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
'''+table(crossed)+f'''

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
ni llamar solvers. Los {audit['new_exact_witnesses_checked']+aa['new_exact_witnesses_checked']}
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
'''
    (HERE/'RESULTADOS.md').write_text(md)
    preamble=r'''\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage[spanish]{babel}
\usepackage{lmodern,amsmath,amssymb,booktabs,tabularx}
\usepackage[margin=1.9cm]{geometry}\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\begin{document}
\begin{center}{\Large Calidad, warm starts y cotas}\\[4pt]
{\large Seguimiento y ablación independientes de OMS}\\[3pt]
14 de octubre de 2026 --- documento de investigación\end{center}
\textbf{Resultado.} Hay una señal concreta para Budget-L2 en un modelo auténtico:
evita objetivos pobres e informes de L2 contradichos. La ablación identifica un
efecto de la representación final. No hay ventaja general frente a Base/IF1 y
el envío v1.3.5 permanece separado y sin cambios.
\section*{Diseño prospectivo y entregas}
48 asignaciones: los tres MIPLIB previamente seleccionados, semillas nuevas
31/47 y ocho tratamientos. Gurobi 13.0.2, cuatro hilos, gap 1\%, presolve y
escalado interno automáticos salvo el control indicado. Frío: hasta 15 s;
warm: hasta $1+14$ s MILP. Referencia global: 20 s, incluyendo selección,
exportación, importación/cotejo, resolución, reparación, verificación y auditoría.
Los factores diádicos existentes no se reajustan después de resultados.

Presupuestos $\delta_r=10^{-4}\max(1,|b_r|)$, cotas $10^{-4}$, dominios
enteros exactos; unidades algebraicas experimentales. Contratos para el punto
crudo y comprobación separada del entero. No son tolerancias físicas operativas.
\begin{center}\small\begin{tabular}{@{}lrrrr@{}}\toprule
Tratamiento & Entregas & Suma s & Veto online & Cotas en pool\\\midrule
'''
    text=preamble+texrows(overview)+r'''
\bottomrule\end{tabular}\end{center}
Las cuentas online y posteriores son por fase y se solapan. No se suman como
fallos distintos. Denominador seis, incluidas abstenciones. La suma de tiempos
no compara velocidades a calidad equivalente ni estima rendimiento poblacional.
''' + f'''
Hubo {audit['native_mip_calls']} llamadas MILP y {audit['delivered_points_checked']}
entregas. Cinca se abstiene dos veces por 96 intervalos incompatibles. Se
proporcionaron {audit['mip_starts_supplied']} Starts y los logs registran
{audit['mip_starts_loaded_in_logs']} cargas. No hubo errores o excesos de 20 s.
''' + r'''
La preparación compartida se cronometró aparte. La persistencia final del
seguimiento también; en ablación, el NPZ final se incluye sin medición separada.
Los archivos auxiliares quedan en su etapa. El control Witness-warm tiene un
testigo exacto previo cuya adquisición está excluida y declarada: es diagnóstico
con información previa, no un algoritmo de velocidad nuevo. Los tres modelos
no son familias nuevas ni una muestra representativa.
\newpage
\section*{La reparación puede iniciar otra búsqueda, sin ventaja general}
En control, warm-tight entrega 1.374590/1.400469 y warm-IF1 1.313721/1.313715,
recuperando calidad frente al LP solo (antes 26.248128). Cold-IF1 entrega
1.265274/1.313755 y Cold-tight 1.322940/1.433450. Calentar no supera
sistemáticamente a los controles robustos con igual asignación MILP.

Comparaciones por modelo/semilla: umbral descriptivo del 1\% del objetivo frío,
además de una guarda numérica. No es significación estadística ni gap certificado.
\begin{center}\small\begin{tabular}{@{}lrrr@{}}\toprule
Warm contra su control frío & Mejora $>1\%$ & Peor $>1\%$ & Sin dos entregas\\\midrule
''' + texrows(paired)+r'''
\bottomrule\end{tabular}\end{center}
Base-warm-IF1 no mejora más del 1\% en ningún par y empeora en tres.
Witness-warm usa información previa y no es un control de velocidad equitativo.
\section*{Testigos y certificaciones incompatibles}
Tres testigos exactos previos permitieron cinco vetos online. Los mejores
testigos obtenidos después contradicen siete cotas y ocho informes de
terminación al 1\%. Optimalidad continúa no verificada. Una cota no refutada
no pasa a ser válida por esa ausencia de evidencia.

Los testigos completos verifican todas las filas, cotas y dominios. Los
objetivos mostrados son 1.265277 en control y 7,547,811.68 en ta1-UUM.
El checker coteja los MPS originales, incluyendo costos y dominios, bajo su
interpretación binary64; no se mezclan modelos ni se usan puntos solo
factibles dentro de tolerancias como testigos exactos.

En ta1-UUM, Base-warm-tight y presolve-off tienen cotas contradichas en ambas
semillas; Cold-tight falla en 47. Witness-warm-tight/47 necesita el testigo
mejor obtenido después. Un testigo previo demasiado caro no detecta todos
los fallos. Desactivar presolve no elimina el problema y no se atribuye una
causa interna específica al solver.

\textbf{Consistencia del propio informe.} Control/L2-warm-IF1/47 conserva
etiqueta óptima, objetivo $5.643361$ y cota $-24.177882$. Su log muestra gap
$528.4306\%$, frente al 1\% solicitado. Rechazar ese informe no requiere
testigo externo. Se comprueban gap relativo, absoluto y una guarda; no se
penaliza TIME\_LIMIT por no alcanzar el objetivo. Este caso también tiene
un testigo mejor, pero su cota negativa no queda refutada por él.
\newpage
\section*{Ablación del mecanismo: representación final e inicio}
La señal en control motivó una selección posterior explícita: estudio de
mecanismo, no confirmación independiente de generalización. Antes de nuevas
llamadas se congelaron 14 asignaciones con semillas 59/71: tres controles en
frío y el cruce $2\times2$ L2/Budget entre origen y destino. Se conservaron
todos los resultados y no se añadieron coeficientes M artificiales.

Mismo modelo, presupuestos, factores, tolerancias $10^{-6}/10^{-5}$, presolve
automático e IntegralityFocus 1 en la fase final. Límites $1+14$ s warm y
15 s frío. Cambiar representación conserva exactamente filas/RHS, objetivo
y dominios; el Start se transmite en coordenadas originales verificadas.
\begin{center}\small\begin{tabular}{@{}lrrrr@{}}\toprule
Tratamiento & Costo 59 & Costo 71 & Ciclo 59/71 s & Fuente final V\\\midrule
''' + texrows(crossed)+r'''
\bottomrule\end{tabular}\end{center}
Fuente final V: punto del solver tras redondear pasa todas las comprobaciones;
las entregas finales pasan en los catorce casos gracias al filtro y reparación.

Los seis destinos L2 declaran terminación óptima, pero sus informes al 1\%
son contradichos por testigos exactos. Cuatro presentan cota inferior
imposible y los otros dos un gap interno incompatible. Los seis destinos
Budget alcanzan el límite y no declaran óptimo; costos 1.265--1.316.
No se certifica su óptimo ni se considera válida una cota solo por no refutarla.

Budget$\to$L2 entrega 3.068627/7.875892: un mejor tipo de inicio no rescata
la representación L2. L2$\to$Budget entrega 1.313510/1.315735 y evita esos
resultados. El efecto pertenece a la representación final dentro de esta
configuración; no identifica una operación interna concreta del solver.
Los cuatro pares tienen Starts con valores binary64 idénticos y la misma
primera fase, comprobados por el checker; cambia la representación final.

En frío, Budget da 1.313510/1.265136 frente a L2 2.815707/33.373658.
Base/IF1 da 1.315834/1.391930 y no tiene cotas contradichas. Evitar el falso
cierre rápido requiere casi todo el tiempo, unos 15 s frente a menos de 1 s.
Es calidad y fiabilidad recuperada, no aceleración. Un modelo y cuatro
semillas acumuladas no prueban ventaja general sobre controles existentes.
\newpage
\section*{Propiedades del controlador}
Sea $V_\delta(y)$ la comprobación completa de filas/cotas dentro de sus
presupuestos y dominios enteros exactos. Cada candidato entra en $S_k$
solo si verifica $V_\delta$. Las etapas no borran candidatos. Por inclusión,
\[
S_k\subseteq S_{k+1}\quad\Longrightarrow\quad
\min_{y\in S_{k+1}}c(y)\le\min_{y\in S_k}c(y).
\]
Todo punto devuelto verifica, y una fase que falla o entrega un objetivo peor
no hace perder el punto anterior. El costo se calcula racionalmente sobre los
valores binary64. Si no hay candidato, se abstiene. No se garantiza progreso
estricto ni superar otra configuración o encontrar el óptimo global.

Para un testigo racional factible $q$, $U=c^\top q$ es una cota superior
primal. Cualquier cota inferior válida satisface
\[
B\le z^*\le U.
\]
Por tanto $B>U$ contradice su validez. El checker requiere el mismo modelo y
factibilidad exacta de todas las filas, cotas y dominios. Usa una guarda de
$\max(10^{-6},8\,\mathrm{ulp}(B))$. Una conversión flotante puede fallar su
presupuesto aunque el testigo racional sea válido; se verifica por separado.
No hallar contradicción no certifica optimalidad y el gap de un punto fuente
no se hereda después de repararlo.

El filtro adicional del informe comprueba
\[
|C-B|>\max\{0.01|C|,10^{-10}\}+\text{guarda}.
\]
Solo descarta incompatibilidad con la terminación solicitada; no certifica
factibilidad, cota dual u óptimo. Se aplica posteriormente y se declara como
tal, sin cambiar el diseño ya ejecutado. Nueve tests cubren retención,
dominios, importación, modelos distintos, testigos exactos sin entrega
binary64, gap relativo/absoluto y ausencia de inferencias de optimalidad.
\section*{Decisión de alcance para OMS}
Existe un resultado tangible: con presolve normal y un modelo auténtico,
la proyección contractual evita objetivos pobres e informes L2 refutados.
El cruce confirma un efecto de la representación final. Es una señal para
discutir el uso verificable de representaciones exportadas.

Todavía no justifica una contribución general adicional: un solo modelo
presenta el mecanismo, Base/IF1 sigue siendo competitivo, el contrato no gana
en otros casos o se abstiene, y warm no aporta ventaja general. Se mantiene
v1.3.5 sin cambios. Una redacción candidata acotada queda en
\texttt{INCORPORACION\_CANDIDATA.md}, sin afirmar que contratos certifiquen
cotas, optimalidad o superioridad universal.
\newpage
\section*{Evidencia, fuentes y reproducción}
62 asignaciones nuevas, 90 llamadas MILP, 60 entregas verificadas y dos
abstenciones contractuales. Los checkers independientes comprueban fuentes,
puntos, retención, testigos, límites y vetos; no importan los runners o
controladores ni llaman solvers. Hay 61 registros nuevos de testigos exactos;
pueden repetir puntos y no se anuncian como soluciones únicas.

Los tres MPS originales se verifican con hashes de descarga. Coeficientes,
RHS, sentidos, costos, cotas y dominios se cotejan contra la representación
canónica binary64. Los certificados corresponden a ese modelo, no a los
decimales racionales ideales del MPS. El adapter independiente admite las
características presentes y rechaza otras.

Los protocolos, hashes, fuentes, exportaciones, Starts, puntos, tiempos,
datos adversos y certificados se conservan. La preparación compartida del
seguimiento y la ablación se mide aparte. Los testigos previos se obtuvieron
en estudios anteriores; para cinca, un LP exacto adicional de desarrollo
se guarda y queda fuera de las 62 asignaciones. No se anuncia su adquisición
como gratuita en Witness-warm ni se llama online al pool posterior.

\textbf{Replay sin licencia comercial.} Desde la raíz del artefacto, Python
y NumPy bastan para ambos checkers. Pytest ejecuta nueve tests. Regenerar
el documento necesita Python; compilarlo requiere pdfLaTeX. Ejecutar nuevas
optimizaciones sí necesita Gurobi/HiGHS/SoPlex con las dependencias declaradas.
Los códigos y modelos congelados no se editan para reanudar experimentos.
\begin{verbatim}
python3 exploration/oms-quality-followup-20261014/independent_check.py
python3 exploration/oms-quality-followup-20261014/check_ablation.py
python3 exploration/oms-quality-followup-20261014/write_report.py
\end{verbatim}
\textbf{Originalidad.} Warm starts, reparación exacta y certificación tienen
antecedentes explícitos. No se reclama su idea general como nueva. Se investiga
la interacción de precisión, representación, aceptación, calidad y trazabilidad,
con controles fuertes y resultados adversos. Las propiedades del filtro y de
retención son elementales y no se venden como teoremas novedosos.

\small
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html}{Gurobi: Start y atributos de variables.}\\
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html}{Gurobi: MIPGap, MIPGapAbs e IntegralityFocus.}\\
\href{https://arxiv.org/abs/2101.09141}{Eifler y Gleixner: exact rational MIP (2021).}\\
\href{https://soplex.zib.de/doc/html/EXACT.php}{SoPlex: LP exacto y referencias.}\\
\href{https://miplib.zib.de/tag_numerics.html}{MIPLIB: Numerics y modelos originales.}\\
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/fileformats/modelformats.html}{Gurobi: convenciones MPS, bounds e integrality markers.}
\end{document}
'''
    (HERE/'quality-note.tex').write_text(text)
    print('Regenerated separate report from 48 prospective and 14 crossover treatments')


if __name__=='__main__':main()
