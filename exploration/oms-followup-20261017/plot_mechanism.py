"""Standalone research figure, regenerated only from verified tabular data."""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
def main():
    rows=list(csv.DictReader((HERE/'mechanism/budget-summary.csv').open()))
    models=list(csv.DictReader((HERE/'mechanism/model-budgets.csv').open()))
    rows=[r for r in rows if int(r['budget'])>=30];x=[int(r['budget']) for r in rows]
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(2,2,figsize=(8.0,5.1),constrained_layout=True)
    axes[0,0].plot(x,[int(r['changed_factors']) for r in rows],'o-',color='#315f91')
    axes[0,0].set(title='(a) Factors changed from L2',ylabel='Rows across six models',ylim=(-300,9200),yticks=[0,4320,8640])
    lo=[];hi=[]
    for b in x:
        rs=[r for r in models if int(r['volume_budget'])==b]
        lo.append(min(float(r['factor_min']) for r in rs));hi.append(max(float(r['factor_max']) for r in rs))
    axes[0,1].fill_between(x,lo,hi,alpha=.22,color='#315f91',label='Range across six models')
    axes[0,1].plot(x,np.sqrt(np.array(lo)*np.array(hi)),'o-',color='#315f91')
    axes[0,1].axhline(1e-9,color='.4',ls='--',lw=1,label='L2 factor')
    axes[0,1].set(title='(b) Activation-row factors',ylabel='Selected factor',yscale='log')
    axes[0,1].legend(fontsize=7,frameon=False)
    axes[1,0].plot(x,[float(r['work_ratio_to_NF3']) for r in rows],'o-',color='#315f91')
    axes[1,0].set(title='(c) Paired geometric solver work',ylabel='Budget-L2 / NF3',ylim=(0,.65))
    axes[1,1].plot(x,[int(r['bound_flags']) for r in rows],'o-',label='Bound contradictions',color='#ad463b')
    axes[1,1].plot(x,[int(r['completion_flags']) for r in rows],'s--',label='Completion contradictions',color='#315f91')
    axes[1,1].set(title='(d) Independent contradictions',ylabel='Calls out of 18',ylim=(-.3,7),yticks=[0,2,4,6])
    axes[1,1].legend(fontsize=7,frameon=False)
    for ax in axes.flat:
        ax.set_xscale('log');ax.set_xticks(x,[str(v) for v in x]);ax.tick_params(axis='x',labelsize=7)
        ax.axvspan(30,100,color='#3b9164',alpha=.10);ax.grid(axis='y',alpha=.18)
        ax.set_xlabel('Volume budget (m³)')
    fig.savefig(HERE/'mechanism/precision-transition.pdf',metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(HERE/'mechanism/precision-transition.png',dpi=160)
    plt.close(fig)
if __name__=='__main__':main()
