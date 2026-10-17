#!/usr/bin/env python3
"""Standalone Spanish research note and a vector precision-effort plot."""
import csv
import json
from pathlib import Path
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
front=ROOT/'exploration/oms-frontier-20261016'
pairs=list(csv.DictReader((front/'paired-costs.csv').open()))
summary=list(csv.DictReader((front/'verified-summary.csv').open()))
fig,axes=plt.subplots(1,3,figsize=(10.5,3.0),layout='constrained')
budgets=[30,100,300,1000,3000,10000]
for presolve,color,label in [(-1,'#176B9D','Presolve automático'),(0,'#B54A35','Sin presolve')]:
    p=[next(r for r in pairs if int(r['presolve'])==presolve and int(r['budget'])==b) for b in budgets]
    s=[next(r for r in summary if int(r['presolve'])==presolve and int(r['budget'])==b and r['policy']=='Budget-L2') for b in budgets]
    for ax,y in zip(axes,[[float(r['work_ratio']) for r in p],[int(r['bound_flags']) for r in s],[int(r['budgets_passed']) for r in s]]):
        ax.plot(budgets,y,'o-',color=color,label=label,linewidth=1.5,markersize=4)
        ax.set_xscale('log');ax.grid(alpha=.2);ax.set_xlabel('Presupuesto de volumen (m³)')
        ax.axvspan(30,100,color='#C3DCC8',alpha=.35,zorder=-1)
