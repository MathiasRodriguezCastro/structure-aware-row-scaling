#!/usr/bin/env python3
"""Render the finite study as a short Spanish note; read archived results only."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def read(p):return json.loads(Path(p).read_text())
def n(x):return '--' if x is None else f'{x:.4g}'
def tex(s):return str(s).replace('_',r'\_').replace('%',r'\%')


def main():
    a=read(HERE/'analysis.json');v=read(HERE/'independent-verification.json')
    normal=[g for g in a['groups'] if g['scale']==g['presolve']==-1 and g['policy']!='Algebraic']
    compact=[]
    for stage,instances in [('discovery',['instance001','instance014','instance042']),('holdout',['instance002','instance003','instance004'])]:
        for instance in instances:
            gs={g['policy']:g for g in normal if g['instance']==instance}
            compact.append(dict(stage=stage,instance=instance,**gs))
    table='| Caso | Etapa | Base: termina / trabajo | GM: termina / trabajo | Ruiz: termina / trabajo |\n|---|---|---:|---:|---:|\n'
    texrows=[]
    for r in compact:
        cells=[f"{r[p]['completed']}/3; {n(r[p]['median_work'])}" for p in ('Base','Structural','Ruiz')]
        table+=f"| {r['instance']} | {r['stage']} | "+' | '.join(cells)+' |\n'
        texrows.append(r['instance'].replace('instance','')+' & '+('D' if r['stage']=='discovery' else 'R')+' & '+' & '.join(cells)+r' \\')
    maxratio=[max(r['physical_ratios'][j] for r in v['point_checks'] if r.get('exact_rational_point')) for j in range(3)]
    budgets='| Escenario | MW / m³ | Admisibles | Modificados | Incompatibles | Máx. residuo / presupuesto |\n|---|---:|---:|---:|---:|---:|\n'
    for j,(name,p,w) in enumerate([('Exigente',.01,100),('Referencia',.1,1000),('Permisivo',1.,10000)]):
        budgets+=f'| {name} | {p} / {w} | 100 % | 0 | 0 | {maxratio[j]:.4g} |\n'
    # The reference physical scenarios scale by exactly one decade conceptually;
    # ratios use each declared binary64 algebraic budget independently.
    genuine=[g for g in a['groups'] if g['policy']=='Structural' and g['scale']==g['presolve']==-1]
    workratios=[r for r in a['paired_comparisons'] if r['scale']==r['presolve']==-1]
    pairtable='| Caso | Pares comparables | Mediana GM/Base de trabajo |\n|---|---:|---:|\n'
    for r in workratios:pairtable+=f"| {r['instance']} | {r['comparable_pairs']}/3 | {n(r['median_work_ratio'])} |\n"
    factorial='| Caso | Interno | Presolve | Base: termina / trabajo | GM: termina / trabajo |\n|---|---|---|---:|---:|\n'
    for instance in ['instance001','instance014','instance042']:
        for scale in (-1,0):
            for presolve in (-1,0):
                gs={g['policy']:g for g in a['groups'] if g['instance']==instance and g['scale']==scale and g['presolve']==presolve}
                factorial+=f"| {instance} | {'auto' if scale==-1 else 'off'} | {'auto' if presolve==-1 else 'off'} | "+' | '.join(f"{gs[p]['completed']}/3; {n(gs[p]['median_work'])}" for p in ('Base','Structural'))+' |\n'
    witness=a['exact_witness'];contradicted=a['contradicted_bounds']
    if witness and witness['outcome']=='exact_feasible':
        witness_text=(f"Una comprobación posterior con SoPlex produjo un punto **racionalmente factible** "
            f"del MILP canónico 001, de costo {witness['objective']:.9g}. El verificador independiente "
            f"comprueba todas sus filas, cotas e integridad sin tolerancias. Ese testigo refuta "
            f"{len(contradicted)} cotas inferiores reportadas en el factorial (todas con ScaleFlag=0); "
            f"{sum(r['status']==2 for r in contradicted)} de esas corridas tenían estado OPTIMAL. "
            "No prueba el óptimo del MILP. El costo del testigo no es una referencia óptima.")
        witness_tex=(f"Un testigo racional factible de costo {witness['objective']:.9g} refuta "
            f"{len(contradicted)} cotas inferiores del factorial; {sum(r['status']==2 for r in contradicted)} "
            "provenían de corridas con estado OPTIMAL. Todas tenían ScaleFlag=0. "
            "Se verificaron sin tolerancias filas, cotas e integridad del testigo. "
            "Esto certifica una contradicción de cotas, no el óptimo del MILP.")
    else:
        witness_text='El intento posterior de construir un testigo racional terminó desconocido. No se presenta una contradicción exacta de cotas ni se interpreta desconocido como inviable.'
        witness_tex=witness_text
    original=read(HERE/'inputs/instance001/preparation.json')['canonical_stats']
    equality=[]
    for r in compact:
        b=r['Base']['diagnostic'];s=r['Structural']['diagnostic']
        equal=b['presolve']['normalized_sha256']==s['presolve']['normalized_sha256']
        equality.append(equal)
    text=f'''# Escalamiento interno y valor del generador: resultados

**Decisión: conservar este trabajo como exploración independiente; no modificar
OMS v1.3.5.** Hay beneficios del escalamiento externo en algunos casos con
parámetros normales, pero no una ventaja atribuible a presupuestos físicos o
roles en este banco, ni una regla predictiva validada. No se incorpora otra tabla
al artículo por una evidencia que aún no cumple ese objetivo.

## Alcance y calidad del experimento

Seis SG-Ter-Mer reales de 360 períodos, {original['columns']} variables,
{original['rows']} filas y {original['integers']} enteras cada uno. Se mantienen
las variables enteras del generador. Descubrimiento retrospectivo: 001, 014,
042; reserva fijada antes de optimizar: 002, 003, 004. No son una muestra
aleatoria ni seis familias independientes. No se usan para este ensayo los tres
MPS continuos de la exploración Benders. El diagnóstico LP–DW permanece pendiente.

{a['arms']} brazos planificados, **{a['native_mip_calls']} llamadas MILP reales**
tras deduplicar matrices idénticas; {a['separate_lp_calls']} relajaciones LP y
{a['diagnostics']} diagnósticos presolve separados. Un intento LP racional
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
las {6*original['rows']:,} filas preparadas. En los acoplamientos ambos candidatos
quedan en la banda identidad; el resto usa GM. Generator también coincide para
los tres presupuestos autorizados. Ruiz es un control distinto de cuatro
medias iteraciones, sin escalar columnas.

{budgets}
Admisibilidad y modificación se calculan para Structural/Generator en las filas
físicas reconocidas; el máximo observado abarca **todos los puntos finales y
políticas** del estudio, evaluados racionalmente. Cada escenario cubre
{sum(r['physical_rows'] for r in v['contracts'] if r['scenario']=='Reference'):,}
filas físicas en seis modelos; el denominador no incluye otras restricciones.
Se convierten MW/m³ a unidades algebraicas por los coeficientes del generador.
Son objetivos de precisión del estudio, no tolerancias de UTE.

La garantía es condicional: residuo exportado <=1e-6 implica residuo original
<=1e-6/alpha. Esa cota no es el residuo observado; este se verifica por separado.
La coincidencia permite deduplicar MILP, pero **impide identificar una ventaja
operacional de la información física**. Tampoco demuestra que nunca aporte.

## 2. El escalamiento externo sí puede afectar condiciones normales

{table}
Cada celda: corridas que declaran OPTIMAL al gap solicitado / mediana de trabajo
de las tres corridas, incluidas las censuradas. GM significa Algebraic=Structural.
No es una tabla de aceleraciones: alcanzar un límite con peor incumbente/cota
no equivale a resolver más rápido. Estado OPTIMAL es la declaración numérica
del solver, sujeta a comprobación. Todos los estados, cotas, objetivos, gaps,
tiempos y puntos están archivados en runs y runs-summary.csv.

{pairtable}
Se exige que ambos terminen y sus objetivos difieran <=1e-6 max(1,|U1|,|U2|).
No se inventa una razón de aceleración para pares censurados o de calidad distinta.
Con un presupuesto de 12 unidades esto solo es una comparación acotada, no una
afirmación asintótica ni de tiempos a optimalidad exacta.

## 3. Presolve e interacciones

La huella exacta de filas normalizadas, dominios y objetivo coincide entre
Base y GM después del diagnóstico de presolve en **{sum(equality)}/6** casos con
parámetros normales. Las magnitudes sí cambian y el trabajo puede cambiar.
Por tanto, conservar la misma geometría normalizada no basta para anticipar
el esfuerzo; reducir rangos tampoco garantiza una ventaja. La relajación LP
normal es numéricamente la misma entre esas formulaciones.

{factorial}
Las desactivaciones son intervenciones diagnósticas, no configuraciones
operativas recomendadas. Las declaraciones de completamiento con ScaleFlag=0
deben leerse junto con las verificaciones y la siguiente comprobación.

{witness_text}

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
'''
    (HERE/'RESULTADOS.md').write_text(text)
    # Keep the PDF deliberately short; full factorial remains in the Markdown/CSV.
    latex=r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage[margin=2cm]{geometry}
\usepackage{booktabs,hyperref,array}
\hypersetup{colorlinks=true,urlcolor=blue}
\setlength{\parskip}{5pt}\setlength{\parindent}{0pt}
\begin{document}
\begin{center}{\Large Escalamiento interno y valor del generador}\\[4pt]
Exploración independiente para OMS --- octubre de 2026\end{center}
\textbf{Decisión: mantener OMS v1.3.5 sin cambios.} El escalamiento externo
produce beneficios en algunos casos con parámetros normales, pero no aparece
una ventaja atribuible a información adicional ni una regla predictiva validada.

\textbf{Diseño.} Seis modelos SG--Ter--Mer de 360 períodos, 6120 variables,
10080 filas y 1440 enteras cada uno. Descubrimiento: 001,014,042, elegidos por
resultados históricos; reserva: 002,003,004, fijados antes de optimizar. Se
conserva la integralidad original. No se usan los tres MPS continuos de Benders.
Se exportan MPS nativos desde el ejecutable existente, sin modificar fuentes.
No es una réplica de los LP antiguos DummyLp: cambian exportador, orden,
semillas, factores dyádicos y gap.

Gurobi 13.0.2, cuatro hilos, semillas 307,331,353, 12 s y 12 unidades de trabajo,
gap 0.1\%, tolerancias 1e-6/1e-5, sin starts. Factorial Base/Structural por
escalamiento interno auto/off y presolve auto/off, más controles GM y Ruiz.
Reserva con parámetros normales. Todas las resoluciones fueron secuenciales.
ARMS brazos, CALLS llamadas MILP reales al deduplicar y LPS LP diagnósticos.
Un LP racional posterior se informa aparte. Diagnóstico y verificación no se
incluyen en el tiempo de optimización; sus costos están registrados.

\textbf{Atribución.} Un selector común elige potencias de dos dentro de una
ventana [1e-9,1e9], con banda identidad [0.5,2]. Se comprueba exactamente cada
producto de coeficiente/RHS y se conservan cotas, dominios y objetivo.
Algebraic usa GM; Structural cambia a L2 en acoplamientos. En los seis modelos,
ambos candidatos de acoplamiento quedan en la banda identidad y el resto usa
GM: \textbf{Algebraic=Structural en todas las filas}. Generator aplica además
presupuestos físicos: tampoco cambia factores. No se fuerza actividad reduciendo
presupuestos. Ruiz conserva columnas y usa cuatro medias iteraciones.

\begin{center}\begin{tabular}{lrrrr}\toprule
Escenario & MW & m$^3$ & Admisibles & Modificados/incompatibles\\\midrule
Exigente & .01 & 100 & 100\% & 0/0\\
Referencia & .1 & 1000 & 100\% & 0/0\\
Permisivo & 1 & 10000 & 100\% & 0/0\\\bottomrule
\end{tabular}\end{center}
Las unidades algebraicas se convierten por los coeficientes físicos de cada
fila; son objetivos numéricos del estudio, no tolerancias de UTE. La garantía
residuo original $\leq10^{-6}/\alpha$ es condicional al residuo exportado.
Los máximos observados divididos por presupuesto, sobre todos los puntos
finales/políticas, fueron RATIOS. Se evaluaron racionalmente y no se confunden
con la garantía. La igualdad de factores impide identificar una ventaja
operacional de la información física en este banco; no demuestra inutilidad
universal de esa información.

\newpage
\textbf{Resultado con escalamiento interno y presolve normales.}
Cada celda indica corridas que declaran OPTIMAL al gap pedido sobre tres, y
mediana de trabajo incluyendo las censuradas. GM agrupa Algebraic y Structural.

\begin{center}\begin{tabular}{llrrr}\toprule
Caso & Etapa & Base & GM & Ruiz\\\midrule
TABLE
\bottomrule\end{tabular}\end{center}
D: descubrimiento; R: reserva. Una mediana de trabajo menor con peor cota o
incumbente no es una aceleración. RESULTADOS.md y los CSV conservan todos los
estados, gaps, cotas, objetivos, tiempos y el factorial completo. No se informa
una razón de aceleración cuando uno no termina o la calidad primal difiere.

\textbf{Qué revela presolve.} En EQUALITY de seis casos Base y GM tienen
exactamente la misma huella de filas normalizadas, dominios y objetivo tras
el diagnóstico presolve normal, aunque sus magnitudes y trabajo difieren.
La relajación LP normal coincide numéricamente. Ni esa huella ni la reducción
de rangos permiten afirmar una ventaja universal. No se ha localizado un corte,
pivote o factor interno que explique causalmente las diferencias.

\textbf{Comprobación posterior.} WITNESS
El intento racional usa un patrón entero del descubrimiento, todas las filas y
cotas originales y costo $\leq0$, con 30 s de SoPlex. Está fuera de los tiempos
del factorial y es una validación posterior, no evidencia prospectiva.

\textbf{Límites y decisión.} Se fijaron conclusiones y hashes del descubrimiento
antes de abrir resultados de reserva. No se ajustó un predictor a tres casos
ni se reajustó con los reservados. Es un ensayo acotado de una familia y un
solver: no prueba una ventaja nueva generator-aware, un mecanismo interno
específico o una predicción útil fuera de muestra. Por eso se archiva separado
y no se amplía el manuscrito. El diagnóstico compacto LP--DW, la frontera
precisión--trabajo y los límites conjuntos del escalamiento siguen pendientes.

\textbf{Reproducción y fuentes.} El paquete incluye entradas, MPS, datos
canónicos, factores, puntos, trazas, logs, protocolo y scripts. Un replay sin
solver reimporta los seis MPS y comprueba los residuos con aritmética racional.
La entrega OMS y los siete paquetes anteriores se verifican por SHA256.
La documentación de \href{https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.presolve}{Gurobi, Model.presolve}
advierte que su modelo puede diferir del usado por optimize: no es la matriz
realmente escalada internamente. Véanse también
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:ScaleFlag}{ScaleFlag}
y el \href{https://soplex.zib.de/doc/html/EXACT.php}{modo racional de SoPlex}.
\end{document}
'''
    for k,val in {'ARMS':a['arms'],'CALLS':a['native_mip_calls'],'LPS':a['separate_lp_calls'],
                  'RATIOS':', '.join(n(x) for x in maxratio),'TABLE':'\n'.join(texrows),
                  'EQUALITY':sum(equality),'WITNESS':witness_tex}.items():latex=latex.replace(k,str(val))
    (HERE/'scaling-mechanisms-note.tex').write_text(latex)


if __name__=='__main__':main()
