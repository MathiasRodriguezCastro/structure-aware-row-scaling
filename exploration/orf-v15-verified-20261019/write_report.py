#!/usr/bin/env python3
"""Compact research report; no automatic promotion into the frozen manuscript."""
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
def load(p):return json.loads((HERE/p).read_text())
def fmt(x):return '—' if x is None else f'{x:.3f}'
def interval(r):return f"{r['PAR2_paired_geometric_ratio']:.3f} [{r['lower95']:.3f}, {r['upper95']:.3f}]"
def table(headers,rows):
    return ['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows]


def main():
    validation=load('VALIDATION.json');assert validation['status']=='passed'
    assert load('STATISTICS_VALIDATION.json')['status']=='passed'
    x=load('COMPUTATIONAL_RESULTS.json');p=load('PRECISION_RESULTS.json');sel=load('SELECTOR_VALIDATION.json');bench=load('SELECTOR_BENCHMARK.json')
    first=x['experiment_I'];pol={r['policy']:r for r in first['policy_results']}
    projection=load('PROJECTION_SENSITIVITY.json')
    primary=next(r for r in first['comparisons'] if r['control']=='L2' and r['tau']==.001)
    secondary=next(r for r in first['comparisons'] if r['control']=='L2' and r['tau']==.01)
    clear_speed=(primary['offline_verified_available']['upper95']<1 and
        pol['Budget-L2']['targets']['0.001']>=pol['L2']['targets']['0.001'])
    precision_recovery=any(r['final_physical_budget_pass']<r['runs'] for r in p['observed_final_precision'] if r['policy']=='L2')
    lines=['# Seguimiento para una posible v1.5: resultados completos','',
        'La versión de envío v1.4.2 permanece congelada. Este informe evalúa los',
        'cuatro trabajos propuestos; no constituye una nueva versión enviada ni',
        'una promesa de aceptación editorial.','',
        '## Resultado principal y decisión','',
        ('Se identifica una reducción del indicador temporal penalizado frente a L2 bajo la definición primaria.' if clear_speed else
         '**No se establece una ventaja temporal general frente a L2 al exigir el objetivo común de precisión y calidad.**'),
        f"Budget-L2 alcanza {pol['Budget-L2']['targets']['0.001']}/72 objetivos primarios, frente a {pol['L2']['targets']['0.001']}/72 de L2.",
        'La razón del indicador de disponibilidad verificada PAR2 es '+interval(primary['offline_verified_available'])+'.',
        f"Entre los {primary['common_success_pairs']} éxitos comunes, la razón de disponibilidad real es {fmt(primary['offline_verified_available']['common_success_geometric_ratio'])}.",
        'PAR2 asigna 60 segundos de resolución más preparación a un objetivo no',
        'alcanzado; su razón no es una reducción del tiempo observado de las soluciones.',
        ('Aparecen incumplimientos de precisión de L2 en alguna especificación; se detallan abajo sin ocultar los controles.' if precision_recovery else
         'En las cuatro especificaciones del experimento de precisión, L2 satisface todos los presupuestos finales comprobados. No se demuestra recuperación primal adicional frente a L2 en esa muestra.'),
        '',
        'El avance tangible del software es un selector que incorpora la exportación',
        'efectiva a la decisión y un auditor independiente de sus reservas. Es una',
        'extensión condicional del procedimiento existente, no una prueba de un',
        'nuevo escalador universalmente competitivo. La información física conserva',
        'su valor de especificación; las etiquetas no afectan al solver una vez',
        'compilado el mismo vector de factores.','',
        '## Diseño y significado de los tiempos','',
        '630 asignaciones registradas: 288 para candidatos, 126 para precisión y',
        '216 para robustez. Una repetición técnica predeterminada corrige la',
        'implementación de tiempos de verificación del primer caso Base; no añade',
        'un escenario ni una semilla. Se conservan un fallo previo al optimizador,',
        'el programa original, la enmienda y todos los resultados iniciales.',
        'La repetición solo sustituye tiempos comparativos si vectores, trabajo,',
        'endpoints y primer objetivo se reproducen exactamente.','',
        '24 escenarios conocidos de 24, 72 y 168 horas; semillas nuevas 211, 257,',
        '293; cuatro hilos, límite común de 30 segundos, gap nativo solicitado del 1%.',
        'CPLEX utiliza doce escenarios seleccionados por índice y búsqueda',
        'tradicional común para instrumentar sus incumbentes. El control de',
        'ScaleFlag usa seis escenarios: automático, 0 y 2. Son escenarios de la',
        'misma familia y padres conocidos, no una muestra externa nueva.','',
        'El objetivo primario permite un costo hasta U_ref + 0,001 max(1,|U_ref|);',
        'el secundario usa 0,01. U_ref es un testigo factible racional adquirido',
        'antes de estas ejecuciones, no un óptimo certificado. El gap de parada',
        'del 1% puede terminar una búsqueda sin llegar al objetivo primario del',
        '0,1%, incluso sin error numérico. Un objetivo no alcanzado no equivale',
        'automáticamente a una cota incorrecta.','',
        'Se verifican presupuestos físicos crudos y tras redondear enteros,',
        'distancia entera <=1e-9 y cotas exactas del punto redondeado. Las filas',
        'sin unidad declarada usan error hacia atrás <=1e-6. Esta definición',
        'no certifica factibilidad exacta de todas las filas ni optimalidad.',
        'Las eventuales violaciones diminutas de cotas se conservan como tales.',
        'El callback guarda todos los candidatos y el punto final; el verificador',
        'corre después del solver. El tiempo de descubrimiento es retrospectivo;',
        'la disponibilidad real incluye la espera hasta fin del solver y el',
        'costo de comprobar el prefijo de candidatos. No se presenta como un',
        'verificador en línea ni como un nuevo criterio de parada.','',
        '## I. Objetivos comprobados y calidad','']
    lines+=table(['Política','Objetivo 0,1%','Objetivo 1%','Presupuestos finales','Dominios finales','Contradicciones B'],[
        [r['policy'],f"{r['targets']['0.001']}/72",f"{r['targets']['0.01']}/72",f"{r['final_physical_pass']}/72",
         f"{r['final_domain_pass']}/72",r['detected_bound_contradictions']] for r in first['policy_results']])
    lines+=['','Las contradicciones usan testigos exactos de la representación efectivamente',
        'importada; ausencia de contradicción no significa certificación de todas',
        'las cotas. Un candidato que pasa el control primal puede coexistir con',
        'una cota refutada.','']
    lines+=table(['Control','Pares con éxito común','PAR2 descubrimiento [95%]','PAR2 disponibilidad [95%]','Disponibilidad en éxitos comunes'],[
        [r['control'],r['common_success_pairs'],interval(r['process_discovery']),interval(r['offline_verified_available']),
         fmt(r['offline_verified_available']['common_success_geometric_ratio'])]
        for r in first['comparisons'] if r['tau']==.001])
    lines+=['','Los intervalos remuestrean 24 escenarios, conservando juntas las tres semillas:',
        '100000 remuestras, percentiles marginales 95%. Son condicionales a los',
        'padres conocidos. Los éxitos comunes son un subconjunto seleccionado,',
        'por eso se publican junto al análisis penalizado de todos los casos.',
        f"Al objetivo secundario, Budget-L2 alcanza {pol['Budget-L2']['targets']['0.01']}/72 y L2 {pol['L2']['targets']['0.01']}/72;",
        'su PAR2 de disponibilidad es '+interval(secondary['offline_verified_available'])+'.',
        'Entre éxitos comunes la razón es '+fmt(secondary['offline_verified_available']['common_success_geometric_ratio'])+'.',
        'El indicador penalizado puede mejorar por mayor cumplimiento del objetivo,',
        'aunque los éxitos comunes no lleguen antes. No se confunden ambos efectos.','',
        '## II. Precisión y necesidad del contrato','',
        'Requisitos numéricos experimentales, sin atribuirles autoridad operativa:','',
        '- b10: potencia 0,01 MW; balance y activación 10 m3.',
        '- b100: potencia 0,01 MW; balance y activación 100 m3.',
        '- b1000: potencia 0,01 MW; balance y activación 1000 m3.',
        '- heterogeneous: potencia 0,001 MW; balance 0,001 m3; activación 10 m3.',
        '',
        'El balance a un litro es una meta de conservación numérica del estudio,',
        'no una tolerancia de medición del operador. Las conversiones a unidades',
        'algebraicas se reconstruyen desde cada fila. Cada celda tiene seis modelos',
        'y tres semillas; los controles reutilizados no cuentan como nuevas llamadas.','']
    lines+=table(['Contrato','Política','Presupuestos finales','Máximo q=v/delta','Filas que incumplen'],[
        [r['contract'],r['policy'],f"{r['final_physical_budget_pass']}/{r['runs']}",f"{r['max_q']:.3g}",r['violating_rows']]
        for r in p['observed_final_precision'] if r['policy']!='Budget100-reused'])
    lines+=['',f"Con activación de 1 m3, {p['incompatible_models_at_1m3']}/24 modelos contienen {p['incompatible_rows_at_1m3']} filas",
        'cuyo E=gamma sum |a_entero| agota el presupuesto. Esto certifica incompatibilidad',
        'de la condición suficiente, no infactibilidad del despacho ni imposibilidad',
        'de que un punto concreto cumpla un metro cúbico. No se lanzan MIP en ese caso.',
        f"El control numérico compilado reproduce los factores antiguos sin diferencias ({p['legacy_numeric_envelope_mismatches']} discrepancias).",
        'Por tanto, no se atribuye un efecto causal a las etiquetas físicas. Los',
        'márgenes por familia, percentiles de q, intervenciones y reservas R/delta',
        'están íntegros en los CSV, incluyendo la aplicación de nuevos requisitos',
        'a las soluciones antiguas Budget100.','',
        '## III. CPLEX e interacción con el escalado interno','']
    robust=[('CPLEX',x['CPLEX'])]+[(f'Gurobi ScaleFlag={k}',v) for k,v in x['Gurobi_internal_scaling'].items()]
    rows=[]
    for label,r in robust:
        pp={a['policy']:a for a in r['policy_results']};cc=next(c for c in r['comparisons'] if c['control']=='L2' and c['tau']==.001)
        rows.append([label,r['scenarios'],f"{pp['Budget-L2']['targets']['0.001']}/{pp['Budget-L2']['runs']}",
            f"{pp['L2']['targets']['0.001']}/{pp['L2']['runs']}",interval(cc['offline_verified_available']),
            f"{pp['Budget-L2']['detected_bound_contradictions']}/{pp['L2']['detected_bound_contradictions']}"])
    lines+=table(['Configuración','Escenarios','Objetivo Budget','Objetivo L2','PAR2 disponibilidad B/L2 [95%]','B Budget/L2'],rows)
    lines+=['','El criterio primario de dominios exige cotas exactas. En los puntos finales',
        'de CPLEX, algunas desviaciones de cota están entre 1,3e-13 y 4,2e-11:',
        'no se deben interpretar como una falta importante de precisión física.',
        'Para comprobar su influencia se añadió una sensibilidad posterior: redondear',
        'enteros, proyectar sobre las cotas exactas y volver a verificar el punto',
        'completo, aplicando la misma regla a todas las políticas. No altera la',
        'definición primaria ni mide una disponibilidad en línea del punto reparado.','']
    lines+=table(['Ámbito con proyección posterior','Política','Objetivo 0,1%','Objetivo 1%'],[
        [r['scope'],r['policy'],f"{r['targets']['0.001']}/{r['runs']}",f"{r['targets']['0.01']}/{r['runs']}"]
        for r in projection['policy_results'] if r['scope'] in ['I','CPLEX']])
    lines+=['','La proyección permite separar el efecto de cotas diminutamente excedidas',
        'de la precisión de las filas y de la calidad del costo. No elimina las',
        'contradicciones independientes de cotas duales ya detectadas. Las tablas',
        'de tiempo primarias conservan su criterio registrado y no se reinterpretan',
        'como tiempos medidos del posprocesamiento añadido.','',
        'Estas comparaciones usan las mismas representaciones y ajustes dentro de',
        'cada solver. CPLEX se ejecutó con la biblioteca completa 22.1.2; la API',
        'Community instalada por defecto no admite los tamaños mayores. No se',
        'comparan sus ticks con las unidades de trabajo de Gurobi. Cambiar ScaleFlag',
        'aísla una opción del solver, no reconstruye todas sus operaciones internas.',
        'Los intervalos de seis o doce escenarios tienen incertidumbre limitada por',
        'ese tamaño y no prueban generalidad entre familias.','',
        '## Selector con exportación efectiva','',
        f"La auditoría independiente certifica {p['export_aware_physical_rows_certified']} casos fila-presupuesto del nuevo selector",
        '(seis modelos y cuatro contratos; no son observaciones independientes)',
        'con epsilon+B(alpha)+alpha E <= alpha delta, usando los coeficientes/RHS',
        'realmente escritos. Si falta una cota finita y el producto tiene error',
        'no nulo, ese candidato se rechaza. Un producto exacto no necesita esa cota.',
        'Se elige entre candidatos finitos; abstenerse no prueba inexistencia global.',
        'El orden logarítmico se calcula en binario64; las desigualdades residuales',
        'se certifican con racionales exactos.','',
        'En la configuración de referencia, los factores del Budget-L2 anterior',
        'también satisfacen la condición completa de exportación en todas las filas',
        'físicas auditadas. Aquí el nuevo selector no recupera una garantía que',
        'esos factores hubieran perdido; incorpora su comprobación a la elección.',
        'Esta diferencia limita cuánto puede afirmarse de su utilidad adicional.','',
        f"Se comprueban {sel['boundary_transfer_checks']} puntos racionales en la frontera de la tolerancia exportada.",
        'Hay un ejemplo donde la proyección ideal no cumple la reserva uniforme',
        'de exportación y un factor vecino sí la cumple. Es una prueba controlada',
        'del algoritmo, no evidencia de una ventaja en una segunda aplicación.',
        f"La variante ordenada reproduce los {bench['configurations']} archivos completos del experimento II por SHA-256.",
        f"Medianas de selección: exhaustiva {bench['median_exhaustive_selection_seconds']:.3f} s; ordenada {bench['median_ranked_selection_seconds']:.3f} s.",
        f"Razón geométrica de tiempos de selección: {bench['geometric_selection_time_ratio']:.3f}.",
        'Es un benchmark de compilación posterior; no reemplaza los tiempos de',
        'proceso de los MIP ya registrados ni demuestra una aceleración completa.',
        'La garantía sigue condicionada al residuo escrito, las cotas y la',
        'distancia entera efectivamente satisfechos. No certifica optimalidad.','',
        '## Qué incorporar al artículo','',
        'La campaña responde las cuatro líneas solicitadas. La decisión editorial',
        'debe basarse en cumplimiento y generalidad, no en escoger el cociente más',
        'favorable. Este informe conserva todos los resultados y no modifica v1.4.2.',
        'El selector ofrece una mejora concreta de implementación y certificación;',
        'los resultados de candidatos y robustez delimitan su ventaja computacional.',
        'Sin una recuperación relevante frente a L2 o una reducción temporal estable,',
        'no se justifica anunciar una v1.5 sustancialmente superior ni agrandar el',
        'manuscrito principal con toda esta campaña.','',
        '## Reproducción','',
        'Extraer la evidencia científica heredada de Online Resource 2 v1.4.2,',
        'superponer sus escenarios prospectivos y luego este seguimiento. Desde',
        'esa raíz ejecutar, sin Gurobi ni CPLEX:', '', '```sh',
        'python3 exploration/orf-v15-verified-20261019/check.py',
        'python3 exploration/orf-v15-verified-20261019/check_selector.py',
        'python3 exploration/orf-v15-verified-20261019/precision.py',
        'python3 exploration/orf-v15-verified-20261019/analyze.py',
        'python3 exploration/orf-v15-verified-20261019/check_statistics.py',
        'python3 exploration/orf-v15-verified-20261019/projection_sensitivity.py',
        '```','',
        f"Se retienen {validation['candidate_events']} eventos de candidatos, sus vectores y todas las trazas.",
        'VALIDATION.json, STATISTICS_VALIDATION.json, SELECTOR_VALIDATION.json y',
        'PRECISION_RESULTS.json documentan comprobaciones independientes y límites.',
        'El DOI de la versión de envío permanece reservado para el final por',
        'decisión del autor; este trabajo no publica ni envía un manuscrito.']
    md='\n'.join(lines)+'\n';(HERE/'RESULTADOS.md').write_text(md)
    # A compact standalone report, using the same tables and text as Markdown.
    def esc(s):
        return ''.join({'\\':r'\textbackslash{}','&':r'\&','%':r'\%','_':r'\_','#':r'\#',
            '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}.get(c,c) for c in s.replace('**','').replace('`',''))
    tex=[r'\documentclass[a4paper,10pt]{article}',r'\usepackage[utf8]{inputenc}',r'\usepackage[T1]{fontenc}',
         r'\usepackage{lmodern,booktabs,longtable,geometry,hyperref,adjustbox}',r'\geometry{margin=2.3cm}',
         r'\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}\emergencystretch=2em',r'\begin{document}']
    i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('# '):tex.append(r'\begin{center}\Large\bfseries '+esc(line[2:])+r'\end{center}')
        elif line.startswith('## '):tex.append(r'\section*{'+esc(line[3:])+'}')
        elif line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
            data=[[c.strip() for c in row.strip('|').split('|')] for row in block if not re.fullmatch(r'[|:\- ]+',row)]
            tex.append(r'\begin{center}\small\adjustbox{max width=\linewidth}{\begin{tabular}{'+'l'*len(data[0])+r'}\toprule')
            for j,row in enumerate(data):tex.append(' & '.join(esc(c) for c in row)+r'\\'+(r'\midrule' if j==0 else ''))
            tex.append(r'\bottomrule\end{tabular}}\end{center}');continue
        elif line=='```sh':
            tex.append(r'\begin{verbatim}');i+=1
            while lines[i]!='```':tex.append(lines[i]);i+=1
            tex.append(r'\end{verbatim}')
        elif line.startswith('- '):tex.append(r'\noindent\textbullet\ '+esc(line[2:])+r'\par')
        else:tex.append(esc(line))
        i+=1
    tex.append(r'\end{document}');(HERE/'research-note.tex').write_text('\n'.join(tex)+'\n')
    decision=dict(clear_primary_time_advantage_over_L2=clear_speed,observed_L2_precision_failures_in_budget_study=precision_recovery,
        frozen_paper_modified=False,new_submission_version_created=False)
    (HERE/'EDITORIAL_DECISION.json').write_text(json.dumps(decision,indent=2)+'\n')
    print(json.dumps(decision,indent=2))


if __name__=='__main__':main()