axes[0].set_ylabel('Trabajo Budget / NF3');axes[0].axhline(1,color='gray',linestyle='--',linewidth=1)
axes[1].set_ylabel('Cotas contradichas, de 18');axes[1].set_ylim(-.4,10)
axes[2].set_ylabel('Cumplen presupuesto, de 18');axes[2].set_ylim(14.5,18.5)
axes[0].legend(fontsize=8,frameon=False);fig.savefig(HERE/'precision-effort.pdf');plt.close(fig)
text=r'''\documentclass[11pt]{article}
\usepackage[a4paper,margin=20mm]{geometry}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,booktabs,graphicx,amsmath,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue}
\title{Contratos de precisión: resultados nuevos para OMS}
\author{Nota de investigación y decisión editorial}\date{16 de octubre de 2026}
\begin{document}\maketitle
\noindent Se completaron 384 llamadas MILP nuevas y 56 LP de adquisición o
refinamiento, además del diagnóstico exacto y del benchmark de implementación.
Las asignaciones se fijaron por campaña antes de resolver; la ablación y el
refinamiento posteriores están identificados como seguimientos. Se conservan
resultados adversos, abstenciones y ambas pasadas del benchmark C++.

\section*{1. Resultado que fortalece el paper actual}
La frontera conserva 330 MILP y 30 abstenciones, seis modelos conocidos, tres
semillas nuevas y siete presupuestos. A potencia fija 0,01 MW, presolve automático
y 30--100 m\textsuperscript{3}, los seis modelos cumplen el criterio prefijado
frente a NF3: objetivos satisfechos, menor trabajo, ninguna contradicción de cota
detectada y costo de candidato dentro del margen comparativo del 1\%.

\begin{center}\begin{tabular}{lrr}\toprule
Presolve automático & 30 m\textsuperscript{3} & 100 m\textsuperscript{3}\\\midrule
Budget cumple objetivos & 18/18 & 18/18\\
Cotas/cierres contradichos de Budget & 0/0 & 0/0\\
Cotas/cierres contradichos de NF3 & 0/0 & 0/0\\
Trabajo emparejado Budget/NF3 & 0,411 & 0,362\\
Tiempo completo emparejado Budget/NF3 & 0,704 & 0,629\\\bottomrule
\end{tabular}\end{center}
La ausencia de contradicciones no certifica las cotas. La recuperación primal
frente a L2 sigue localizada en 046 sin presolve; bajo presolve automático L2
ya cumple los objetivos. La evidencia nueva es el régimen de esfuerzo y
consistencia. Fuera de él reaparecen discrepancias y fallos de precisión.
Los segundos corresponden a una máquina compartida. A 30 m\textsuperscript{3},
tres modelos baratos tienen mayor tiempo completo aunque consumen menos Work.

\begin{center}\includegraphics[width=\linewidth]{precision-effort.pdf}\end{center}
\noindent El sombreado indica el régimen auto que cumple el criterio fijado.
3.000 y 10.000 m\textsuperscript{3} producen la misma exportación que L2 y no
se cuentan como representaciones independientes. El caso de 10 m\textsuperscript{3}
se omite del gráfico porque solo uno de los seis modelos admite su contrato.

\section*{2. Software: menos costo con exactamente los mismos datos}
El selector C++ integrado produce exactamente los mismos factores y datos
binary64 que Python en doce pares modelo/política. La preparación Budget-L2
es entre 3,70 y 6,37 veces más rápida según medianas por modelo; la mediana de
esas medianas pasa de 1,243 a 0,315 s. Se conservan 336 mediciones y 48 preflights:
el primer diseño completo se repitió tras corregir el CSV de auditoría, sin
cambiar ningún modelo. No se extrapola esa aceleración a una resolución completa.

\section*{3. Garantías globales que antes no estaban cerradas}
Se verificaron los duales de seis LP que relajan todas las binarias, sin fijar
patrones. Son cotas inferiores globales verdaderas. Con testigos enteros
exactamente factibles, certifican el 1\% en 005,022,031 y prueban el óptimo
MILP exacto de 031. Las anchuras de los otros intervalos son 22,085\% (001),
1,099\% (027) y 5,209\% (046); no certifican sus gaps del 1\%.

Un seguimiento sobre todas las 18 salidas conjuntas resuelve 13 LP de patrón
distintos. Los puntos refinados son exactamente factibles en los 18 casos;
nueve tienen garantía global del 1\% y tres son óptimos exactos. El LP de patrón
solo aporta el testigo primal; la cota inferior procede exclusivamente del LP
global. La salida certificada es el vector racional refinado. La adquisición
global suma 23,98 s y el refinamiento 48,52 s, además de solver, selección y
testigos de referencia. No es una garantía gratuita ni exclusiva de los contratos.

\section*{4. Extensión conjunta, conservada como investigación separada}
Se implementó una caracterización del escalamiento dyádico conjunto con
contratos, exactitud de matriz/RHS/costos/cotas y columnas enteras inmóviles.
Un verificador independiente reconstruye intervalos por enumeración de
exponentes y comprueba potenciales y ciclos: 84 celdas y 16.893.360 desigualdades.
El menor entero de centrado pasa de 17 a 8 a 100 m\textsuperscript{3} en los seis
modelos. Es centrado de magnitudes, no condición espectral.

La ablación 2x2 tiene 72 brazos y 54 llamadas únicas: 18 del piloto, 36 nuevas
y 18 aliases declarados antes de resolver. Las medias geométricas Work son
1,922 para filas, 1,399 para conjunto con contratos y 3,683 sin contratos.
El contrato conjunto reduce trabajo en cinco modelos frente al conjunto libre:
en 001 su razón es 0,0355; en cambio, 031 empeora 2,81 veces. Todas las variantes
cumplen el objetivo preestablecido de 100 m\textsuperscript{3}. Se declara el
costo offline de seleccionar factores y no se afirma una ventaja de ciclo completo.

La formulación logarítmica y los algoritmos de grafos tienen antecedentes
clásicos. La combinación merece seguimiento, pero su novedad y validez externa
no están establecidas. No se añade como otra contribución principal del artículo.
Frente al Budget-L2 por filas ya disponible, el conjunto contractual consume
22,2\% más trabajo agregado y solo mejora en dos modelos. El addendum conserva
los CSV fuente y sus hashes; no se presenta la mejora frente a un control más
débil como una ventaja sobre el método actual.

\section*{Decisión y archivos}
OMS v1.3.11 incorpora un párrafo de sensibilidad y las Tablas S17--S19; conserva
dos contribuciones principales. El manuscrito tiene 35 páginas, el suplemento
25 y la carta una. La extensión conjunta y su refinamiento quedan separados.
Los modelos siguen siendo conocidos y de una familia; los pilotos externos
anteriores no mostraron una ventaja general y no se repitieron para forzarla.
No se publicaron ni enviaron archivos. El DOI queda para el último paso.

\noindent Los protocolos, datos, scripts independientes y decisiones se conservan
en cuatro directorios de exploración, todos fechados 16 de octubre.
El archivo \texttt{RESULTADOS.md} enlaza cada informe completo.
\end{document}
'''
(HERE/'research-note.tex').write_text(text)
for _ in range(2):subprocess.run(['pdflatex','-halt-on-error','-interaction=nonstopmode','research-note.tex'],cwd=HERE,stdout=subprocess.DEVNULL,check=True)
log=(HERE/'research-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
