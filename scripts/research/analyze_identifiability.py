#!/usr/bin/env python3
"""Summarize direct export comparisons; keep kernel and ownership controls separate."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


def main():
    folder=ROOT/'results-revision/research-audit/identifiability-final'
    exports=pd.read_csv(folder/'exports.csv')
    comparisons=pd.read_csv(folder/'named_comparisons.csv')
    matrix=exports.pivot(index=['block_range','severity','pattern','seed'],columns='variant',values='kappa2_common_rank')
    summaries=[]
    for control in ['Flat-GM','Role-Hybrid','SA-Mat-permB','Flat-L2']:
        ratio=matrix['SA-Mat']/matrix[control]
        for r in [1,2,3]:
            values=ratio.xs(r,level='block_range')
            comp=comparisons[(comparisons['first']=='SA-Mat')&(comparisons['second']==control)&(comparisons.block_range==r)]
            summaries.append(dict(control=control,block_range=r,n=len(values),
                                  ratio_min=values.min(),ratio_median=values.median(),ratio_max=values.max(),
                                  byte_equal=int(comp.byte_equal.sum()) if len(comp) else None))
    table=pd.DataFrame(summaries)
    table.to_csv(folder/'summary.csv',index=False)
    figs=ROOT/'paper/figs/research';figs.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':11,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(9,3.6),layout='constrained')
    rng=np.random.default_rng(1)
    for ax,controls in zip(axes,[['Flat-GM'],['Role-Hybrid','SA-Mat-permB']]):
        for control,color,offset in zip(controls,['#0072b2','#d55e00'],[-.09,.09]):
            ratio=matrix['SA-Mat']/matrix[control]
            for r in [1,2,3]:
                values=ratio.xs(r,level='block_range').to_numpy()
                ax.scatter(r+offset+rng.uniform(-.06,.06,len(values)),values,s=10,alpha=.4,color=color,
                           label=control if r==1 else None,rasterized=False)
                ax.plot([r+offset-.1,r+offset+.1],[np.median(values)]*2,color=color,lw=2)
        ax.axhline(1,color='black',ls='--',lw=.8)
        ax.set_xticks([1,2,3],['[-1,1]','[-2,2]','[-3,3]'])
        ax.set_xlabel('Original block exponent range')
        ax.set_ylabel(r'SA-Mat / control $\kappa_2^+$ ratio')
        ax.legend(title='Control',loc='best',fontsize=10)
    axes[0].set_yscale('log');axes[0].set_title('(a) Different coupling kernels')
    axes[1].set_ylim(.92,1.1);axes[1].set_title('(b) Matched kernels')
    fig.savefig(figs/'identifiability.pdf',bbox_inches='tight')
    fig.savefig(figs/'identifiability.png',dpi=180,bbox_inches='tight')
    print(table.to_string(index=False))


if __name__=='__main__':main()
