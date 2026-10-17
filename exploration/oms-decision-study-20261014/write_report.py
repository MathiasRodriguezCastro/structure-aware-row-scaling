#!/usr/bin/env python3
"""Deterministic separate research report; all numerical tables use audited records."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def tex(s):
    return str(s).replace('_', r'\_').replace('%', r'\%').replace('&', r'\&')


def main():
    out = HERE / 'confirmation'; design = read(out / 'design.json')
    audit = read(out / 'independent-verification.json')
    records = [read(out / 'runs' / t['model'] / f"{t['arm']}-s{t['seed']}" / 'run.json') for t in design['queue']]
    assert len(records) == audit['assigned_treatments'] == 80 and audit['execution_failures'] == 0
    assert audit['accepted_sources_with_nominal_mu_above_one'] == 48
    assert audit['source_points_with_nominal_mu_at_most_one'] == 12
    md_table = []; latex_table = []
    for arm in design['arms']:
        rs = [r for r in records if r['arm'] == arm]
        passed = sum(r['delivered'] for r in rs); before = sum(r['source_point_budget_met'] for r in rs)
        repairs = sum(len(r['repair_attempts']) for r in rs); seconds = sum(r['total_seconds'] for r in rs)
        abstentions = sum(r['outcome'] == 'contract_abstention' for r in rs)
        md_table.append(f'| {arm} | {before}/10 | {passed}/10 | {repairs} | {abstentions} | {seconds:.3f} |')
        latex_table.append(f'{tex(arm)} & {before}/10 & {passed}/10 & {repairs} & {abstentions} & {seconds:.3f}'+r'\\')
    control = []; control_tex = []
    for seed in design['seeds']:
        for arm in ('Tight-check', 'IntegralityFocus-check', 'Base-check-repair', 'Budget-check-repair', 'L2-check-repair'):
            r = next(v for v in records if v['model'] == 'control30-3-2-3' and v['seed'] == seed and v['arm'] == arm)
            control.append(f"| {seed} | {arm} | {r['delivered_objective']:.6f} | {r['total_seconds']:.3f} |")
            control_tex.append(f"{seed} & {tex(arm)} & {r['delivered_objective']:.6f} & {r['total_seconds']:.3f}"+r'\\')
    attempts = [a for r in records for a in r['repair_attempts']]
    tmin, tmax = min(a['total_seconds'] for a in attempts), max(a['total_seconds'] for a in attempts)
    source_good = sum(r['source_point_budget_met'] for r in records)
    dev = read(HERE / 'development-repair' / 'summary.json')
    exact_dev = next(r for r in dev['results'] if r['mode'] == 'exact')
    bounds = read(out / 'bound-discrepancies.json')
    assert len(bounds) == 2 and all(r['arm'] == 'Tight-check' for r in bounds)
    upper = bounds[0]['exact_feasible_upper_bound']
    bounds_table = '\n'.join(f"| {r['seed']} | {r['reported_bound']:.2f} | {r['exact_feasible_upper_bound']:.2f} | {r['reported_bound']-r['exact_feasible_upper_bound']:.2f} |" for r in bounds)
    bounds_tex = '\n'.join(f"{r['seed']} & {r['reported_bound']:.2f} & {r['exact_feasible_upper_bound']:.2f} & {r['reported_bound']-r['exact_feasible_upper_bound']:.2f}"+r'\\' for r in bounds)
    md = f'''# Reparación, aceptación y decisión numérica: resultados del seguimiento

**Conclusión:** verificar y reparar recuperó tres entregas que fallaban en Base,
pero este seguimiento no demuestra una ventaja propia del escalamiento contractual.
Tolerancias estrictas e IntegralityFocus igualaron su aceptación. La reparación
fue barata en estos casos, con una pérdida importante de calidad del objetivo en
control30-3-2-3. Se conserva como investigación independiente, sin agregar otra
contribución al paper OMS v1.3.5.

## Diseño y alcance

Se fijaron 80 tratamientos antes de resolver: cinco modelos, semillas 11 y 23 y
ocho alternativas, con orden aleatorio registrado. Los horizontes Kondili H14 y
H16 son nuevos; los tres modelos MIPLIB son los seleccionados en el piloto, con
semillas nuevas. Eso añade confirmación limitada, no nuevas familias ni una muestra
representativa. La calibración anterior, semilla 17, queda fuera de los denominadores.

Gurobi 13.0.2, cuatro hilos, presolve y escalado interno automáticos, gap 1 %, MILP
hasta 15 s y referencia de 20 s para el ciclo. Se aplican exactamente las reglas
diádicas existentes. HiGHS 1.15.1 reoptimiza el LP con los enteros fijados; SoPlex
8.1.0/GMP 6.2.1 queda como reparación exacta condicional. No se reajustaron factores,
presupuestos o parámetros después de ver resultados.

Los presupuestos STN siguen siendo 1e-5 kg (10 mg) para material, 1e-5 para lógica
y 1e-3 en unidades monetarias de la fuente; son objetivos numéricos del estudio.
MIPLIB utiliza 1e-4 max(1, |RHS|), en unidades algebraicas experimentales. Una
entrega debe satisfacer todas las filas y cotas dentro de sus presupuestos y los
dominios enteros exactamente. La garantía contractual MIPLIB se refiere al punto
crudo; el redondeado se comprueba después, sin promesa uniforme de redondeo.

## Aceptación y costo completo

| Tratamiento | Fuente tras redondear | Entregas verificadas | LP de reparación | Abstenciones contractuales | Suma de tiempos, s |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(md_table)+f'''

Todas las cuentas tienen denominador 10, incluidos los dos contratos incompatibles.
No son probabilidades poblacionales. Hay {audit['native_calls']} llamadas MILP,
{source_good} puntos fuente aceptables y {audit['delivered_points_independently_checked']}
entregas verificadas. Los {len(attempts)} LP condicionales recuperaron la entrega;
su costo incluyó preparar, resolver, comprobar y guardar sus certificados y estuvo
entre {tmin:.4f} y {tmax:.4f} s. No se necesitó el LP exacto en esta confirmación.
Dos puntos de HiGHS resultaron también factibles exactos al comprobarlos racionalmente.

Los tiempos de la tabla incluyen selección real de factores, exportación,
importación y cotejo nativo, MILP, verificación y reparación condicional. La
persistencia exterior se mide aparte; los archivos auxiliares de reparación están
dentro del tiempo de reparación. No hubo excesos de 20 s ni errores de ejecución.
**Desviación de registro:** la construcción inicial común de los modelos no se
cronometró por separado, pese a la frase correspondiente del protocolo. No se
presenta una suma que incluya esa etapa. Se documenta en audit-deviations.json.
El entorno y los tiempos por etapa quedan registrados. No se infiere superioridad
general en velocidad de dos semillas o de sumas con objetivos diferentes.

## Precisión recuperada y calidad del objetivo

En control30-3-2-3, reparar Base entrega costo 26,248128, desde puntos crudos
no entregables de −39,917360 (semilla 11) y −23,049913 (23). Budget reduce el
costo reparado a 24,661027 y L2 entrega 33,373658. Los controles Tight e
IntegralityFocus entregan costos cercanos a 1,27: son mucho mejores, aunque usan
aproximadamente 15 s. Un punto reparado rápido con peor objetivo no equivale a
una optimización rápida de igual calidad. No se conserva el gap del punto fuente.

| Semilla | Tratamiento | Objetivo entregado, minimización | Ciclo, s |
|---|---|---:|---:|
'''+ '\n'.join(control)+f'''

En Kondili todos los tratamientos cumplen, sin reparaciones. El diagnóstico
elige Budget y no mejora la aceptación del control. En cinca, Base, Tight e
IntegralityFocus cumplen; NumericFocus falla en ambas semillas. L2 requiere
una reparación en semilla 23. Budget se abstiene por 96 intervalos incompatibles.
En ta1-UUM se repara Base para semilla 23, con cambio de objetivo de 0,282 unidades.
La ventaja observada allí proviene del LP de reparación, no del contrato.

## Testigos exactos y contradicciones de cotas

Un LP flotante de ta1-UUM entrega un vector binary64 que satisface **exactamente**
todas las restricciones de la representación canónica. Su objetivo exacto,
comprobado con Fraction, se muestra como {upper:.2f}. Es una cota superior primal
del mismo modelo original. Las dos llamadas Tight declaran terminación óptima y
reportan cotas inferiores que la exceden:

| Semilla Tight | Cota inferior reportada | Testigo factible exacto | Diferencia |
|---|---:|---:|---:|
{bounds_table}

El testigo mejora también sus objetivos en más de 1 %. Importación y escalado se
cotejaron contra el mismo JSON original; la comparación no mezcla modelos. El
checker usa una guarda de max(1e-6, 8 ulp(cota)), muy inferior a estas diferencias.
Por lo tanto, esos informes de cota/gap quedan contradichos para el modelo
canónico. No se afirma haber certificado el óptimo global, ni que las demás cotas
sean válidas por ausencia de contradicción. No se atribuye una causa específica
al presolve, al escalado interno o al solver sin experimentos adicionales.
El checker también vuelve a leer los tres MPS originales, sin llamar al solver,
y coteja coeficientes, RHS, objetivo, sentidos, cotas y dominios con los modelos
canónicos; valida los SHA-256 originales de descarga. El adapter admite únicamente
las características presentes y rechaza otras. Se aplica la interpretación
binary64 de literales y los defaults documentados en el
[formato MPS de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/reference/fileformats/modelformats.html).

## Mecanismo, entrega y garantías

Los máximos coeficientes enteros de los tres MIPLIB son 1,058e7, 1e17 y 1,109e7,
mientras que los máximos continuos son 1, 1,4 y 1. Al fijar enteros desaparecen
de la matriz LP los coeficientes grandes, lo que orientó la reparación. Esto no
garantiza buena condición, factibilidad del entero elegido o éxito del LP.

El ciclo comprueba el punto fuente redondeado; si falla, fija los enteros más
próximos, prueba un LP flotante y, si sigue sin entrega verificada, un LP racional
con los datos originales completos. Cada candidato se comprueba en **todas** las
filas, cotas y dominios originales. Solo devuelve una entrega que pasa. Hay a lo
sumo una llamada MILP y dos LP; la terminación depende de que los backends terminen
o respeten sus mecanismos de interrupción. El presupuesto temporal es una
referencia operativa, no una garantía de tiempo real del sistema operativo.

Una contradicción constante tras fijar enteros prueba que ese patrón no tiene
continuación exacta, no que el MILP completo sea inviable. La factibilidad racional
del LP tampoco prueba optimalidad MILP ni que convertir su testigo a float conserve
las precisiones. El desarrollo separado sí obtuvo un testigo exacto de
control30-3-2-3, costo 26,248128; la conversión también pasa. Su tiempo medido fue
{exact_dev['total_seconds']:.4f} s. Ese ensayo de desarrollo no entra en la tabla principal.

### Obstrucción de representación comprobable

Para una igualdad unaria a x = b después de fijar los enteros, sea q=b/a y sean
f− y f+ sus vecinos binary64 adyacentes. Si ambos son finitos, el menor residuo
alcanzable entre valores binary64 es min(|a f−−b|, |a f+−b|): a cada lado de q,
la distancia crece al alejarse. Si ese mínimo excede δ, ningún valor binary64
con ese patrón entero puede satisfacer el presupuesto de esa fila.

Ejemplo de comprobación, **no modelo experimental favorable**: 3x=1, 0≤x≤1.
El testigo racional x=1/3 es exacto, pero el menor residuo binary64 es 2^−54.
Con δ=2^−55 no hay entrega aceptable; con δ=2^−54 sí. Los tests comprueban ambos
casos. No se hallaron obstrucciones unarias en los casos reales del seguimiento.
Esta propiedad elemental separa factibilidad exacta y precisión de representación;
no se presenta como un teorema nuevo ni como una mejora práctica ya demostrada.

### Diagnóstico previo y error de exportación

La regla fijada eligió Budget para STN y Base con reparación reservada para los
tres MIPLIB. Logró 10/10, como Base-repair, con mayor costo de selección. En
48 puntos fuente que pasan, la cota nominal μ supera 1: la falta de garantía
suficiente sigue sin ser un predictor de fallo. Solo 12 puntos tienen μ≤1;
el checker verifica sus hipótesis de residuos exportados e integralidad y no
encuentra contradicciones de la cota cuando esas hipótesis se cumplen.

El soporte firmado de exportación ya desarrollado en el piloto es
R⁺ = Σ max[(αa_j−â_j) l_j, (αa_j−â_j) u_j] − (αb−b̂).
Bajo pertenencia del punto a la caja y residuo exportado ≤ε, la violación tras
redondear es ≤max(0,(ε+R⁺)/α+γΣ_enteros|a_j|). Para igualdad se aplican ambos
signos. Los coeficientes con error cero no necesitan cotas finitas. Aquí las
exportaciones diádicas son exactamente proporcionales, de modo que R⁺=0.
No se atribuye a ese diagnóstico una predicción o utilidad que los datos no prueban.

## Antecedentes y decisión para OMS

La reparación exacta y la certificación ya tienen antecedentes explícitos en
[Eifler y Gleixner](https://arxiv.org/abs/2101.09141) y
[Cheung, Gleixner y Steffy](https://arxiv.org/abs/1611.08832).
[SoPlex](https://soplex.zib.de/doc/html/EXACT.php) implementa LP racional;
[IntegralityFocus](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameterintegralityfocus)
es un control existente pertinente. No se reclama como novedoso verificar o
reparar. El posible desarrollo es integrar requisitos, representación, aceptación,
abstención y calidad con trazabilidad; esta muestra no demuestra una ventaja
propia de contratos que justifique una nueva contribución en el artículo.

**Decisión:** mantener el envío OMS v1.3.5. La investigación deja un ciclo ejecutado,
reparaciones y certificados reproducibles, una separación comprobada entre precisión
y optimalidad y un resultado negativo útil sobre el diagnóstico. Los resultados
no justifican ampliar el paper ni iniciar una búsqueda de casos favorables.

## Reproducción

```bash
python3 exploration/oms-decision-study-20261014/independent_check.py
python3 -m pytest -q exploration/oms-decision-study-20261014/test_repair.py
python3 exploration/oms-decision-study-20261014/write_report.py
```

Python/NumPy bastan para el checker; pytest para cinco tests. El replay no llama
solvers. El artefacto contiene protocolo, congelamiento y enmienda preejecución,
fuentes, modelos, 80 registros, puntos, logs, certificados, tiempos y hashes.
Los certificados son del **modelo canónico binary64**, no de una interpretación
racional ideal de los decimales del MPS ni de precisión física operativa.
'''
    (HERE / 'RESULTADOS.md').write_text(md)
    preamble = r'''\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{lmodern,amsmath,amssymb,booktabs,tabularx,array}
\usepackage[margin=1.85cm]{geometry}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\newcommand{\R}{\mathbb{R}}
\begin{document}
\begin{center}
{\Large Reparación, aceptación y decisión numérica}\\[3pt]
{\large Seguimiento prospectivo independiente del paper OMS}\\[3pt]
14 de octubre de 2026 --- documento de investigación
\end{center}
\textbf{Resultado.} Verificar y reparar recuperó entregas que fallaban en Base,
pero no se demuestra una ventaja propia de contratos frente a alternativas
existentes. El estudio queda separado del artículo v1.3.5.
\section*{Diseño y aceptación}
Se fijaron 80 tratamientos antes de resolver: cinco modelos, semillas 11 y 23,
ocho alternativas y orden aleatorio registrado. Kondili H14/H16 son horizontes
nuevos de la misma fuente independiente; los tres MIPLIB son los del piloto,
con semillas nuevas. No son nuevas familias ni una muestra representativa.
La calibración previa, semilla 17, se excluye de la confirmación.

Gurobi 13.0.2, cuatro hilos, presolve y escalado interno automáticos, gap 1\%,
MILP hasta 15 s y referencia de ciclo de 20 s. Los LP condicionales usan
HiGHS 1.15.1 (hasta 2 s) y SoPlex 8.1.0/GMP (hasta 3 s restantes).
Las políticas escaladas usan exactamente el kernel diádico existente.

Se conservan los presupuestos: STN $10^{-5}$ kg (10 mg) en material,
$10^{-5}$ en lógica y $10^{-3}$ en unidades monetarias; MIPLIB
$10^{-4}\max(1,|b_r|)$ en unidades algebraicas experimentales.
Son objetivos numéricos del estudio. Una entrega debe satisfacer todas las
filas y cotas dentro de sus presupuestos y dominios enteros exactamente.
Los contratos MIPLIB cubren el punto crudo; el redondeado se comprueba después.
\begin{center}\small
\begin{tabular}{@{}lrrrrr@{}}\toprule
Tratamiento & Fuente & Entrega & LP & Abst. & Suma s\\\midrule
'''
    p1 = preamble + '\n'.join(latex_table) + r'''
\bottomrule\end{tabular}\end{center}
Fuente: punto fuente tras redondear; Entrega: asignación verificada; LP:
reparaciones; Abst.: incompatibilidad contractual. Denominador diez por
tratamiento, incluyendo abstenciones. No son tasas poblacionales.
''' + f'''
Hubo {audit['native_calls']} llamadas MILP y {audit['delivered_points_independently_checked']}
entregas verificadas. Los {len(attempts)} LP flotantes condicionales recuperaron
la entrega, con costo de {tmin:.4f}--{tmax:.4f} s. No se llamó al LP exacto en
confirmación; dos puntos de HiGHS también resultaron factibles exactos.
''' + r'''
La suma incluye selección, exportación, importación y cotejo, MILP,
verificación y reparación. La persistencia exterior se mide aparte; los
archivos auxiliares del LP están incluidos en reparación. No hubo errores
ni excesos de 20 s. \textbf{Desviación documentada:} la construcción común
inicial no se cronometró, pese a una frase del protocolo. No se incluye en
estas sumas. Dos semillas no permiten inferir velocidad general.
\newpage
\section*{Precisión, costo y calidad del objetivo}
En \texttt{control30-3-2-3}, Base-repair recupera precisión desde objetivos
crudos no entregables de $-39.917360$ y $-23.049913$, pero entrega costo
$26.248128$. Los controles estrictos entregan aproximadamente $1.27$ y
usan unos 15 s. La reparación rápida de peor objetivo no equivale a
optimización rápida de igual calidad. No se transfiere el gap de la fuente.
\begin{center}\small
\begin{tabular}{@{}rlrr@{}}\toprule
Semilla & Tratamiento & Costo entregado & Ciclo s\\\midrule
''' + '\n'.join(control_tex) + r'''
\bottomrule\end{tabular}\end{center}
En Kondili todas las alternativas pasan sin reparación. En cinca, Base,
Tight e IntegralityFocus pasan y NumericFocus falla en ambas semillas.
L2 necesita reparar una entrega; Budget se abstiene por 96 intervalos
incompatibles. En \texttt{ta1-UUM}, Base necesita reparación en semilla 23,
con cambio de objetivo de 0.282 unidades. La recuperación es del LP,
no del contrato. Los 80 registros y tiempos por etapa quedan conservados.
\section*{Contradicciones independientes de cotas}
Un punto binary64 reparado de \texttt{ta1-UUM} satisface exactamente todas
las filas, cotas y dominios del modelo canónico, comprobados con aritmética
racional. Su objetivo constituye una cota superior factible del mismo
modelo. Las llamadas Tight terminan con etiqueta óptima y cotas inferiores
que la contradicen:
\begin{center}\small
\begin{tabular}{@{}rrrr@{}}\toprule
Semilla & Cota reportada & Testigo exacto & Diferencia\\\midrule
''' + bounds_tex + r'''
\bottomrule\end{tabular}\end{center}
El testigo también mejora sus objetivos en más de 1\%. La importación y
el escalado se cotejan contra los mismos datos originales: no se mezclan
modelos. La guarda numérica del checker, $\max(10^{-6},8\,\mathrm{ulp}(B))$,
es muy inferior a las diferencias observadas. No se certifica el óptimo
global ni se consideran válidas las otras cotas por no hallar contradicción.
Tampoco se atribuye una causa al presolve o escalado interno sin controles
adicionales. Precisión primal, calidad y optimalidad se conservan separadas.
\newpage
\section*{Mecanismo de reparación y garantías de aceptación}
Los tres MIPLIB tienen máximos coeficientes enteros de $1.058\,10^7$,
$10^{17}$ y $1.109\,10^7$, frente a máximos continuos de 1, 1.4 y 1.
Fijar enteros retira los coeficientes grandes de la matriz del LP. Esta
observación orienta la reparación, pero no garantiza buena condición,
factibilidad del patrón o éxito del LP.

El ciclo selecciona y exporta, resuelve una vez y comprueba el punto
redondeado. Si falla, fija los enteros más próximos, reoptimiza el LP y
comprueba todas las restricciones originales. Si aún falla la entrega,
intenta un LP racional y comprueba por separado el testigo y su conversión
a binary64. Si nada pasa, se abstiene.

\textbf{Propiedad de aceptación.} Defina $V_\delta(y)$ como la verificación
de todas las filas y cotas bajo sus presupuestos originales y dominios
enteros exactos. Cada instrucción que devuelve un punto se ejecuta solamente
después de comprobar $V_\delta(y)$. Por tanto, todo punto devuelto satisface
$V_\delta$. Es una garantía del filtro, independiente de las etiquetas
del solver. No garantiza encontrar un punto ni certificar su optimalidad.
El número de intentos está acotado por un MILP y dos LP; la terminación
depende de que los backends terminen o sean interrumpidos. Los 20 s son
una referencia operativa, no una garantía de tiempo real.

Se sustituyen los enteros en el RHS con aritmética racional sobre los
datos binary64 originales. El LP racional se escribe con decimales completos,
sin un nuevo redondeo del RHS. Una contradicción en una fila constante
prueba ausencia de continuación exacta de ese patrón, no inviabilidad
global MILP. Un testigo exacto es primal; no certifica optimalidad MILP.
''' + f'''
El desarrollo separado obtuvo un testigo exacto para control, con costo
26.248128, entrega flotante también verificada y tiempo
{exact_dev['total_seconds']:.4f} s. Es desarrollo, excluido de la tabla prospectiva.
''' + r'''
\section*{Obstrucción de representación}
Tras fijar enteros, considere $a x=b$, $a\ne0$, y $q=b/a$. Sean
$f^-<q<f^+$ los dos vecinos binary64 adyacentes, ambos finitos. Entonces
\[
\min_{f\in\mathbb F_{64}}|af-b|
=\min\{|af^--b|,|af^+-b|\}.
\]
En cada lado de $q$, $|a|\,|f-q|$ crece al alejarse; ningún otro valor
flotante tiene menor residuo. Si ese mínimo excede $\delta$, la fila no
tiene entrega binary64 que cumpla su presupuesto para esos enteros,
aunque admita un testigo racional exacto. Las cotas de variables no pueden
eliminar esa imposibilidad. El diagnóstico omite casos sin vecinos finitos.

Ejemplo de comprobación: $3x=1$, $0\le x\le1$. El testigo racional es
$1/3$ y el mínimo residuo binary64 es $2^{-54}$. Con $\delta=2^{-55}$
no hay entrega; con $\delta=2^{-54}$ sí. Cinco tests incluyen esa frontera,
contradicciones enteras, dominios y decimales exactos. No hubo obstrucciones
unarias en los casos reales. Es cuantización elemental, sin novedad
matemática reclamada ni beneficio práctico general demostrado.
\newpage
\section*{Diagnóstico previo y exportación}
La regla congelada eligió Budget para STN y Base con reparación reservada
para MIPLIB. Logra 10/10, como Base-repair, con mayor trabajo de selección.
En 48 puntos fuente que pasan, la cota nominal $\mu$ supera uno. La falta
de garantía suficiente no predice un fallo. Solo 12 puntos tienen
$\mu\le1$; el checker comprueba las hipótesis exportadas e integrales
y no encuentra contradicciones cuando son satisfechas.

El tratamiento del error de exportación, ya implementado en el piloto,
usa el soporte firmado de la caja original:
\[
R^+=\sum_j\max\{(\alpha a_j-\hat a_j)l_j,
(\alpha a_j-\hat a_j)u_j\}-(\alpha b-\hat b).
\]
Si $x\in[l,u]$ y $\hat a^\top x-\hat b\le\varepsilon$, descomponer
el residuo da
\[
a^\top x-b\le(\varepsilon+R^+)/\alpha.
\]
Si cada entero cambia a lo sumo $\gamma$ al redondear, la violación final
está acotada por
\[
\max\left\{0,\frac{\varepsilon+R^+}{\alpha}
+\gamma\sum_{j\in I}|a_j|\right\}.
\]
Para igualdades se consideran ambos signos. Términos con error cero no
necesitan cotas finitas. Aquí las exportaciones diádicas son exactamente
proporcionales y $R^+=0$. Se distinguen límite nominal, hipótesis observadas
y residuo efectivamente verificado, sin atribuir capacidad predictiva.
\section*{Antecedentes y decisión para OMS}
La reparación exacta y los certificados tienen precedentes explícitos:
Eifler y Gleixner (2021) y Cheung, Gleixner y Steffy (2016/2017).
SoPlex implementa LP racional e IntegralityFocus es un control existente
pertinente. Verificar o reparar no se reclama como idea novedosa.
La posible investigación es integrar requisitos, representación, aceptación,
abstención y calidad con trazabilidad. La muestra actual no demuestra una
ventaja propia del contrato frente a esos controles.

\textbf{Decisión: conservar el envío v1.3.5.} Quedan un ciclo realmente
ejecutado, reparaciones, certificados reproducibles y una separación
comprobada entre precisión y optimalidad. No se añade una contribución
ni una tabla al paper con estos resultados, ni se buscan casos favorables.
\section*{Reproducción y fuentes}
El checker independiente no importa el runner ni los solvers. Recomprueba
78 fuentes, 71 entregas, 11 candidatos LP, 9975 factores y 96 intervalos
incompatibles; coteja también los tres MPS originales y el desarrollo. Python/NumPy y
pytest bastan para replay y tests. Los programas, protocolos, enmienda
pre-ejecución, modelos, fuentes originales, logs, tiempos, puntos y hashes
se conservan en el artefacto. Los certificados se refieren al modelo
canónico binary64, no a decimales MPS racionales ideales o estándares físicos.

\small
\href{https://arxiv.org/abs/2101.09141}{Eifler y Gleixner: exact rational MIP (2021).}\\
\href{https://arxiv.org/abs/1611.08832}{Cheung, Gleixner y Steffy: verifying integer programming results.}\\
\href{https://soplex.zib.de/doc/html/EXACT.php}{SoPlex: exact LP and references to Gleixner--Steffy.}\\
\href{https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html}{Gurobi: IntegralityFocus and numerical controls.}\\
\href{https://github.com/jckantor/STN-Scheduler}{STN-Scheduler: Kondili source, pinned MIT generator.}\\
\href{https://miplib.zib.de/tag_numerics.html}{MIPLIB 2017: Numerics collection and original MPS sources.}
\end{document}
'''
    (HERE / 'decision-note.tex').write_text(p1)
    print('Regenerated RESULTADOS.md and decision-note.tex from 80 audited treatments')


if __name__ == '__main__':
    main()
