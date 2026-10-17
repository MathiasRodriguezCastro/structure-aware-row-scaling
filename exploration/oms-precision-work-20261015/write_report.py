#!/usr/bin/env python3
"""Short note and transparent work-to-target figure, from archived data only."""
import csv
import json
from pathlib import Path
from fractions import Fraction as Q
from statistics import median

HERE=Path(__file__).resolve().parent
POLICIES=['Base','Tight','GM','Ruiz','L2','NumericFocus','Budget-Demanding']
LABELS={'Base':'Base','Tight':'Base tight','GM':'GM','Ruiz':'Ruiz-R4','L2':'L2','NumericFocus':'L2 NumericFocus 3','Budget-Demanding':'Budget exigente'}


def read(p):return json.loads(p.read_text())
def fmt(x):return '--' if x is None else f'{x:.3g}'


def figure(rows,instances,seeds):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,3,figsize=(11.4,3.6),sharey=True)
    indexed={(r['instance'],r['policy'],int(r['seed'])):r for r in rows if r['scenario']=='Demanding'}
    for ax,instance in zip(axes,instances):
        for j,policy in enumerate(POLICIES):
            color='#b63d32' if policy.startswith('Budget') else '#346786'
            for offset,seed in zip([-.14,0.,.14],seeds):
                r=indexed[(instance,policy,seed)];hit=r['numeric_hit']=='True'
                supported=r['target_pattern_supported']=='True' and r['nominal_cost_supported']=='True'
                if hit:
                    ax.scatter(float(r['first_work']),j+offset,s=23,edgecolor=color,
                               facecolor=color if supported else 'white',linewidth=.9,zorder=3)
                else:ax.scatter(45,j+offset,s=23,marker='x',color=color,linewidth=.9,zorder=3)
        ax.set_xscale('log');ax.set_xlim(.08,70);ax.set_xticks([.1,1,4,16,45],['0.1','1','4','16','sin\nllegada'])
        ax.tick_params(axis='x',labelsize=7);ax.grid(axis='x',alpha=.2);ax.axvline(25,linestyle=':',color='.7')
        ax.set_title(instance.replace('instance','Caso '));ax.set_xlabel('Trabajo del solver hasta el objetivo')
        ax.spines[['top','right']].set_visible(False)
    axes[0].set_yticks(range(len(POLICIES)),[LABELS[p] for p in POLICIES]);axes[0].invert_yaxis()
    fig.text(.5,.01,'Cada punto es una semilla. Lleno: respaldo racional del patrón/costo; vacío: solo llegada numérica. ×: sin llegada al terminar.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(HERE/'work-to-target.pdf',metadata={'CreationDate':None,'ModDate':None});fig.savefig(HERE/'work-to-target.png',dpi=180);plt.close(fig)


def main():
    a=read(HERE/'analysis.json');d=read(HERE/'design.json');v=read(HERE/'independent-verification.json')
    rows=list(csv.DictReader((HERE/'first-hits.csv').open()));figure(rows,d['instances'],d['seeds'])
    gs={(g['instance'],g['policy'],g['scenario']):g for g in a['groups']}
    table='| Caso | Política | Llegadas exigentes | Respaldadas | Trabajo mediano de las llegadas |\n|---|---|---:|---:|---:|\n'
    for instance in d['instances']:
        for policy in POLICIES:
            g=gs[instance,policy,'Demanding']
            table+=f"| {instance} | {LABELS[policy]} | {g['numeric_hits']}/3 | {g['exact_supported_hits']}/3 | {fmt(g['median_work_on_hits'])} |\n"
    comparison='| Caso | Escenario | Contrato llega | Contrato supera todos los controles | Con respaldo racional |\n|---|---|---:|---:|---:|\n'
    comptex=[]
    for instance in d['instances']:
        for scenario in ['Demanding','Reference','Permissive']:
            c=[r for r in a['matched_comparisons'] if r['instance']==instance and r['scenario']==scenario]
            cells=[sum(r['budget_hit'] for r in c),sum(r['budget_faster_than_every_control'] for r in c),sum(r['budget_supported_faster'] for r in c)]
            comparison+=f"| {instance} | {scenario} | "+' | '.join(f'{x}/3' for x in cells)+' |\n'
            comptex.append(instance.replace('instance','')+' & '+{'Demanding':'Exigente','Reference':'Referencia','Permissive':'Permisivo'}[scenario]+' & '+' & '.join(f'{x}/3' for x in cells)+r' \\')
    bfast=sum(r['budget_faster_than_every_control'] for r in a['matched_comparisons'])
    supportedfast=sum(r['budget_supported_faster'] for r in a['matched_comparisons'])
    prec_only=sum(r['precision_only_hit']=='True' and r['numeric_hit']!='True' for r in rows)
    case001ratio=median(r['budget_over_best_control_work_ratio'] for r in a['matched_comparisons'] if r['instance']=='instance001' and r['scenario']=='Demanding')
    if supportedfast:
        decision=f"Hay una señal acotada: el contrato correspondiente al escenario agrega la llegada más temprana respaldada en {supportedfast}/27 comparaciones modelo/semilla/precisión. No equivale a superioridad general; revisar la tabla por modelo y la dependencia de precisión antes de decidir transferencia. OMS permanece sin cambios."
    else:
        decision="No se observa una llegada más temprana respaldada del contrato frente al conjunto de controles competitivos en estas 27 comparaciones. Este banco no justifica ampliar OMS; se conserva el resultado negativo y se cierra esta prueba."
    if a['arms_with_identical_first_hits_across_precision_scenarios']==a['arms']:
        decision=("Con cada política fija, cambiar solo el presupuesto de aceptación no cambia ninguna primera llegada. "
                  "La calidad del objetivo determina la entrega. Recalcular factores con otro presupuesto sí puede cambiar la búsqueda. El contrato exigente gana al conjunto de controles en "
                  f"{supportedfast}/27 comparaciones, concentradas en un modelo, y pierde en otros. "
                  "No aparece una ventaja general ni un intercambio práctico precisión/trabajo; OMS permanece sin cambios.")
    targets='| Caso | Testigo racional previo U | Umbral común Ccap |\n|---|---:|---:|\n'
    for i,r in d['references'].items():targets+=f"| {i} | {float(Q(r['objective_exact'])):.6f} | {float(Q(r['objective_cap_exact'])):.6f} |\n"
    text=f'''# Frontera precisión–trabajo con calidad común

**{decision}**

## Diseño ejecutado

Tres modelos SG-Ter-Mer de 360 períodos y enteros originales: 001,022,046,
posiciones 1,3,6 del banco físico limpio anterior. Son modelos conocidos,
seleccionados antes de estas corridas; el ensayo es prospectivo en semillas y
parámetros, no validación de generalización a otros modelos. Se mantienen
Base.lp y su interpretación binary64; no se usa el ejecutable del generador.

{a['arms']} brazos, **{a['native_mip_calls']} MILP reales** después de deduplicar,
semillas 401/409/419. Gurobi 13.0.2, cuatro hilos, presolve y escalado internos
automáticos, IntegralityFocus=1, tolerancia entera común 1e-9, primal 1e-6 salvo
Tight (1e-9), gap .1 %, 15 s / 16 unidades de trabajo. Corridas secuenciales.
Se conservan **{a['candidate_events']} eventos de candidatos**, incluidos MIPSOL
que no mejoran el incumbente y puntos finales. Un parámetro nominal no garantiza
el residuo de la fila exportada ni la precisión original observada.

GM, Ruiz y L2 son diádicos y tienen la misma ventana [1e-9,1e9], sin banda
identidad ni escalado de columnas. Budget usa el mismo candidato L2 e impone
epsilon/alpha+E<=delta, reservando E=gamma sum_enteros|aij|. Se comprobaron
exactamente todos los productos coeficiente/RHS; el error de exportación es cero.
El escenario exigente cambia 1440 activaciones por modelo. Referencia y permisivo
coinciden con L2; no se repiten las resoluciones. GCD examina 1080 filas por
modelo, todas ya primitivas y con RHS entero: coincide con Base. Nunca se aplica
piso del RHS en filas con variables continuas.

## Objetivo y precisión común

{targets}
Se adquirió cada testigo antes de los MILP mediante un LP racional con el patrón
de un testigo GM anterior, verificando todas las filas/cotas del Base original.
U es una referencia factible, no un óptimo. Ccap=U+.01 max(1,|U|) es una aspiración
común con información offline; no es un gap certificado y esos puntos nunca se
utilizan como Start. La adquisición costó
{sum(r['acquisition_seconds'] for r in d['references'].values()):.3f} s en total, fuera
de las fronteras nativas. No se obtiene gratuitamente en un algoritmo general.

Las precisiones autorizadas son (MW,m3): exigente (.01,100), referencia (.1,1000)
y permisiva (1,10000). Se comprueban después de redondear los enteros, sobre
potencia, envolventes, balances y activaciones de volumen, con conversión de
unidades por fila. Son objetivos numéricos del estudio, no estándares del operador.
Otras filas tienen presupuesto auxiliar 1e-8 max(1,|RHS|); cotas, 1e-6 absoluto.
Estos últimos criterios se declaran, no se presentan como validación física.

**Resultado central:** en {a['arms_with_identical_first_hits_across_precision_scenarios']}/{a['arms']}
brazos, las primeras llegadas son idénticas para las tres precisiones (o faltan
en las tres), **manteniendo fija la política y sus factores**. La envolvente
del mismo conjunto de políticas coincide sobre esta grilla de aceptación.
La falta de calidad, no una precisión física insuficiente, discrimina las
entregas en esta prueba. No se extrapola a presupuestos no ensayados.

Esto no significa que la política contractual sea insensible al presupuesto.
Al recalcular factores, Budget-Demanding puede llegar donde Budget-Reference y
Budget-Permissive no llegan: las últimas coinciden con L2. En 001 el exigente
llega 3/3 y los otros dos 0/3. La selección contractual cambia la búsqueda aun
cuando los puntos disponibles ya pasan las precisiones físicas. No se afirma
monotonía del rendimiento al variar el presupuesto que diseña el escalamiento.

Primera llegada: candidato que pasa todos esos controles y tiene C<=Ccap.
Todos los residuos y costos se evalúan exactamente. Se emplea una acumulación
entera de los datos diádicos, comprobada por un segundo algoritmo de exponentes
por fila y un parser independiente de Base.lp. Alinear exponentes no se presenta
como novedad matemática. Se detectaron {prec_only} asignaciones brazo/escenario
con precisión alcanzada pero sin calidad común al terminar; son observaciones
correlacionadas por reutilización, no una tasa poblacional de fallos.

## Trabajo hasta obtener precisión y calidad

![Trabajo al objetivo exigente](work-to-target.png)

{table}
La mediana solo incluye llegadas y debe leerse junto a su denominador. No se
imputa un tiempo corto al fracaso ni se denomina aceleración a una parada temprana
con peor costo. Una cruz en la figura significa sin llegada al terminar; su
posición a la derecha es una categoría, no trabajo realmente consumido.

{comparison}
La política contractual se corresponde con la precisión pedida. Se compara con
el mejor de Base, Tight, GM, Ruiz, L2 y L2-NumericFocus para el mismo modelo,
semilla y objetivo. Ese mejor control es una envolvente retrospectiva, no un
selector gratuito. Ganar esa comparación es evidencia fuerte dentro de esta
muestra; perderla no identifica un control único que gane siempre. Hay {bfast}
llegadas contractuales numéricamente más tempranas y {supportedfast} respaldadas.
Referencia/permisivo repiten L2 y no se cuentan como experimentos independientes.
En 001, la razón emparejada mediana Budget/GM es {case001ratio:.4f}, aproximadamente
{100*(1-case001ratio):.1f} % menos trabajo. En 046, GM tiene 3/3 llegadas frente
a 2/3 de Budget, con menor trabajo en las llegadas comparables. Estas diferencias
se conservan aunque no produzcan una ventaja general del contrato.

## Respaldo exacto y costo de la verificación

Se intentó un LP por patrón entero único de las primeras llegadas, sin reemplazar
un patrón que fallara por otro favorable. Son **{a['unique_posthoc_patterns']} patrones**;
{a['posthoc_native_lp_calls']} llamadas SoPlex y estados {a['exact_pattern_counts']}.
El costo de construcción, resolución y comprobación fue
{a['posthoc_acquisition_total_seconds']:.3f} s, fuera del trabajo MILP. Un testigo
del mismo patrón debe tener U<=Ccap y además U<=C+.01 max(1,|U|). Esto respalda
existencia de una continuación y fidelidad unilateral de costo; no certifica
factibilidad exacta del vector flotante original ni óptimo MILP.

Las cotas reportadas se contrastan también con el testigo factible previo:
{len(a['bound_contradictions_against_prior_exact_reference'])} llamadas nativas tienen
una cota que lo excede. La ausencia de contradicción no valida las otras cotas.
No se usa una cota no certificada para declarar calidad común.

La selección se ejecutó y midió de nuevo en cada brazo. Primera llegada se
evalúa retrospectivamente; el callback no detuvo ni modificó el MILP. El costo
de captura (mediana {a['median_capture_seconds']:.4f} s por llamada) entra en el tiempo
del optimizador. Selección, construcción, persistencia, comprobación y LP exactos
se registran por separado. Un menor trabajo nativo no prueba menor tiempo total
de un controlador online, que no se ha ensayado aquí. No se agregan tiempos de
modelos distintos para proclamar una aceleración.

## Decisión y límites

{decision}

Son tres modelos de una familia y tres semillas; no un muestreo aleatorio. Las
relaciones no se extrapolan a otro solver. El conjunto ensayado define una
frontera empírica, no el menor trabajo posible entre todos los algoritmos.
Las diferencias de residuos muy inferiores al escenario exigente no representan
por sí solas una utilidad adicional. Este estudio tampoco resuelve LP–DW ni los
límites conjuntos del escalamiento por filas.

Fuentes primarias: [callbacks MIPSOL de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/callbacks.html),
[parámetros numéricos](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/numeric_parameters.html)
y [SoPlex exacto](https://soplex.zib.de/doc/html/EXACT.php). El modo de callbacks
puede entregar candidatos que no mejoran el incumbente; por eso se conservan todos.

README.md contiene el replay y las limitaciones. El manifiesto del paquete
incluye entradas, candidatos, secuencias, parámetros, certificados y resultados.
Los ocho paquetes previos y la entrega OMS permanecen protegidos por SHA256.

Nota de importación: el LP usa cotas 1e20 como sentinelas. La API las interpreta
como infinitas, conforme a [Gurobi: atributos de variables](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html).
El parser independiente aplica esa semántica y comprueba además las cotas finitas
literales en todos los candidatos y testigos; no hay que confundir esa normalización
documentada con una modificación contractual. Los modelos canónicos y sus hashes
quedaron fijados antes del primer MILP.
'''
    (HERE/'RESULTADOS.md').write_text(text)
    latex=r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage[spanish]{babel}
\usepackage[margin=2cm]{geometry}\usepackage{graphicx,booktabs,hyperref,amsmath}
\hypersetup{colorlinks=true,urlcolor=blue}\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\begin{document}
\begin{center}{\Large Precisión y trabajo con calidad común}\\[4pt]Exploración OMS, 15 de octubre de 2026\end{center}
\textbf{Resultado.} DECISION

\textbf{Pregunta.} Medir cuánto trabajo hace falta para alcanzar simultáneamente
un presupuesto de precisión y un costo comparable, frente a controles fuertes.
Una parada rápida con costo inaceptable no es una mejora.

\textbf{Diseño.} Tres modelos SG--Ter--Mer de 360 períodos e integralidad
original: 001,022,046, posiciones 1,3,6 del banco limpio anterior. Son conocidos,
no validación en modelos nuevos. ARMS brazos; MIPS llamadas MILP reales tras
deduplicar; semillas 401,409,419. Gurobi 13.0.2, cuatro hilos, presolve y escalado
internos automáticos, IntegralityFocus=1, tolerancia entera común 1e-9, primal
1e-6 (Tight: 1e-9), gap 0.1\%, 15 s/16 unidades de trabajo. Resoluciones
secuenciales, sin starts, desde los Base.lp archivados. No se usa ni cambia el
generador. Se guardan EVENTS candidatos, incluidos los que no mejoran incumbente.

GM, Ruiz y L2 usan potencias de dos dentro de [1e-9,1e9], sin banda identidad.
Todos los productos son exactamente proporcionales; no hay escalado de columnas.
Budget aplica el mismo candidato L2 y exige $\epsilon/\alpha+E\leq\delta$, con
$E=10^{-9}\sum_{j\text{ entero}}|a_{ij}|$. El exigente cambia 1440 factores
de activación por modelo. Referencia/permisivo coinciden con L2. GCD examina
1080 filas enteras por modelo, ya primitivas: coincide con Base; no se aplica
redondeo del RHS a filas con variables continuas.

\textbf{Calidad y precisión.} Se obtiene antes un testigo racional factible por
modelo mediante LP de un patrón conocido, verificando Base. No es un óptimo.
La aspiración común es $C\leq U_{ref}+.01\max(1,|U_{ref}|)$, con referencia
offline declarada, nunca suministrada como Start. Presupuestos (MW,m$^3$):
(.01,100), (.1,1000), (1,10000); objetivos numéricos, no estándares operativos.
Incluyen potencia, envolventes, balances y activaciones, con sus unidades.
Se redondean enteros y se comprueban todas las filas: las otras tienen criterio
auxiliar $10^{-8}\max(1,|b_i|)$; cotas, $10^{-6}$. Costos y residuos se evalúan
exactamente. Alinear denominadores dyádicos para usar enteros no se reclama novedoso.

\newpage
\textbf{Trabajo hasta la precisión exigente y calidad común.}
\begin{center}\includegraphics[width=\textwidth]{work-to-target.pdf}\end{center}
Cada punto es una semilla; lleno: respaldo racional del patrón/costo; vacío:
solo llegada numérica. Una cruz significa que no hubo llegada al terminar y su
posición es categórica: no implica haber consumido ese trabajo. Las medianas y
todos los estados/costos figuran en RESULTADOS.md y los CSV.

\begin{center}\small\begin{tabular}{llrrr}\toprule
Caso & Precisión & Llega & Gana controles & Con respaldo\\\midrule
COMPARISON
\bottomrule\end{tabular}\end{center}
La política Budget corresponde a la precisión solicitada. Ganar significa menor
trabajo que todos Base, Tight, GM, Ruiz, L2 y L2-NumericFocus del mismo caso y
semilla. El mejor control es una envolvente retrospectiva, no un selector
operativo gratuito. Referencia/permisivo reutilizan L2.

\newpage
\textbf{Respaldo posterior.} Se toma la primera llegada de cada brazo/escenario,
se deduplica por patrón y se intenta un LP racional original por patrón,
sin reemplazar resultados adversos. PATTERNS patrones; EXACTCALLS llamadas LP
posteriores. Un primal exacto del mismo patrón con $U\leq C_{cap}$ respalda la
calidad; además se exige $U\leq C+.01\max(1,|U|)$ para respaldar el costo nominal.
No es factibilidad exacta del punto flotante original ni óptimo global MILP.
Los desconocidos permanecen como tales. El replay comprueba referencias,
testigos y los residuos mediante un algoritmo independiente de exponentes por
fila y un parser completo de los Base.lp originales.

FLAGS cotas inferiores nativas exceden un testigo factible previo. Se
conservan esas contradicciones. No se valida una cota por no refutarla y no se
usa el gap reportado como prueba del objetivo común.

\textbf{Costo.} La adquisición de referencias es offline y el respaldo posterior
también está fuera de la frontera nativa. La selección se ejecutó y midió por
corrida; se registran construcción, captura, optimización, persistencia y
verificación. Primera llegada se mide retrospectivamente, sin detener ni
alterar el solver. Menor trabajo nativo no implica menor tiempo de un controlador
online, no evaluado aquí. No se suman tiempos de distintos problemas como si
midieran una aceleración a calidad fija.

\textbf{Decisión.} DECISION

Tres modelos de una familia y tres semillas no prueban generalidad ni efectos
en otro solver. Diferencias de residuos muy inferiores a lo solicitado no
aportan utilidad por sí solas. Los ocho paquetes previos y OMS v1.3.5 se
preservan por SHA256. El diagnóstico LP--DW y los límites conjuntos del
escalamiento siguen pendientes.

\textbf{Fuentes y reproducción.} README.md, PROTOCOL.md, registros originales,
certificados y manifiesto acompañan esta nota. El replay no llama a solvers;
las corridas nuevas requieren Gurobi y los certificados, SoPlex/GMP.
Documentación primaria: \href{https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/callbacks.html}{callbacks MIPSOL de Gurobi},
\href{https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/numeric_parameters.html}{parámetros numéricos}
y \href{https://soplex.zib.de/doc/html/EXACT.php}{SoPlex exacto}.
\end{document}
'''
    replace={'DECISION':decision.replace('%',r'\%'),'ARMS':a['arms'],'MIPS':a['native_mip_calls'],'EVENTS':a['candidate_events'],
             'COMPARISON':'\n'.join(comptex),'PATTERNS':a['unique_posthoc_patterns'],'EXACTCALLS':a['posthoc_native_lp_calls'],
             'FLAGS':len(a['bound_contradictions_against_prior_exact_reference'])}
    for k,val in replace.items():latex=latex.replace(k,str(val))
    (HERE/'precision-work-note.tex').write_text(latex)


if __name__=='__main__':main()
