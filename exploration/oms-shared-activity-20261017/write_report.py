"""Build a separate scientific note only from fully replayed completed results."""
import collections
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    follow=HERE/'centered-followup';validation=json.loads((follow/'VALIDATION.json').read_text())
    assert validation['all_complete'] and not validation['failed_processes']
    result=json.loads((follow/'SUMMARY.json').read_text());assert result['complete']
    rows=json.loads((follow/'RESULTS.json').read_text());groups=collections.defaultdict(list)
    for r in rows:groups[(r['policy'],r['budget_label'])].append(r)
    policies=('Coefficient-SOS','Tight-coefficient-SOS','Unconstrained-shared','Centered-individual',
              'Centered-shared','Minimum-shared','Indicator-budget','Tight-raw')
    table=[]
    for policy in policies:
        values=[]
        for budget in ('1e-04','1e-06','1e-08'):
            own=groups[(policy,budget)];assert len(own)==15
            values.append(f"{sum(bool(x.get('primal_pass')) for x in own)}/15; {sum(bool(x.get('quality_target_met')) for x in own)}/15")
        table.append(policy+' & '+' & '.join(values)+r' \\')
    comparisons=[]
    for p in result['paired']:
        if p['budget']!='1e-06' or p['baseline']!='Tight-raw':continue
        w=p['work_geometric_ratio_on_both_quality'];t=p['cycle_geometric_ratio_on_both_quality']
        comparisons.append(p['name'].replace('_',r'\_')+f" & {p['proposal_primal_pass']}/3 & {p['baseline_primal_pass']}/3 & {p['both_quality_pairs']} & "+
                           ('--' if w is None else f'{w:.3f}')+' & '+('--' if t is None else f'{t:.3f}')+r' \\')
    native=json.loads((HERE/'VALIDATION.json').read_text())
    interpretation=(HERE/'INTERPRETACION.md').read_text()
    # The interpretation is retained as Markdown; the note contains a conservative
    # data-independent scope statement and full tables for assessment.
    source=r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-nodecimaldot]{babel}
\usepackage{amsmath,amssymb,booktabs,array}
\usepackage[colorlinks=true,urlcolor=blue,linkcolor=blue]{hyperref}
\title{Selección de escalas para actividades MILP\ sujetas a presupuestos de precisión}
\author{Nota de investigación separada del envío OMS}
\date{17 de octubre de 2026}
\begin{document}\maketitle
\noindent\textbf{Estado.} Se implementaron y contrastaron dos reglas de selección:
radio mínimo y mejor centrado dentro del conjunto admisible. El estudio conserva
195 ejecuciones válidas primarias y 360 procesos nuevos de seguimiento, incluidos
resultados adversos. El manuscrito OMS v1.3.14 permanece sin cambios. Las pruebas
no acreditan prioridad bibliográfica de la construcción completa.

\section{Pregunta y antecedentes}
Para un bloque $g_i(x_C)\le M_i z$, con $z$ binaria y $M_i>0$, el contrato
uniforme de una fila contiene $M_i\gamma_z$, independiente del factor de fila.
Si $\delta_i\le M_i\gamma_z$, ese contrato es imposible. Se investiga si una
representación extendida permite seleccionar escalas que respeten precisión y
mejoren la entrega verificada frente a controles adecuados.

