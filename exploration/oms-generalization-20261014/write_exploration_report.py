#!/usr/bin/env python3
"""Write a separate working note and PDF source from verified pilot records."""
import csv
from fractions import Fraction
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    design=json.loads((HERE/'pilot/design.json').read_text())
    verification=json.loads((HERE/'pilot/independent-verification.json').read_text())
    rows=list(csv.DictReader((HERE/'pilot/verified-runs.csv').open()))
    lookup={(r['model'],r['solver'],r['policy']):r for r in rows}
    policies=['Base','Dyadic-GM','Dyadic-L2','Budget-dyadic-L2','Dyadic-L2-tight','Dyadic-L2-NumericFocus3']
    def status(row):
        if row is None:return '--'
        if 'abstention' in row['outcome']:return 'A'
        if row['outcome']=='import_or_execution_failure':return 'I'
        return 'V' if row['primal_accepted']=='True' else 'F'
    table=[];latex=[]
    for item in design['models']:
        for solver in design['solvers']:
            outcomes=[status(lookup.get((item['name'],solver,p))) for p in policies]
            table.append('| '+item['name']+' | '+solver+' | '+' | '.join(outcomes)+' |')
            latex.append(item['name'].replace('-','{-}')+' & '+solver+' & '+' & '.join(outcomes)+r'\\')
    cost=[];costlatex=[]
    for name in ('Kondili-H10','Kondili-H12'):
        for solver in ('gurobi','highs'):
            a=lookup[name,solver,'Dyadic-L2'];b=lookup[name,solver,'Budget-dyadic-L2']
            work_a=f"{float(a['work']):.5f}" if a['work'] else '--'
            work_b=f"{float(b['work']):.5f}" if b['work'] else '--'
            line=f"{name} | {solver} | {float(a['optimizer_seconds']):.4f} | {float(b['optimizer_seconds']):.4f} | {work_a} | {work_b}"
            cost.append('| '+line+' |')
            costlatex.append(name+' & '+solver+f" & {float(a['optimizer_seconds']):.4f} & {float(b['optimizer_seconds']):.4f} & {work_a} & {work_b}"+r'\\')
    source = '''# Resultados preliminares y decisión de alcance

**Conclusión:** el procedimiento se pudo trasladar a fuentes independientes, pero
este piloto no demuestra una ventaja de aceptación primal de Budget-L2 frente a
su control o a las alternativas existentes. No se incorpora al artículo actual.
El aporte tangible por ahora es un prototipo de aceptación/abstención comprobado,
certificados de incompatibilidad y evidencia que limita el uso predictivo del diagnóstico.

Se conservaron 55 brazos, incluidos dos que se abstienen por incompatibilidad y
uno que falla al importar. Se resolvieron 52 brazos y se guardaron sus puntos.
Un checker separado, sin importar el runner ni ningún solver, verifica esos 52
puntos con aritmética racional: 41 cumplen los presupuestos después de redondear
enteros y 42 antes. Estas cuentas mezclan configuraciones deliberadamente distintas
y no son tasas poblacionales ni un ranking de métodos. Todo es piloto, semilla 17.

## Portabilidad a producción por lotes

El generador STN-Scheduler y los datos originales de Kondili son independientes
del despacho hidrotérmico. H=10 tiene 409 filas efectivas y 321 variables; H=12,
483 filas y 379 variables. Los contratos cambian exactamente 88 y 104 factores
de filas de capacidad. El objetivo de precisión es 1e-5 kg (10 mg), elegido para
el estudio; no es una exigencia de una planta. Todas las políticas y ambos solvers
cumplen el presupuesto en ambos modelos. Modificar factores no equivale a obtener
una mejora práctica cuando el control ya cumple la precisión.

## MIPLIB y controles

Los tres modelos se eligieron por criterios fijados antes de resolver: tag Numerics,
mezcla de variables continuas y enteras, dimensiones acotadas y primeros tres grupos
distintos al ordenar por no ceros y nombre. Los presupuestos son numéricos algebraicos,
no físicos. Se conserva la discrepancia entre la ficha y los no ceros del MPS de cinca.

V = asignación entera verificada dentro de los presupuestos de todas las filas y cotas;
F = existe punto, pero falla esa comprobación; A = abstención por incompatibilidad;
I = fallo de importación; -- = parámetro no disponible. V no significa factibilidad
exacta ni optimalidad. Los métodos escalados son variantes diádicas exactas: el control
L2 y Budget comparten kernel, cotas de coeficientes y, en STN, tolerancia entera.

| Modelo | Solver | Base | GM | L2 | Budget-L2 | L2-tight | NumericFocus 3 |
|---|---|---|---|---|---|---|---|
'''+ '\n'.join(table)+'''

En `control30-3-2-3`, Budget-L2 reduce el máximo residuo/presupuesto del punto
crudo Gurobi de 26.526 (L2) a 0,302; sin embargo, el punto redondeado sigue
fallando, con ratio 146.563. Base y GM también cumplían el presupuesto crudo.
No es una recuperación de una asignación entera verificada ni superioridad sobre
las alternativas. Las seis variantes Gurobi fallan el chequeo redondeado en este
piloto. HiGHS devuelve puntos que lo superan, pero alcanza el límite de 15 s en
todas las variantes: hay precisión primal, no una certificación de optimalidad.

En `neos-3421095-cinca`, 96 intervalos continuos del contrato son vacíos con las
especificaciones declaradas. Budget se abstiene en ambos solvers. La importación
Base de HiGHS falla con coeficientes de hasta 1e17; escalados convencionales permiten
importar y obtener puntos que cumplen tras redondear. Gurobi Base también entrega
un punto que cumple. La incompatibilidad limita la garantía uniforme solicitada,
no prueba que el problema sea inviable o que no exista una buena solución.

En `ta1-UUM`, el contrato cambia 55 filas y ambos métodos L2 superan los presupuestos;
todos alcanzan el límite. NumericFocus 3 falla este chequeo en Gurobi. Un remedio
numérico existente tampoco garantiza resultados en todas las configuraciones, pero
este caso no prueba una ventaja propia de Budget frente a su control directo.

## Costos del contrato en STN

| Modelo | Solver | L2: solver s | Budget: solver s | L2: trabajo | Budget: trabajo |
|---|---|---|---|---|---|
'''+ '\n'.join(cost)+'''

Son tiempos de optimización de una llamada por configuración, no estimaciones de
velocidad general. Trabajo se conserva solamente para Gurobi. Excluyen selección
de factores, importación y verificación; el tiempo completo de cada llamada queda
en sus registros. Los controles ya satisfacen los presupuestos. La fracción del
presupuesto utilizada no permite equiparar la calidad de objetivos o cotas MILP.

## Diagnóstico previo y algoritmo

El diagnóstico computa μ = (ε/α + γ Σ|a_j|)/δ usando los parámetros nominales,
por fila y solver. En 31 puntos verificados, μ supera uno: no disponer de esa
garantía suficiente no predice necesariamente un fallo. El checker comprueba también
los residuos exportados realmente observados y la hipótesis entera; cuando todas
las hipótesis y μ≤1 se cumplen, las filas pasan la verificación, como exige la cota.
No se entrenó un predictor ni se evaluó uno en datos de confirmación.

`certifying_workflow.py` implementa un ciclo finito de intento, verificación,
alternativa y abstención. Devuelve solamente la asignación redondeada que verifica;
mantiene el estado de optimalidad separado como no verificado. En el replay de diez
pares modelo/solver, devuelve nueve asignaciones comprobadas y se abstiene en
Gurobi/control30-3-2-3. Para HiGHS/cinca, rechaza la importación Base y usa el punto
L2 comprobado. El replay no es una evaluación prospectiva de una política adaptativa.
Siete tests cubren fallos tras redondear, dominios enteros exactos, etiquetas óptimas irrelevantes, datos no
finitos, importaciones no cotejadas y cotas de exportación contra todos los vértices.

La cota de exportación firmada utiliza el soporte de la caja real:
R⁺ = Σ max[(αa_j−â_j) l_j, (αa_j−â_j) u_j] − (αb−b̂).
La violación tras redondear queda acotada por max[0,(ε+R⁺)/α+E] si el punto crudo
pertenece a la caja y las hipótesis son válidas. Para igualdad se consideran ambos
signos. Los términos con error cero no necesitan cotas finitas. El prototipo y sus
tests verifican esta descomposición elemental; no se la presenta como teorema novedoso.
En este piloto las exportaciones diádicas tienen error exactamente cero.

## Originalidad y decisión

La verificación independiente, los certificados y la reparación de puntos ya tienen
antecedentes fuertes. Eifler y Gleixner (2021) incluyen reparación exacta en un solver
MILP racional; Cheung, Gleixner y Steffy (2016/2017) estudian certificados verificables.
Gleixner y Steffy desarrollan LP con oráculos de precisión limitada. No hay base aquí
para anunciar como nueva la idea general de resolver, verificar y reparar.

La diferencia potencial sigue siendo una especificación trazable de presupuestos de
aplicación, factores, representación y aceptación. Para elevarla a contribución
algorítmica falta una evaluación prospectiva de las decisiones y costos totales y
una comparación con reparaciones/tolerancias/controles existentes. Este piloto
comprueba portabilidad y límites, sin demostrar esa ventaja.

**Decisión para el paper:** conservar v1.3.5 sin cambios. No agregar otra contribución,
otra tabla principal ni una campaña oportunista. La siguiente fase que podría aportar
valor sería ejecutar un ciclo de verificación y reparación bajo un protocolo fijo,
con requisitos defendibles y modelos/semillas no usados en el piloto. Debe informar
abstenciones y costo total y superar un control directo; si no lo hace, queda fuera.

## Reproducción

Desde la raíz del repositorio o del artefacto extraído:

```bash
python3 exploration/oms-generalization-20261014/generalization_study.py verify
python3 exploration/oms-generalization-20261014/independent_check.py
python3 exploration/oms-generalization-20261014/certifying_workflow.py
python3 -m pytest -q exploration/oms-generalization-20261014/test_certifying_workflow.py
```

El replay necesita Python/NumPy y pytest para los tests; no requiere Gurobi, HiGHS,
Pyomo o licencias. Regenerar modelos y ejecutar llamadas nuevas sí requiere las
dependencias descritas en `PILOT_PROTOCOL.md`. Los datos originales, logs, decisiones,
objetivos, puntos y resultados adversos se mantienen identificados por hashes.

Fuentes primarias:

- [STN-Scheduler y licencia MIT](https://github.com/jckantor/STN-Scheduler).
- [MIPLIB Numerics](https://miplib.zib.de/tag_numerics.html).
- [Guía numérica de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html).
- [Eifler y Gleixner, reparación/certificación exacta](https://arxiv.org/abs/2101.09141).
- [Cheung, Gleixner y Steffy, certificados](https://arxiv.org/abs/1611.08832).
- [Gleixner y Steffy, oráculos de precisión limitada](https://optimization-online.org/wp-content/uploads/2019/12/7507.pdf).
'''
    (HERE/'RESULTADOS.md').write_text(source)
    tex=r'''\documentclass[11pt]{article}
\usepackage[margin=25mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern,microtype,amsmath,booktabs,graphicx,xurl,xcolor}
\usepackage[colorlinks=true,allcolors=blue!45!black]{hyperref}
\title{Exploración preliminar: contratos de precisión en fuentes MILP independientes}
\author{Documento de trabajo separado del paper OMS}
\date{14 de octubre de 2026}
\begin{document}\maketitle
\noindent\textbf{Conclusión.} El piloto comprueba transferencia de código, verificaciones
y abstenciones, pero no una ventaja de aceptación primal de Budget-L2 frente a su
control. Se conserva intacta la entrega \texttt{v1.3.5-oms-submission}.
No se añade una contribución ni resultados al artículo en esta etapa.

\section{Diseño y alcance}
Se fijaron dos modelos de producción por lotes del generador independiente
STN-Scheduler (Kondili, H=10 y H=12), y tres grupos distintos del tag Numerics de
MIPLIB seleccionados antes de resolver, por número de no ceros y dimensiones.
Se conservan 55 brazos, 52 puntos, dos abstenciones y un fallo de importación.
Gurobi y HiGHS usan presolve normal, cuatro hilos, semilla 17, gap 1\% y límite 15 s.
Las exportaciones son diádicas exactas, con los intervalos ya implementados y
coeficientes en $[10^{-9},10^9]$. Objetivo, cotas, dominios y proporcionalidad de
filas/RHS se cotejan antes de aceptar una importación.

En STN el presupuesto de cantidades es $10^{-5}$ kg (10 mg), un objetivo numérico
elegido para el estudio; filas lógicas $10^{-5}$ y monetarias $10^{-3}$ en las
unidades de la fuente. No son tolerancias industriales. Los contratos modifican
88 y 104 factores de capacidad, respectivamente. L2 y Budget comparten una
tolerancia entera guiada; en HiGHS su parámetro MIP también afecta la precisión
primal. MIPLIB usa $10^{-4}\max(1,|b_r|)$ en unidades algebraicas experimentales,
sin interpretación física; su contrato cubre el punto crudo y el redondeado se
comprueba después. El archivo actual de cinca tiene 4.350 no ceros, frente a
3.678 de la ficha; se conserva esa discrepancia.

\section{Resultados conservados}
V: punto entero dentro de presupuestos de todas las filas/cotas. F: punto que falla.
A: abstención. I: importación fallida. Guion: control no disponible.
V no significa factibilidad exacta, cota dual válida u óptimo global. L2 y GM son
sus variantes diádicas exactas; ``tight'' reduce tolerancias a $10^{-9}$.
\begin{center}\small\setlength{\tabcolsep}{4pt}
\begin{tabular}{llrrrrrr}\toprule
Modelo & Solver & Base & GM & L2 & Budget & Tight & NF3\\\midrule
'''+ '\n'.join(latex)+r'''
\bottomrule\end{tabular}\end{center}

Un checker separado, sin importar el runner ni un solver, revisa 52 puntos con
\texttt{Fraction}: 41 pasan tras redondear y 42 antes. Las cuentas combinan
configuraciones y no son tasas poblacionales ni un ranking.

En STN todas las políticas pasan: cambiar factores no aporta una ganancia de
precisión necesaria cuando los controles ya cumplen. En control30-3-2-3,
Budget reduce el ratio crudo Gurobi de 26.526 a 0,302, pero el entero falla con
ratio 146.563; Base y GM también cumplían en crudo. Todas las variantes Gurobi
fallan el chequeo entero. HiGHS lo supera, pero llega al límite en todas sus llamadas.

En cinca hay 96 intervalos continuos vacíos para el contrato. Esto limita la
garantía uniforme: Gurobi Base y varios controles HiGHS sí producen puntos que
cumplen después de redondear. La importación Base de HiGHS falla con coeficientes
de hasta $10^{17}$. En ta1-UUM el contrato cambia 55 factores y ambos L2 pasan;
se alcanza el límite, y NumericFocus falla en Gurobi. No hay mejora propia de
Budget en aceptación respecto de su control directo.

\section{Costo y diagnóstico}
Tiempos de una llamada por configuración, de optimización solamente; no incluyen
selección, importación o verificación. Trabajo corresponde exclusivamente a Gurobi.
No se infiere velocidad general de este piloto.
\begin{center}\small
\begin{tabular}{llrrrr}\toprule
Modelo & Solver & L2 (s) & Budget (s) & L2 trabajo & Budget trabajo\\\midrule
'''+ '\n'.join(costlatex)+r'''
\bottomrule\end{tabular}\end{center}

El indicador previo es $\mu_r=(\epsilon/\alpha_r+
\gamma\sum_{j\in I}|a_{rj}|)/\delta_r$, con parámetros nominales por solver.
En 31 puntos que pasan, $\mu>1$: ausencia de garantía suficiente no predice un
fallo. También se comprueban las hipótesis exportada y entera realmente observadas.
No se entrenó un predictor ni se validó sobre datos de confirmación.

\section{Prototipo y componente matemático}
El ciclo finito de intento, comprobación, alternativa y abstención devuelve
solamente el punto entero que verifica y conserva la optimalidad como no verificada.
Su replay de diez pares devuelve nueve asignaciones y se abstiene en
Gurobi/control30-3-2-3; HiGHS/cinca pasa de la importación Base fallida a L2.
Es un replay de brazos fijos, sin medida prospectiva de costo adaptativo.
Siete tests cubren etiquetas óptimas que no pueden anular fallos, redondeo, dominios enteros exactos,
importaciones no cotejadas, datos no finitos y soporte contra todos los vértices.

Sean $e=\alpha a-\widehat a$ y $e_b=\alpha b-\widehat b$. Sobre una caja válida,
\[
 R^+=\sum_j\max(e_jl_j,e_ju_j)-e_b,\qquad
 v(x^{\rm int})\le\max\{0,(\epsilon+R^+)/\alpha+E\}.
\]
La pertenencia del punto crudo a la caja y las hipótesis de residuo/redondeo son
necesarias. Para igualdad se evalúan ambos signos. Los términos con error cero
no requieren extremos finitos. Es una descomposición elemental, no una novedad
demostrada. En el piloto diádico el error de exportación es exactamente cero.

\section{Decisión y reproducción}
La verificación, reparación y certificación tienen antecedentes fuertes; el posible
aporte sigue siendo la integración trazable de presupuestos, selección y aceptación,
con utilidad adicional comprobada. Este piloto no basta para proclamarla.
La siguiente fase útil sería una política prospectiva, requisitos defendibles,
modelos/semillas nuevos, controles fuertes, abstenciones y costo total declarado.
Se conserva la versión OMS actual.

El documento completo \texttt{RESULTADOS.md} y \texttt{PILOT\_PROTOCOL.md}
describen cada precisión, control y alcance. El artefacto conserva los cinco modelos,
55 registros, puntos, logs, decisiones y replays sin licencias para verificar.
Se necesitan Python/NumPy y pytest para los tests; generar modelos/soluciones nuevas
requiere además las dependencias registradas. No se atribuyen certificados de
optimalidad a este estudio.

\paragraph{Fuentes primarias}
\href{https://github.com/jckantor/STN-Scheduler}{STN-Scheduler};
\href{https://miplib.zib.de/tag_numerics.html}{MIPLIB Numerics};
\href{https://arxiv.org/abs/2101.09141}{Eifler y Gleixner (2021), reparación exacta};
\href{https://arxiv.org/abs/1611.08832}{Cheung, Gleixner y Steffy, certificados};
\href{https://optimization-online.org/wp-content/uploads/2019/12/7507.pdf}{Gleixner y Steffy, oráculos de precisión limitada};
\href{https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html}{guía numérica de Gurobi}.
\end{document}
'''
    (HERE/'exploration-note.tex').write_text(tex)
    print('Standalone RESULTADOS.md and exploration-note.tex written from verified records')


if __name__=='__main__':main()
