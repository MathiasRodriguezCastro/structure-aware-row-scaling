"""Descriptive per-model comparisons: precision before quality, cost after both."""
import collections
import csv
import json
import math
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent


def main():
    rows=json.loads((HERE/'RESULTS.json').read_text());validation=json.loads((HERE/'VALIDATION.json').read_text())
    design=json.loads((HERE/'pilot/design.json').read_text());summary=[]
    groups=collections.defaultdict(list)
    for row in rows:groups[(row['name'],row['budget_label'],row['policy'])].append(row)
    for (name,budget,policy),items in sorted(groups.items()):
        valid=[r for r in items if r.get('primal_pass')]
        summary.append({'name':name,'budget':budget,'policy':policy,'calls':len(items),
                        'points':sum(r['has_point'] for r in items),'primal_pass':len(valid),
                        'quality_target_met':sum(r.get('quality_target_met',False) for r in items),
                        'median_verified_objective':statistics.median(r['verified_objective'] for r in valid) if valid else None,
                        'median_work':statistics.median(r['work'] for r in items),
                        'median_cycle_seconds':statistics.median(r['fresh_process_seconds'] for r in items),
                        'median_selection_export_seconds':statistics.median(r['selection_export_seconds'] for r in items),
                        'activity_hypothesis_failures':sum(r.get('activity_hypothesis_failures',0) for r in items)})
    with (HERE/'SUMMARY.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    lookup={(r['name'],r['budget_label'],r['policy'],r['seed']):r for r in rows};paired=[]
    for v in design['variants']:
        if v['policy']!='Centered-shared':continue
        for baseline in ('Coefficient-SOS','Tight-coefficient-SOS','Unconstrained-shared','Centered-individual','Minimum-shared','Indicator-budget','Tight-raw'):
            pairs=[]
            for seed in (197,199,211):
                p=lookup.get((v['name'],v['budget_label'],'Centered-shared',seed));b=lookup.get((v['name'],v['budget_label'],baseline,seed))
                if p is not None and b is not None:pairs.append((p,b))
            if not pairs:continue
            fair=[(p,b) for p,b in pairs if p.get('quality_target_met') and b.get('quality_target_met')]
            paired.append({'name':v['name'],'budget':v['budget_label'],'baseline':baseline,'pairs':len(pairs),
                           'proposal_primal_pass':sum(bool(p.get('primal_pass')) for p,b in pairs),
                           'baseline_primal_pass':sum(bool(b.get('primal_pass')) for p,b in pairs),
                           'proposal_quality_target_met':sum(bool(p.get('quality_target_met')) for p,b in pairs),
                           'baseline_quality_target_met':sum(bool(b.get('quality_target_met')) for p,b in pairs),
                           'both_quality_pairs':len(fair),
                           'work_geometric_ratio_on_both_quality':math.exp(statistics.mean(math.log(p['work']/b['work']) for p,b in fair)) if fair else None,
                           'cycle_geometric_ratio_on_both_quality':math.exp(statistics.mean(math.log(p['fresh_process_seconds']/b['fresh_process_seconds']) for p,b in fair)) if fair else None})
    (HERE/'SUMMARY.json').write_text(json.dumps({'complete':validation['all_complete'],'by_model_budget_policy':summary,'paired':paired},indent=2)+'\n')
    lines=['# Normalización sujeta a precisión: resultado','',
           f"Procesos completados: {validation['completed_attempts']}/{validation['planned_calls']}. "+('Campaña completa.' if validation['all_complete'] else '**Provisional; no es una conclusión de la campaña.**'),'',
           '| Modelo | Presupuesto | Política | Precisión | Calidad | Trabajo mediano | Ciclo mediano (s) |',
           '|---|---:|---|---:|---:|---:|---:|']
    for r in summary:lines.append(f"| {r['name']} | {r['budget']} | {r['policy']} | {r['primal_pass']}/{r['calls']} | {r['quality_target_met']}/{r['calls']} | {r['median_work']:.4g} | {r['median_cycle_seconds']:.4g} |")
    lines+=['','Calidad: punto que cumple todos los presupuestos, con objetivo recalculado dentro del',
            'margen del 1% de la referencia fijada. No es certificación de optimalidad.',
            'Trabajo y ciclo solo se comparan como ventaja cuando ambos brazos alcanzan esa calidad.',
            'Ciclo desde JSON preservado: excluye descarga, contracción común y generador original.',
            'Presupuestos distintos no son aplicaciones independientes.','']
    (HERE/'RESULTADOS.md').write_text('\n'.join(lines))
    print(json.dumps({'complete':validation['all_complete'],'calls':validation['completed_attempts'],'cells':len(summary)}))


if __name__=='__main__':main()