Una implicación mediante holgura y SOS1 es conocida; SCIP también implementa
normalización por coeficientes y holguras compartidas.\footnote{\url{https://scipopt.org/doc-10.0.2/html/cons__indicator_8c_source.php}}
Gurobi documenta tolerancias absolutas, fugas big-M y el posible costo adicional
de SOS/indicadores.\footnote{\url{https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html}}
La investigación no reclama novedad por esos ingredientes. La parte candidata
es caracterizar el conjunto de escalas compatible simultáneamente con precisión,
ventanas y representación exacta, y seleccionar dentro de él sin un optimizador.

\section{Representación y transferencia condicional}
Se introduce $y\in[0,R]$, $w\in[0,1]$, $w+z=1$, SOS1$(w,y)$ y
\[
 g_i(x_C)-h_i y\le0,\qquad h_i=M_i/R.
\]
La proyección MILP coincide con la original. Si $z=0$, $y=0$. Si $z=1$,
elegir $y=\max(0,\max_i g_i/h_i)\le R$.
La envolvente convexa de $(z,y)$ es $0\le y\le Rz$. Ignorar SOS en un LP
no equivale a imponer esa envolvente ni demuestra igual comportamiento de raíz.

Supóngase que $\operatorname{round}(z)\in\{0,1\}$,
$|w+z-1|\le\varepsilon_c$, $1/2-\varepsilon_c>\gamma_s$,
SOS1 tiene a lo sumo un miembro con módulo mayor que $\gamma_s$,
el residuo de cada enlace exportado es como máximo $\varepsilon$ y
$y\le R+\tau$. Entonces, con $T=\max(\gamma_s,\tau)$,
\[
 v_i(x_C,\operatorname{round}(z))\le
 \varepsilon/\alpha_i+(M_i/R)T.
\]
En efecto, si se redondea a cero, $w\ge1/2-\varepsilon_c>\gamma_s$ y
$|y|\le\gamma_s$. Si se redondea a uno, se utiliza la cota superior de $y$.
No se requiere una hipótesis de distancia de $z$ a entero. Las demás filas,
cotas y dominios se verifican por separado. Los parámetros nominales no
aseguran estas hipótesis en la solución devuelta.

\section{Selección exacta y mejor centrado}
Se toman $R=2^r$, $\alpha_i=2^{u_i}$ y datos interpretados como racionales
binary64 almacenados. Para cada coeficiente $a\ne0$, sean
$[s_-(a),s_+(a)]$ los desplazamientos que producen un binary64 finito exacto.
Con $m_i=\min|g_{ij}|$, $H_i=\max|g_{ij}|$, ventana $[\ell,U]$, definir
\begin{align*}
A_i&=\min(\lfloor\log_2(U/H_i)\rfloor,\min_j s_+(g_{ij}),1023),\\
C_i&=\max(\lceil\log_2(\ell/m_i)\rceil,\max_j s_-(g_{ij}),-1074),\\
B_i&=\min(\lfloor\log_2(U/M_i)\rfloor,s_+(M_i)),\\
D_i&=\max(\lceil\log_2(\ell/M_i)\rceil,s_-(M_i)).
\end{align*}
Las condiciones de la fila son exactamente
$\max(C_i,r+D_i)\le u_i\le\min(A_i,r+B_i)$.
Sean $P_i=\varepsilon2^{-A_i}$ y $Q_i=\varepsilon2^{-B_i}$.
Si $A_i<C_i$, $B_i<D_i$ o $\delta_i\le P_i$, no hay representación.
En otro caso el intervalo exacto de radios es
\begin{align*}
r_i^- =\max\{&-1074,-s_+(M_i),C_i-B_i,
\lceil\log_2(M_iT/(\delta_i-P_i))\rceil,\\
&\lceil\log_2((Q_i+M_iT)/\delta_i)\rceil\},\\
r_i^+ =\min\{&1023,\lfloor\log_2(\mathrm{cap})\rfloor,-s_-(M_i),A_i-D_i\}.
\end{align*}
Se obtiene utilizando el mayor exponente admisible
$u_i=\min(A_i,r+B_i)$ para decidir factibilidad de precisión. La cota mínima
es $\max(P_i+M_iT2^{-r},(Q_i+M_iT)2^{-r})$.
Un bloque compartido es admisible si y solo si
$r_-:=\max_i r_i^-\le r_+:=\min_i r_i^+$.
El cálculo recorre coeficientes y filas; no busca radios ni llama a un solver.
El conteo de operaciones no supone aritmética racional de costo constante.

La regla primaria elige $r_-$. El seguimiento define
$q_i=M_i^2/\|g_i\|_2^2$ y minimiza sobre el intervalo entero
\[
 F(r)=\max(q_{\max}2^{-2r},2^{2r}/q_{\min}).
\]
Un término decrece y otro crece, por lo que basta comparar los dos enteros
que rodean $\log_2(q_{\min}q_{\max})/4$, truncados a $[r_-,r_+]$.
Se comparan racionalmente y se rompe el empate hacia menor $r$.
Es un óptimo de centrado relativo, no del trabajo computacional.

Las conversiones coherentes $g_i,M_i,\delta_i\mapsto2^{k_i}(g_i,M_i,\delta_i)$
conservan $q_i$, el radio y los coeficientes exportados si la conversión y su
inversa preservan las representaciones admisibles relevantes. No basta conservar
solo el minimizador anterior; véase \texttt{COVARIANCE\_SCOPE.md}. No se afirma
invariancia global en desbordamientos ni para conversiones decimales inexactas.

\paragraph{Ejemplo algebraico, sin optimizar.}
Para $100x\le10^8z$, $\delta=10^{-4}$, $\varepsilon=10^{-6}$,
$\gamma_s=10^{-5}$, la regla centrada libre elige $r=20$; la contractual,
$r=24$, $h=5.9604644775390625$, $\alpha=1/32$, con cota menor que $10^{-4}$.
La reserva original $M\gamma_z$ es aproximadamente $1000$.
Esto demuestra extensión de un tipo de garantía condicional, no una ventaja
computacional ni cumplimiento incondicional del optimizador.

\section{Evaluación prospectiva}
Cinco modelos fijos: control30 y cinca son conocidos; neos-1112787 proviene
de una exploración anterior; beasleyC3 y k16x240b son dos modelos nuevos de
redes con costos fijos. Los dos neos conservan clasificación de aplicación
desconocida. No hay cinco familias independientes. La contracción certificada
de cinca es común a todos los controles y se reproduce racionalmente.

La primaria usa cinco cambios de unidad, tres semillas y aliases fijados por
bytes/parámetros: 225 asignaciones, 65 exportaciones distintas y 195 ejecuciones
válidas. Son representaciones, no nuevas instancias. Una escritura truncada
se conserva y se repitió una vez; no es una observación independiente.
El radio mínimo no muestra superioridad general: control30 falla precisión
redondeada en 3/3; Tight-raw pasa 3/3. Se verifican @HYP@ hipótesis de
actividad y @TRANSFER@ transferencias válidas, conservando todos los fallos.

El seguimiento fija antes de resolver ocho políticas, tres presupuestos
algebraicos de activación y tres semillas nuevas: 360 procesos completos.
Los presupuestos son sensibilidad numérica y no estándares físicos.
Gurobi 13.0.2, cuatro hilos, presolve/escalado interno automáticos,
PreSOS1BigM=0, WorkLimit=5, TimeLimit=30 s, gap nominal 1\%.
$\varepsilon=10^{-6}$, $\gamma_s=10^{-5}$, salvo controles Tight con ambos
en $10^{-9}$. Los estados nativos no certifican optimalidad global.

Precisión exige todas las filas, cotas y dominios tras redondear todos los
enteros originales. Calidad exige además objetivo original dentro del margen
del 1\% de la referencia fijada previamente, que no siempre es óptimo certificado.
La verificación de puntos usa racionales sin solver. La comprobación revisa
@POINTS@ puntos del seguimiento y @ROWS@ filas fuente en 120 variantes.

\begin{table}[ht]\centering\small
\caption{Precisión y calidad, en ese orden. Cada entrada tiene denominador 15:
cinco modelos y tres semillas. Los presupuestos no son aplicaciones distintas.}
\begin{tabular}{lccc}\toprule
Política & $10^{-4}$ & $10^{-6}$ & $10^{-8}$\\\midrule
@TABLE@
\bottomrule\end{tabular}\end{table}

Las políticas con bytes y parámetros coincidentes se identifican explícitamente;
sus llamadas reales no prueban diferencias entre métodos. El tiempo exterior
incluye inicio de Python, lectura de JSON, selección, exportación, cotejo nativo,
solve, verificación y persistencia. Excluye descarga, FBBT común y generador C++.
La máquina es compartida; el orden es aleatorio y la carga queda registrada.

\begin{table}[ht]\centering\small
\caption{Propuesta Centered-shared frente a Tight-raw a $10^{-6}$.
W/T son medias geométricas emparejadas solo donde ambos alcanzan calidad;
se deben leer junto al denominador N y las entregas. No son aceleraciones generales.}
\begin{tabular}{lrrrrr}\toprule
Modelo & Prec. prop. & Prec. Tight & N & W & T\\\midrule
@PAIRS@
\bottomrule\end{tabular}\end{table}

\section{Alcance de las conclusiones}
\textbf{La evidencia no justifica incorporar el candidato como un método con
ventaja práctica en OMS.} Centered-shared cumple precisión en 33/45 y además
calidad en 17/45; Tight-raw obtiene 44/45 y 33/45, respectivamente.
Individualizar las actividades tampoco recupera una ventaja general.
Los contratos admiten representaciones que el contrato uniforme por filas
rechaza. Eso se demuestra algebraicamente. Su utilidad frente a una
normalización ya conocida se debe juzgar con soluciones efectivas, calidad
comparable y costo completo. Invariancia y mejor centrado, aislados, no bastan.
La inspección nativa detecta cambios de coeficientes/cotas de actividades durante
presolve y algunos puntos incumplen soporte SOS. Son observaciones; no
identifican completamente un mecanismo causal ni validan cotas duales.

En cinca, la propuesta cumple precisión en 3/3 a $10^{-4}$ y 3/3 a $10^{-8}$,
pero falla 3/3 a $10^{-6}$. En la semilla 199, una activación viola
0.015642202283948508, unas 15642 veces su presupuesto de $10^{-6}$;
su hipótesis SOS falla. El ejemplo compacto retrospectivo se comprueba con
\texttt{check\_nonmonotonicity.py}, sin solver ni NumPy.

La interpretación específica de los resultados queda en \texttt{INTERPRETACION.md};
los datos completos, incluidos casos adversos, en CSV/JSON. No se incorpora esta
investigación como tercera contribución del paper por el mero hecho de ejecutar
más experimentos. Una ausencia de contradicciones tampoco certifica optimalidad.

\paragraph{Reproducción.} \texttt{README.md} enumera las comprobaciones independientes.
Los protocolos, diseños previos, programas, MPS de origen, exportaciones, puntos,
logs, tiempos, intentos interrumpidos y manifiesto de integridad se preservan.
Las verificaciones de soluciones no necesitan licencia comercial.
\end{document}
'''
    source=source.replace('@TABLE@','\n'.join(table)).replace('@PAIRS@','\n'.join(comparisons))
    source=source.replace('@HYP@',str(native['returned_activity_hypotheses_checked'])).replace('@TRANSFER@',str(native['valid_conditional_row_transfers']))
    source=source.replace('@POINTS@',str(validation['points_rechecked'])).replace('@ROWS@',str(validation['source_rows_checked']))
    (HERE/'research-note.tex').write_text(source)
    print(json.dumps({'source':'research-note.tex','points':validation['points_rechecked'],'complete':True}))


if __name__=='__main__':main()
