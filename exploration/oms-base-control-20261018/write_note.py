#!/usr/bin/env python3
"""Brief report from completed reader-only replays; never invokes an optimizer."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    d=json.loads((HERE/'VALIDATION.json').read_text())
    c=json.loads((HERE/'confirmation/VALIDATION.json').read_text())
    rows=list(csv.DictReader((HERE/'per-model.csv').open()))
    a={r['control']:r for r in d['paired_comparisons'] if r['budget']==100}
    b={r['control']:r for r in c['paired']}
    md=['# Budget-L2 frente al modelo sin escalado externo','',
        '18 de octubre de 2026. Control dirigido del resultado favorable de OMS.','',
        '**Sí: hay una ventaja de trabajo frente a Base y Base-tight en esta muestra.**',
        'Los tres métodos cumplen todos los presupuestos en 18/18 llamadas, sin',
        'contradicciones de cota/cierre detectadas. A 100 m³, el deterioro máximo',
        'del costo candidato de Budget-L2 es inferior al 0,1%.','',
        '| Comparador | Trabajo Budget/control | Menor trabajo | Tiempo completo intercalado | Menor tiempo |',
        '|---|---:|---:|---:|---:|']
    for p in ['Base','Base-tight']:
        md.append(f"| {p} | {a[p]['gm_work_ratio']:.6f} | {a[p]['cheaper_pairs']}/18 | {b[p]['paired_full_time_ratio']:.6f} | {b[p]['cheaper_time_pairs']}/18 |")
    md+=['','Se agregan 36 controles (6 modelos × 3 semillas × 2 políticas) y se',
        'reutilizan 36 llamadas Budget-L2 de 30/100 m³. Presolve automático,',
        'IntFeasTol=1e-9, potencia 0,01 MW, Gurobi 13.0.2, cuatro hilos, 120 s,',
        'gap solicitado 1%. Base mantiene el escalado interno automático;',
        'Base-tight cambia solo FeasibilityTol a 1e-9. No se cambia el generador.',
        'El diseño es posterior a los resultados anteriores y anterior a estos controles.','',
        'Se verifican exactamente las 10.080 filas originales antes/después de',
        'redondear, cotas, dominios, objetivos y 18 testigos racionales existentes',
        'de las representaciones realmente resueltas. No se adquieren nuevos LPs.','',
        'Los seis modelos mejoran en media frente a ambos controles. En instance031',
        'la razón contra Base es 0,993: una mejora pequeña; una llamada Base es',
        'ligeramente más barata que Budget-L2. Se conservan todos los pares.','',
        'El resultado pasa el filtro fijado de trabajo, precisión y calidad.',
        'Se fijan entonces 54 repeticiones a 100 m³, en 18 bloques consecutivos',
        '(modelo, semilla), con orden aleatorio de las tres políticas por bloque.',
        'Solo esas mediciones contemporáneas se usan para comparar segundos.',
        'Son más rápidos 9/18 pares ante cada control; los modelos cortos 005,022,031',
        'pagan el costo de preparación y resultan más lentos.',
        'Incluyen proceso fresco, generación una vez, selección/exportación cuando',
        'corresponde, importación/cotejo, solver, extracción, verificación y persistencia.',
        'Compilación y adquisición histórica de testigos son costos separados.','',
        f"Cumplen {c['both_budgets_pass']}/54; contradicciones detectadas de cota/cierre: {c['bound_flags']}/{c['completion_flags']}; límites: {c['timed_out']}.",
        f"Coinciden {c['same_native_endpoint_as_prior']}/54 extremos nativos y {c['same_point_as_prior']}/54 puntos con los anteriores.",'',
        'La mejora es de esfuerzo a los presupuestos y calidad candidata comprobados.',
        'Base también cumple y obtiene residuos de agua menores. Son seis modelos',
        'conocidos de una familia y las mismas semillas, en una máquina compartida.',
        'El intercalado no equivale a aislar el hardware. Los costos candidatos no',
        'son gaps MILP igualmente certificados. Ausencia de contradicción detectada',
        'no certifica todas las cotas, optimalidad ni superioridad general.','',
        'Se incorporan los controles a OMS (resumen, introducción, Tabla 12 y S23).',
        'Se agregan 90 MILP y se reutilizan 36; los 126 puntos permiten 2.540.160',
        'comprobaciones de filas originales. La sensibilidad histórica, resultados',
        'adversos y versión v1.3.14 se conservan. El DOI sigue diferido.','',
        'Reproducción sin resolver, desde la raíz:','', '```bash',
        'python3 exploration/oms-base-control-20261018/check.py --allow-absent-historical',
        'python3 exploration/oms-base-control-20261018/confirmation.py check',
        'python3 scripts/research/oms_base_tables.py','```','',
        'El flag omite solo PDFs históricos ausentes; los insumos científicos son obligatorios.','']
    (HERE/'RESULTADOS.md').write_text('\n'.join(md))
    tex=[r'\documentclass[10pt,a4paper]{article}',r'\usepackage[margin=2.5cm]{geometry}',
        r'\usepackage[T1]{fontenc}',r'\usepackage[utf8]{inputenc}',r'\usepackage[spanish]{babel}',
        r'\usepackage{lmodern,microtype,amsmath,booktabs}',r'\usepackage[hidelinks]{hyperref}',
        r'\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}',r'\begin{document}',
        r'\begin{center}{\Large Budget-L2 frente al modelo sin escalado externo}\\',
        r'Control dirigido del resultado favorable de OMS --- 18 de octubre de 2026\end{center}']
    skip=False
    for line in md[4:]:
        if line.startswith('|---'):continue
        if line.startswith('| Comparador'):
            tex+=[r'\begin{center}\begin{tabular}{lrrrr}\toprule',
                r'Control & Trabajo relativo & Menor trabajo & Tiempo relativo & Menor tiempo\\\midrule']
            continue
        if line.startswith('| '):
            cells=[x.strip() for x in line.strip('|').split('|')]
            tex.append(' & '.join(cells)+r'\\')
            if cells[0]=='Base-tight':tex.append(r'\bottomrule\end{tabular}\end{center}')
            continue
        if line.startswith('Reproducción'):
            skip=True
            tex+=[r'\textbf{Reproducción.} Ejecutar \texttt{make research-oms-check} desde la raíz,',
                r'sin optimizar. El protocolo, diseños, puntos, logs y desgloses por modelo',
                r'están en \path{exploration/oms-base-control-20261018/}.']
        if skip:continue
        line=line.replace('%',r'\%').replace('m³',r'm$^3$').replace('×',r'$\times$')
        line=line.replace('**Sí: hay una ventaja de trabajo frente a Base y Base-tight en esta muestra.**',r'\textbf{Sí: hay una ventaja de trabajo frente a Base y Base-tight en esta muestra.}')
        tex.append(line)
    tex+=[r'\begin{center}\begin{tabular}{lrr}\toprule',
        r'Modelo & Trabajo Budget/Base & Trabajo Budget/Base-tight\\\midrule']
    for n in ['instance001','instance005','instance022','instance027','instance031','instance046']:
        r=[next(v for v in rows if v['budget']=='100' and v['instance']==n and v['control']==p) for p in ['Base','Base-tight']]
        tex.append(f"{n.replace('instance','')} & {float(r[0]['work_ratio']):.3f} & {float(r[1]['work_ratio']):.3f}"+r'\\')
    tex+=[r'\bottomrule\end{tabular}\end{center}',r'Razones geométricas de tres semillas a 100 m$^3$.',r'\end{document}']
    (HERE/'research-note.tex').write_text('\n'.join(tex)+'\n')
    (HERE/'README.md').write_text('# Control Base de la mejora favorable de OMS\n\nVer [resultados](RESULTADOS.md), [protocolo](PROTOCOL.md) y [nota breve](research-note.pdf).\nLos 36 controles y 54 repeticiones tienen diseños cerrados y resultados completos.\nEl replay no requiere Gurobi ni SoPlex. Las nuevas adquisiciones requieren un directorio\nnuevo y las herramientas registradas; nunca sobrescribir las campañas cerradas.\n')


if __name__=='__main__':
    main()
