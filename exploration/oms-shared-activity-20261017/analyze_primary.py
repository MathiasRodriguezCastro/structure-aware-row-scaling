"""Aggregate completed unit-zero comparisons, without double-counting aliases."""
import csv
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
design=json.loads((HERE/'pilot/design.json').read_text())
rows=json.loads((HERE/'pilot/RESULTS.json').read_text())
assert len(rows)==195 and json.loads((HERE/'VALIDATION.json').read_text())['all_complete']
records={(r['name'],r['arm'],r['seed']):r for r in rows}
table=[];expanded=[]
for assignment in design['assignments']:
    items=[records[(assignment['name'],assignment['canonical_arm'],s)] for s in (181,191,193)]
    for r in items:expanded.append({**r,'assigned_policy':assignment['policy'],'assigned_unit':assignment['unit_exponent']})
    if assignment['unit_exponent']!=0:continue
    table.append({'model':assignment['name'],'policy':assignment['policy'],'calls':3,
                  'primal_pass':sum(r.get('primal_pass',False) for r in items),
                  'quality_target_met':sum(r.get('quality_target_met',False) for r in items),
                  'median_verified_objective':statistics.median(r['verified_objective'] for r in items),
                  'median_work':statistics.median(r['work'] for r in items),
                  'activity_hypothesis_failures':sum(r['activity_hypothesis_failures'] for r in items)})
with (HERE/'primary-unit-zero.csv').open('w') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
summary={'design_calls':195,'unique_exports_and_parameters':65,'unit_zero_comparisons':table,
         'canonical_runs':rows,'assigned_unit_results':expanded,
         'alias_warning':'Assigned units reuse byte-identical calls; they are not independent observations.',
         'recovery_warning':'One native attempt has a completed log but lost point/metadata; preserved and repeated once as documented in RECOVERY-2.json.',
         'paper_incorporation':False}
(HERE/'PRIMARY_RESULTS.json').write_text(json.dumps(summary,indent=2)+'\n')
text=['# Resultado primario: actividad compartida de radio mínimo','',
      '195 configuraciones/semillas completadas y verificadas; 65 exportaciones con parámetros distintos.',
      'Las cinco unidades de fila no son aplicaciones diferentes. Los aliases se fijaron antes de resolver.',
      'Una escritura truncada se preservó y repitió una vez; no se cuenta como observación independiente.','',
      '| Modelo | Política | Precisión / 3 | Calidad / 3 | Trabajo mediano |',
      '|---|---|---:|---:|---:|']
for r in table:text.append(f"| {r['model']} | {r['policy']} | {r['primal_pass']} | {r['quality_target_met']} | {r['median_work']:.4g} |")
text+=['','La propuesta de radio mínimo no muestra superioridad general. En control30 falla la entrega',
       'redondeada en las tres semillas y algunas hipótesis nominales no se cumplen en las salidas.',
       'La selección algebraica admisible no equivale a garantía incondicional del backend.',
       'Las exportaciones compartidas son idénticas bajo cinco cambios de unidad en los cinco modelos;',
       'esa propiedad también puede tenerla una normalización convencional.','',
       'El seguimiento prospectivo compara una elección centrada con normalización de coeficientes,',
       'centro sin contrato, tolerancias estrictas e indicadores en tres precisiones.','']
(HERE/'PRIMARY_RESULTS.md').write_text('\n'.join(text))
print(json.dumps({'calls':195,'unit_zero_rows':len(table),'paper_incorporation':False}))
