import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
root=Path(__file__).resolve().parents[1];d=root/'results/multiway_preflop_examples_20261030'
with (d/'multiway_preflop.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
fig,axes=plt.subplots(1,2,figsize=(12,5.3),layout='constrained')
for ax,model,title in zip(axes,['random','tight'],['相手全員random','相手全員 99+,AQs+,AKo']):
    for hand,color in [('AA','#9c313e'),('55','#b26f29'),('A9o','#4166a5'),('65s','#168b81'),('72o','#777777')]:
        group=[r for r in rows if r['hand']==hand and r['model']==model]
        x=[int(r['opponents']) for r in group];y=[100*float(r['equity']) for r in group]
        ax.plot(x,y,marker='o',color=color,label=hand,lw=2)
    ax.set_xticks([1,2,3]);ax.set_ylim(0,95);ax.set_xlabel('相手の人数');ax.set_ylabel('エクイティ（%）');ax.set_title(title,loc='left');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
fig.suptitle('プリフロップ：相手人数とレンジによる変化',fontsize=17,x=.01,ha='left')
fig.supxlabel('各相手のカード重複を除外し、共通ボードでショーダウン。分割ポットを含む。\n相手2・3人は各30万配布の推定。相手1人は既存結果。ベット・フォールドなし。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(d/f'multiway_preflop_summary.{ext}',dpi=180,facecolor='white')
print('Saved chart')
