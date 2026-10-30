"""Plot exploratory hypothesis results; requires matplotlib."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

root=Path(__file__).resolve().parents[1];directory=root/'results/hypotheses_20261030'
r=json.loads((directory/'results.json').read_text())
p=list(csv.DictReader((directory/'heldout_predictions.csv').open(encoding='utf-8-sig')))
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(1,3,figsize=(16,5.7),layout='constrained')
ax=axes[0];models=['mean_quadratic','mean_variance_quadratic','mean_quintic'];positions=np.arange(3)
for offset,weight,color,label in [(-.17,'class','#3b7ca7','手札種類を等重み'),(.17,'combo','#dc9861','実コンボ数で加重')]:
    values=[next(m['rmse_pp'] for m in r['H1']['metrics'] if m['weighting']==weight and m['model']==model) for model in models]
    bars=ax.bar(positions+offset,values,width=.33,color=color,label=label)
    ax.bar_label(bars,fmt='%.2f',fontsize=9,padding=3)
ax.set_xticks(positions,['平均のみ\n2次・3係数','平均＋分散\n2次・6係数','平均のみ\n5次・6係数'])
ax.set_ylim(0,6);ax.set_ylabel('未知のランク組を予測したRMSE（ポイント）');ax.set_title('① 分散を加えると平均誤差が減る',loc='left',fontsize=12);ax.legend(fontsize=8)
ax=axes[1]
for kind,color,label in [('pair','#b54455','ペア'),('suited','#168d83','同スート'),('offsuit','#4467af','異スート')]:
    part=[row for row in p if row['kind']==kind]
    ax.scatter([float(row['equity'])*100 for row in part],[float(row['cv_mean_variance_quadratic'])*100 for row in part],s=19,c=color,label=label,alpha=.8)
for label in ('AA','22','AKs','65s','A9o'):
    row=next(row for row in p if row['hand']==label)
    ax.annotate(label,(float(row['equity'])*100,float(row['cv_mean_variance_quadratic'])*100),xytext=(4,4),textcoords='offset points',fontsize=8)
ax.plot([30,90],[30,90],'--',color='#888888',lw=1);ax.set_xlim(28,90);ax.set_ylim(28,90)
ax.set_xlabel('既存100万配布のエクイティ（%）');ax.set_ylabel('平均＋分散モデルの未学習手札への予測（%）');ax.set_title('ただし個別には大きく外れる',loc='left',fontsize=12);ax.legend(fontsize=8)
ax=axes[2];confirmation=r['H3']['fresh_confirmation']
y=[row['equity']*100 for row in confirmation];err=[1.96*row['se']*100 for row in confirmation]
bars=ax.bar([0,1],y,yerr=err,capsize=5,color=['#168d83','#4467af'],width=.55)
ax.bar_label(bars,fmt='%.2f%%',padding=8)
ax.set_xticks([0,1],[row['hand'] for row in confirmation]);ax.set_ylim(0,72);ax.set_ylabel('新しいseed・各50万配布のエクイティ（%）');ax.set_title('③ 平均順位の順序が勝率で逆転',loc='left',fontsize=12)
fig.suptitle('プリフロップ169手札：仮説の検証結果',fontsize=18,x=.01,ha='left')
fig.supxlabel('相手はランダム1人、ボード未定。予測は同じランクのs/oを同時に学習から外す91分割。\n平均誤差の改善は全手札の精密予測を意味しません。右図の誤差棒は正規近似95%区間。',fontsize=9,color='#4b5563')
for ax in axes:
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
for ext in ('png','svg','pdf'):fig.savefig(directory/f'hypothesis_summary.{ext}',dpi=180,facecolor='white')
print('Saved hypothesis summary PNG/SVG/PDF')
