"""Standalone descriptive plot, with no uncertainty/generalization claim."""
import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'VALIDATION.json').read_text())['all_complete']
rows=json.loads((HERE/'RESULTS.json').read_text());groups=collections.defaultdict(list)
for r in rows:groups[(r['policy'],r['budget'])].append(r)
budgets=[1e-4,1e-6,1e-8]
policies=[('Centered-shared','Propuesta centrada','#1764ab','-'),
          ('Coefficient-SOS','Normalización de coeficientes','#777777','--'),
          ('Tight-coefficient-SOS','Normalización + tolerancias estrictas','#5c3575','-.'),
          ('Indicator-budget','Indicadores con presupuesto','#bd6b12',':'),
          ('Tight-raw','Filas con tolerancias estrictas','#111111','--')]
fig,axes=plt.subplots(1,2,figsize=(10.3,4.3),sharey=True)
for ax,metric,title in zip(axes,('primal_pass','quality_target_met'),('Precisión original tras redondear','Precisión y objetivo de referencia')):
    for policy,label,color,style in policies:
        values=[]
        for budget in budgets:
            own=groups[(policy,budget)];assert len(own)==15
            values.append(sum(bool(r.get(metric)) for r in own))
        ax.plot(budgets,values,label=label,color=color,linestyle=style,marker='o',markersize=4,lw=1.5)
    ax.set_xscale('log');ax.invert_xaxis();ax.set_xticks(budgets,['$10^{-4}$','$10^{-6}$','$10^{-8}$'])
    ax.set_ylim(-.4,15.7);ax.set_yticks([0,3,6,9,12,15]);ax.grid(alpha=.2);ax.set_title(title,fontsize=10)
    ax.set_xlabel('Presupuesto algebraico de activación')
axes[0].set_ylabel('Entregas / 15 (5 modelos × 3 semillas)')
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,ncol=2,loc='lower center',bbox_to_anchor=(.5,.005),frameon=False,fontsize=8)
fig.subplots_adjust(bottom=.30,top=.88,wspace=.13)
fig.suptitle('Sensibilidad descriptiva; las tres precisiones no son aplicaciones independientes',fontsize=10)
for suffix in ('pdf','png'):fig.savefig(HERE/('precision_quality.'+suffix),dpi=170,bbox_inches='tight')
plt.close(fig)
print(json.dumps({'optimizer_calls':0,'figure':'precision_quality.pdf','calls_shown':360,'family_generalization_claim':False}))
