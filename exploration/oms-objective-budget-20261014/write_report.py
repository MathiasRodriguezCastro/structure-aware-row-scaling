#!/usr/bin/env python3
"""Generate the standalone objective-sensitivity report and scientific plot."""
import csv
from fractions import Fraction
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent


def load(p):return json.loads(p.read_text())
def rows(name):return list(csv.DictReader((HERE/name).open()))
def mdtable(data):return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in data)
def textable(data):return '\n'.join(' & '.join(map(str,r))+r'\\' for r in data)


def main():
    d=load(HERE/'design.json');v=load(HERE/'independent-verification.json')
    end=rows('endpoints.csv');curves=rows('curves.csv');fact=rows('feasibility-thresholds.csv');safe=rows('protected-budgets.csv');sel=rows('selective-budgets.csv')
    assert v['new_lp_calls']==208 and v['selective_protection_certificates']==10
    comparisons=[]
    for model in sorted({r['model'] for r in end}):
        es=[r for r in end if r['model']==model];losses=[float(r['relative_loss'])*100 for r in es if r['relative_loss']]
        comparisons.append([model,str(len(es)),str(sum(r['v0_outcome']=='infeasibility_certified' for r in es)),
                            f'{min(losses):.6f}--{max(losses):.6f}' if losses else '0'])
    cases=[]
    fig,ax=plt.subplots(figsize=(7,3.2),layout='constrained')
    for seed,color in ((83,'#195d91'),(97,'#bd5625')):
        record=next(r for r in d['records'] if r['model']=='neos-3083784-nive' and r['arm']=='gurobi-L2-IF1' and r['seed']==seed)
        key=record['pattern'];e=next(r for r in end if r['pattern']==key);s=next(r for r in safe if r['pattern']==key)
        cs=sorted((Fraction(r['lambda_exact']),Fraction(r['value_exact'])) for r in curves if r['pattern']==key and r['value_exact'] and Fraction(r['lambda_exact'])>0)
        v0=Fraction(e['v0_exact']);ax.plot([float(x) for x,y in cs],[float((v0-y)/v0) for x,y in cs],'-o',ms=4,lw=1.4,color=color,label=f'Gurobi, semilla {seed}')
        ax.axvline(float(s['cost_threshold']),color=color,ls=':',lw=.9)
        cases.append(['Gurobi',seed,f'{float(v0):.0f}',f"{float(s['cost_threshold']):.6g}",s['safe_factor_exact']])
    for seed in (83,97):
        record=next(r for r in d['records'] if r['model']=='neos-3083784-nive' and r['arm']=='highs-L2' and r['seed']==seed)
        f=next(r for r in fact if r['pattern']==record['pattern'])
        cases.append(['HiGHS',seed,'inviable',f"{float(f['lambda_feas']):.6g}",'--'])
    ax.axhline(.01,color='#666666',ls='--',lw=1,label='Pérdida del 1 %')
    ax.set(xscale='log',xlim=(5e-10,1.5),ylim=(-.025,1.055),xlabel=r'$\lambda$: escala común de los presupuestos',ylabel=r'Reducción máxima $D_z(\lambda)/v_z(0)$')
    ax.grid(axis='both',alpha=.2);ax.legend(loc='center right',frameon=False,fontsize=8)
    for suffix in ('pdf','png'):
        metadata={'CreationDate':None,'ModDate':None,'Creator':'objective-budget-study'} if suffix=='pdf' else {'Software':'objective-budget-study'}
        fig.savefig(HERE/('objective-sensitivity.'+suffix),dpi=200,metadata=metadata)
    plt.close(fig)
    kept_min=min(int(s['changed_rows']) for s in sel);kept_max=max(int(s['changed_rows']) for s in sel)
    bound_min=min(int(s['changed_bound_variables']) for s in sel);bound_max=max(int(s['changed_bound_variables']) for s in sel)
    assert kept_min==kept_max==40
    md=f'''# Presupuestos de residuos, costo y aceptación certificada

**Resultado:** el diagnóstico ajustado identifica el deterioro máximo permitido
por los presupuestos y dos umbrales de factibilidad. La protección al 1 % necesita
una escala muy pequeña, pero basta aplicarla a **40 de 2.836 filas** por patrón,
conservando los presupuestos de todas las cotas continuas. Los diez casos tienen
certificados de protección, específicos del patrón.
Esto es una garantía posterior específica del patrón, no un presupuesto universal
ni evidencia de superioridad computacional. OMS v1.3.5 permanece sin cambios.

## Diseño y alcance

Se parte de las 72 entregas de los 80 tratamientos previos. Se identifican
41 patrones enteros únicos: 12 de nive y 29 de los otros cuatro modelos.
Las semillas, solvers y controles son los ya guardados; no se resuelve otro MILP.
Se usan todos los patrones y se mantienen las ocho ausencias originales.
Los tratamientos L2/Budget de nive repiten patrones para una misma semilla.
El estudio es retrospectivo: los otros modelos ya estaban seleccionados y control
es referencia conocida, no validación poblacional nueva.

Primero se fijaron 178 tareas LP: v(0)/v(1) para los 41 patrones; siete escalas
diádicas intermedias y un umbral de factibilidad para los 12 de nive. Después,
según la regla fijada en PROTOCOL.md, diez LP de umbral de pérdida al 1 % y diez
LP de validación del factor seguro. La variante selectiva se declaró después de
observar esos resultados, antes de sus diez LP adicionales. Total: 208 llamadas,
2 s por LP, watchdog 4 s. No hay sustituciones ni reintentos de casos favorables.

## Qué mide v(lambda)

Se fijan los enteros z y sus cotas exactas. Solo las filas y cotas continuas se
amplían por lambda*delta y lambda*beta. La igualdad tiene ambos lados ampliados.
Los presupuestos iniciales son algebraicos: delta=1e-4 max(1,|RHS|), beta=1e-4.
No representan tolerancias de UTE/ADME u otro operador.

v(lambda) es el menor costo posible en esa región ampliada. Si el patrón es
exactamente factible, D(lambda)=v(0)-v(lambda) mide una vulnerabilidad potencial,
no el error efectivamente observado en cada entrega nativa. La precisión del
cálculo de c^T x sigue siendo correcta. Cada mínimo aquí se comprueba por igualdad
primal/dual exacta; cada inviabilidad, por rayo original verificado.

## Generalización del diagnóstico, sin atribuir fallos a los solvers

| Modelo | Patrones únicos | Inviables exactos | Pérdida potencial v(0)-v(1), % de abs(v(0)) |
|---|---:|---:|---:|
'''+mdtable(comparisons)+f'''

En control hay entre 4,82 % y 7,65 % de deterioro potencial. Clasificación y
neos-1112787 tienen pérdidas menores que 0,001 %; lesse, cero. En nive, los diez
patrones factibles permiten prácticamente borrar su costo. v(1) es aproximadamente -0,0396 allí:
el pequeño valor negativo procede de ampliar también cotas de no negatividad;
no se interpreta como un costo físicamente factible ni como valor nativo reportado.
Los otros dos patrones nive son inviables exactamente y factibles con lambda=1.

## Sensibilidad ajustada de nive

![Curva de pérdida máxima certificada](objective-sensitivity.png)

Los puntos son óptimos certificados; las líneas unen muestras y no certifican
la interpolación. Las verticales marcan umbrales exactos para permitir una pérdida
del 1 % (objetivo umbral redondeado hacia arriba a múltiplos de 2^-40).

| Solver | Semilla | v(0) | Umbral lambda | Factor seguro diádico |
|---|---:|---:|---:|---:|
'''+mdtable(cases)+f'''

En Gurobi el umbral es de costo; en HiGHS es de factibilidad, magnitudes distintas.
Los umbrales positivos HiGHS indican la mínima ampliación común que vuelve
factible ese patrón. No son umbrales de un solver ni parámetros operativos.
Los enteros y sus cotas nunca se relajan.

Para los diez patrones factibles, los umbrales al 1 % van de aproximadamente
1,489e-8 a 3,187e-8. La optimización ajustada y la cota dual fija dan el mismo
factor diádico en los diez casos. Por tanto, el gran Delta al presupuesto completo
no implica que sea inútil cerca de cero: protege correctamente la pérdida pequeña.
No se obtiene aquí una mejora de factor seguro por reoptimizar el dual.

## Presupuestos selectivos que protegen el costo

Sea pi un dual de v(0), con todas las cotas continuas escritas como filas.
Se reducen por el factor seguro solo los presupuestos con multiplicador no nulo.
Los demás permanecen iguales. La misma dualidad da costo >= v(0)-factor*Delta,
y factor*Delta<=epsilon. Las igualdades comparten presupuesto para ambos lados.

La primera variante cambia **40/2.836 filas (1,41 %)** y reduce presupuestos de
cota de {bound_min} variables continuas. Los diez LP selectivos tienen primal/dual
exacto y cumplen el límite del 1 %. La comprobación siguiente conserva **todas**
las cotas: su contribución al deterioro es aproximadamente 0,0396, muy inferior al margen
del 1 %. Se asigna el margen restante a las filas activas y se prueba la
protección con el primal y dual existentes, sin otra llamada LP. Basta reducir
40 filas; los otros presupuestos quedan intactos. No hay intervalos de factores
incompatibles con ventana [1e-9,1e9] e hipótesis exportada epsilon=1e-6, tanto
para la variante uniforme como selectiva. Admisibilidad no prueba rendimiento.

En las 12 entregas nativas con patrón factible de nive, esta asignación conserva
{v['row_only_budget_native_deliveries_accepted']} y rechaza los cuatro ceros Gurobi. Las cuatro salidas HiGHS
inviables necesitan sus certificados de patrón; no están cubiertas por estas
precisiones calculadas para patrones factibles.

La garantía requiere conocer el patrón y su certificado. Cambiar los enteros
exige otro certificado: proteger el costo de patrones factibles no certifica
la factibilidad de los otros dos. Estos presupuestos no se presentan como una
política global de exportación ni como mejora demostrada sobre controles nativos.

## Filtro de aceptación y comparación con reparación

Se acepta un costo nominal C solo si existe un testigo exacto con los mismos
enteros y costo U<=C+epsilon, epsilon=max(1e-6,abs(U)/100). Esto garantiza una
continuación de costo no mayor que C+epsilon. Es protección unilateral; no es
una cota de exceso de costo, un gap ni optimalidad global.

En el replay de los 80 tratamientos, el filtro conserva 64 entregas nominales,
corrige cuatro ceros Gurobi y se abstiene en 12 casos (ocho sin entrega previa
y cuatro salidas con patrón inviable HiGHS). Los dos patrones HiGHS se repiten.
La reparación exacta con la misma cache conserva 28 entradas ya exactas,
corrige 40 y se abstiene en los mismos 12. El filtro conserva 36 entregas
adicionales sin activar corrección; no evita las llamadas para adquirir testigos.
Son acciones del flujo, no recuentos de vectores distintos: convertir un testigo
racional puede devolver las mismas coordenadas binary64 del punto original.

Ambos usan las mismas {v['shared_certificate_acquisitions']} adquisiciones LP por patrón, con costo observado
agregado {v['shared_acquisition_seconds']:.3f} s. Esa imputación retrospectiva no es un ensayo end-to-end.
La reparación ya proporciona la misma existencia de continuación; no se reclama
una ventaja de trabajo solver o confiabilidad frente a ella. La mejora concreta
es la regla explícita para informar costo respaldado y abstenerse/corregir.

## Verificación, límites y decisión

Se comprobaron {v['lp_native_outcomes']['optimum_certified']} certificados óptimos nativos y 12 rayos de infeasibilidad de
los LP ampliados. Un LP de umbral devolvió un error numérico: se guarda intacto.
Su umbral cero se prueba sin resolver de nuevo, usando el primal ya certificado
de v(0) y el dual de lambda>=0. No se oculta como una resolución exitosa.

Una corrección del constructor, detectada por los tests antes de la primera
llamada LP, preservó los coeficientes de las cotas de lambda. Se conservan el
diseño anterior y la corrección pre-solve; no cambian muestras o parámetros.
Los costos totales adicionales fueron {v['new_lp_total_seconds']:.3f} s, de los cuales {v['new_lp_solver_seconds']:.3f} s fueron
llamadas al ejecutable. Preparación, replay y construcción documental se miden
fuera; no extrapolar el promedio a otros tamaños. La representación es la
canónica binary64; en nive todos los literales originales son exactos en ella.

**Conclusión de investigación:** hay un diagnóstico ajustado y una asignación
selectiva verificable que protege el costo de un patrón ya auditado. Hay señal
fuera de nive en control, con límites explícitos sobre potencial frente a observado.
Todavía no hay una ventaja algorítmica frente a reparación exacta ni protección
preventiva para enteros desconocidos. No se amplía OMS v1.3.5 ni se anuncia otro
paper a partir de esta tanda.

## Reproducción y antecedentes

```bash
python3 exploration/oms-objective-budget-20261014/independent_check.py
python3 -m pytest -q exploration/oms-objective-budget-20261014/test_rational_lp.py exploration/oms-objective-budget-20261014/test_policy.py
python3 exploration/oms-objective-budget-20261014/write_report.py
```

El replay usa Python/NumPy y ninguna llamada solver. La figura requiere Matplotlib.
Los seis tests cubren signos, estacionariedad de variables libres, rayos,
igualdades, dominios enteros, cotas de lambda y reglas de aceptación de costo.
El paquete valida hashes, reconstrucción independiente de cada LP desde el modelo
original, todos los primales/duales y el PDF recompilado desde una extracción limpia.

La sensibilidad y dualidad empleadas son conocidas: véase la sección 5.6 de
[Boyd–Vandenberghe](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf).
La aritmética racional sigue las capacidades de
[SoPlex exacto](https://soplex.zib.de/doc/html/EXACT.php).
La reparación y certificación tienen antecedentes como
[Eifler–Gleixner](https://arxiv.org/abs/2101.09141).
El aporte comprobado aquí es la aplicación, medida y trazabilidad del diagnóstico,
no inventar esas herramientas matemáticas.
'''
    (HERE/'RESULTADOS.md').write_text(md)
    t=r'''\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage[spanish]{babel}
\usepackage{lmodern,amsmath,amssymb,booktabs,graphicx}\usepackage[margin=1.9cm]{geometry}
\usepackage[hidelinks]{hyperref}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\begin{document}\begin{center}{\Large Presupuestos de residuos y protección del costo}\\[4pt]
{\large Sensibilidad exacta y aceptación con certificado}\\[3pt]
14 de octubre de 2026 --- investigación separada de OMS\end{center}
\textbf{Resultado útil.} El diagnóstico ajustado mide cuánto pueden abaratar
el objetivo los presupuestos numéricos. En nive basta reducir los presupuestos
de 40 de 2836 filas, conservando todas las precisiones de cotas continuas,
para proteger el costo al 1\% de un patrón auditado. Diez casos certificados.
No es un presupuesto universal ni una ventaja de solver demostrada.
\section*{Diseño y datos}
Las 72 entregas de los 80 tratamientos previos contienen 41 patrones enteros
distintos: 12 de nive y 29 de los otros cuatro modelos. Los controles fuertes,
solvers y semillas son los anteriores; no se ejecuta otro MILP. Se conservan
ocho ausencias de entrega. L2/Budget de nive repiten patrones por semilla.
El estudio es retrospectivo y control es referencia conocida.

178 LP fijados antes de resolver: $v(0),v(1)$ para los 41 patrones, siete
escalas diádicas intermedias y el umbral de factibilidad para los 12 de nive.
Después se aplicó la regla predefinida: diez umbrales de pérdida al 1\% y diez
validaciones de factor seguro. Una extensión selectiva posterior añadió diez
LP con protocolo separado. Total: 208 llamadas, 2 s por LP y watchdog 4 s.
\section*{Vulnerabilidad potencial del objetivo}
Para enteros $z$ fijados y cotas enteras exactas,
\[
v_z(\lambda)=\min_y\{c_I^\top z+c_C^\top y:\text{filas y cotas continuas
con presupuestos }\lambda\delta,\lambda\beta\}.
\]
Si el patrón es factible exactamente, $D_z(\lambda)=v_z(0)-v_z(\lambda)$.
Mide deterioro potencial; no el error observado en cada salida de un solver.
Se usa $\delta_r=10^{-4}\max(1,|b_r|)$, $\beta_j=10^{-4}$: precisiones
algebraicas experimentales, sin interpretación de tolerancia operativa.
\begin{center}\small\begin{tabular}{@{}lrrr@{}}\toprule
Modelo & Patrones & Inviables & Pérdida potencial (\%)\\\midrule
'''+textable(comparisons)+r'''
\bottomrule\end{tabular}\end{center}
La pérdida se divide por $|v(0)|$ y se muestra como rango de patrones factibles.
En nive, $v(1)\approx-0.0396$: la mínima negatividad procede de ampliar cotas de
no negatividad. No se interpreta como costo físicamente factible o valor nativo.
Control permite deterioros de 4.82--7.65\%, mientras los otros modelos no
muestran esa vulnerabilidad significativa. No se atribuye a los solvers.
\newpage
\section*{Caracterización exacta de nive}
\begin{center}\includegraphics[width=.96\linewidth]{objective-sensitivity.pdf}\end{center}
Puntos: mínimos certificados; líneas: unión visual de muestras, sin garantía
de interpolación. Verticales: primeros presupuestos que permiten una pérdida
del 1\%, con objetivo umbral redondeado hacia arriba a múltiplos de $2^{-40}$.
\begin{center}\small\begin{tabular}{@{}lrrrr@{}}\toprule
Solver & Semilla & $v(0)$ & Umbral $\lambda$ & Factor seguro\\\midrule
'''+textable(cases)+r'''
\bottomrule\end{tabular}\end{center}
En Gurobi se muestra el umbral de costo. En HiGHS, el de factibilidad:
la mínima ampliación común que permite una continuación del patrón inviable.
No son la misma magnitud ni parámetros de un solver.

Los diez patrones factibles tienen umbrales de costo al 1\% entre
$1.489\,10^{-8}$ y $3.187\,10^{-8}$. El dual fijo y el análisis ajustado dan
los mismos factores diádicos seguros en los diez casos. Un $\Delta$ muy
conservador en $\lambda=1$ puede ser útil cerca de cero; aquí reoptimizar el
dual no permite un factor seguro mayor al nivel de protección elegido.
\section*{Asignación selectiva con protección comprobada}
Con las cotas continuas escritas como filas y dual $\pi\le0$ de $v(0)$,
\[
c(y)\ge v(0)-\sum_i|\pi_i|w_i',\qquad
\sum_i|\pi_i|w_i'\le\varepsilon_{\rm obj}.
\]
Se reduce por el factor seguro solo cada presupuesto $w_i$ con precio no
nulo; los demás se conservan. Una igualdad comparte presupuesto para ambos
lados. Se preservan coeficientes, objetivo, RHS, cotas y dominios originales;
cambia únicamente la región de aceptación numérica.
''' + f'''
La primera variante reduce 40/2836 presupuestos de fila (1.41\\%) y {bound_min}
presupuestos de cota. Diez LP selectivos certifican pérdida menor al 1\\%.
Después se conservan todas las cotas: su efecto permitido es aproximadamente 0.0396.
Asignar el margen restante a las filas activas prueba protección con los
certificados existentes, sin otro LP. Basta reducir 40 filas. La regla
conserva {v['row_only_budget_native_deliveries_accepted']}/12 entregas de patrones factibles y rechaza los cuatro ceros Gurobi.
''' + r'''
Los intervalos contractuales son compatibles con la ventana original y la
hipótesis exportada $10^{-6}$ en ambas variantes; no prueba rendimiento.
La garantía requiere el patrón y su certificado. Otros enteros necesitan
otra prueba, incluida su factibilidad exacta.
\newpage
\section*{Filtro de costo frente a reparación exacta}
El filtro mantiene un costo nominal $C$ si existe un testigo exacto del mismo
patrón con costo $U\le C+\varepsilon$, donde
$\varepsilon=\max(10^{-6},|U|/100)$. Garantiza una continuación de costo
no mayor que $C+\varepsilon$. Es unilateral: no acota exceso de costo,
gap u optimalidad global. Si falla, corrige con un testigo comprobado o se abstiene.
\begin{center}\begin{tabular}{@{}lrrr@{}}\toprule
Regla & Conservar entrada & Corregir & Abstenerse\\\midrule
Presupuesto primal solo &72&0&8\\
Reparación exacta, misma cache &28&40&12\\
Filtro de costo, misma cache &64&4&12\\\bottomrule\end{tabular}\end{center}
Las cuatro correcciones del filtro son ceros Gurobi; cuatro abstenciones
adicionales son salidas HiGHS con dos patrones inviables repetidos. Las ocho
ausencias originales siguen contadas. El filtro conserva 36 entradas más
sin activar corrección; no ahorra llamadas para adquirir certificados.
Son acciones del flujo: convertir el testigo racional puede devolver las
mismas coordenadas binary64 del punto original.
''' + f'''
Ambos usan {v['shared_certificate_acquisitions']} adquisiciones por patrón, con {v['shared_acquisition_seconds']:.3f} s
observados. Es imputación retrospectiva sobre candidatos guardados, no un
ensayo end-to-end ni una comparación de velocidad. La reparación ya aporta
la misma existencia de continuación. No se reclama ventaja de trabajo solver.
''' + r'''
\section*{Comprobación y alcance matemático}
La ampliación tiene la forma $Ay\le b+\lambda w$, con todas las variables
libres y sus cotas como filas. El checker exige $\pi\le0$, $A^\top\pi=c$,
factibilidad primal exacta e igualdad del costo primal y dual. Un rayo de
inviabilidad debe tener $A^\top\pi=0$, $\pi^\top b>0$. Verifica cada fila
contra los datos originales, sin importar el constructor experimental.

Por dualidad fuerte, optimizar sobre todos los duales factibles da $v(\lambda)$;
mantener un dual de $v(0)$ da una cota suficiente. Restringirse a duales
óptimos en cero no representa toda la sensibilidad global. La función valor
es convexa y no creciente en la región factible; las muestras verifican ambas
propiedades. Los umbrales se obtienen minimizando $\lambda$, con o sin la
fila adicional de costo, y se respaldan con primal/dual exacto.

La sensibilidad, dualidad y reparación racional son herramientas conocidas.
Aquí se mide su utilidad y alcance, sin anunciar un nuevo teorema o algoritmo
MILP globalmente certificado.
\newpage
\section*{Reproducibilidad y resultados adversos}
''' + f'''
Se verifican {v['lp_native_outcomes']['optimum_certified']} certificados óptimos nativos y 12 rayos.
Un LP de umbral terminó con error numérico, conservado íntegramente. Su
umbral cero se prueba sin repetirlo: primal ya certificado de $v(0)$ y dual
de $\\lambda\\ge0$. No se cuenta como resolución exitosa.

Las 208 llamadas costaron {v['new_lp_total_seconds']:.3f} s de ciclos completos; {v['new_lp_solver_seconds']:.3f} s
fueron llamadas al ejecutable y {v['native_certificate_check_seconds']:.3f} s comprobaciones de certificados.
Preparación compartida, replay y documentos se registran aparte. No se
extrapola el promedio a instancias mayores.
''' + r'''
Un test detectó antes de cualquier llamada LP una pérdida de coeficientes
en las cotas de $\lambda$ del constructor. Se conservan el diseño anterior y
la corrección pre-solve; muestras y parámetros permanecen iguales. Los
seis tests comprueban signos, estacionariedad, rayos, igualdades, cotas de
$\lambda$ y aceptación del costo, incluidos fallos que exigen abstenerse.

Los racionales corresponden al modelo canónico binary64; todos los literales
originales de nive son exactos en esa representación. Los demás modelos
conservan sus cuentas de redondeo y no se certifica su versión decimal ideal.
El ZIP incluye fuentes, diseños, copias MPS, puntos, logs, primales, duales,
rayos, curvas, presupuestos y tiempos. Binarios y licencias de solver se excluyen.
\section*{Decisión y siguiente barrera científica}
Hay un diagnóstico ajustado y una asignación selectiva comprobable que
protege el costo de patrones conocidos. También hay vulnerabilidad potencial
en control, distinta de un error observado. El filtro evita mantener ceros
sin respaldo y puede conservar entregas suficientemente precisas.

Todavía no hay ventaja algorítmica demostrada frente a reparación exacta
con la misma cache, ni presupuestos preventivos para enteros desconocidos.
La aportación actual no justifica otro paper o una tercera contribución.
Se mantiene OMS v1.3.5 sin cambios, con este estudio independiente.
\section*{Reproducción y fuentes primarias}
\begin{verbatim}
python3 exploration/oms-objective-budget-20261014/independent_check.py
python3 -m pytest -q exploration/oms-objective-budget-20261014/
python3 exploration/oms-objective-budget-20261014/write_report.py
\end{verbatim}
Replay: Python y NumPy, sin solvers; tests: pytest; figura: Matplotlib.
El paquete verifica todos los hashes antes y después, vuelve a generar texto
y figura y recompila este PDF desde una extracción limpia.

\href{https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf}{Boyd--Vandenberghe,
sección 5.6}: dualidad, perturbación y sensibilidad conocidas.
\href{https://soplex.zib.de/doc/html/EXACT.php}{SoPlex}: LP racional exacto.
\href{https://arxiv.org/abs/2101.09141}{Eifler--Gleixner}: antecedentes de
reparación y certificación racional MILP. Modelos externos:
\href{https://miplib.zib.de/tag_numerics.html}{MIPLIB Numerics}.
\end{document}
'''
    (HERE/'objective-note.tex').write_text(t)
    print('Regenerated independent sensitivity report, source and figure')


if __name__=='__main__':main()
