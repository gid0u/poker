import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
root=Path(__file__).resolve().parents[1];d=root/'results/postflop_generalization_20261030'
def read(name):
    with (d/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
metrics=read('metrics.csv');sub=read('subgroup_metrics.csv')
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams['axes.unicode_minus']=False
models=['mean','mean_variance','board','opponent_proxy','proxy_distribution'];labels=['平均','平均＋\n分散','＋ボード\n手札特徴','＋別レンジ\n平均','＋別レンジ\n分布']
fig,axes=plt.subplots(1,3,figsize=(17,5.8),layout='constrained')
for ax,split,title in ((axes[0],'group_holdout','未知フロップ群で検証'),(axes[1],'monotone_holdout','同スート3枚を未学習として検証')):
    pos=np.arange(5)
    for off,target,color,lab in [(-.18,'random','#4363ae','random相手'),(.18,'tight','#b94e60','厳格レンジ相手')]:
        values=[float(next(r['rmse_pp'] for r in metrics if r['split']==split and r['target']==target and r['weighting']=='population' and r['model']==m)) for m in models]
        bars=ax.bar(pos+off,values,width=.34,color=color,label=lab);ax.bar_label(bars,fmt='%.1f',fontsize=7,padding=3)
    ax.set_xticks(pos,labels,fontsize=8);ax.set_ylim(0,15.5);ax.set_ylabel('エクイティ予測RMSE（ポイント）');ax.set_title(title,loc='left',fontsize=12);ax.legend(fontsize=8)
ax=axes[2];cats=['paired','monotone','twotone_connected','twotone_other','rainbow'];names=['ペア','同スート3','2スート\n連結','2スート\nその他','3スート'];pos=np.arange(5)
for off,target,color,lab in [(-.18,'random','#4363ae','random相手'),(.18,'tight','#b94e60','厳格レンジ相手')]:
    values=[float(next(r['rmse_pp'] for r in sub if r['target']==target and r['grouping']=='texture' and r['category']==c)) for c in cats]
    bars=ax.bar(pos+off,values,width=.34,color=color,label=lab);ax.bar_label(bars,fmt='%.1f',fontsize=7,padding=3)
ax.set_xticks(pos,names,fontsize=8);ax.set_ylim(0,10);ax.set_ylabel('エクイティ予測RMSE（ポイント）');ax.set_title('未知群のボード別誤差：分布モデル',loc='left',fontsize=12);ax.legend(fontsize=8)
for ax in axes:ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
fig.suptitle('ポストフロップの未知局面で特徴の予測力を比較',fontsize=18,x=.01,ha='left')
fig.supxlabel('2400局面・600フロップ群。実配布の組合せ数で重み付け。相手1人、ショーダウン評価。\n別レンジ特徴はQQ+,AKで独立に64ボードを追加計算して得た値。計算コストが増えるため、同じコストでの比較ではありません。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(d/f'generalization_summary.{ext}',dpi=180,facecolor='white')
print('Saved generalization summary')
