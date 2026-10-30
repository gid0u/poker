import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
root=Path(__file__).resolve().parents[1];d=root/'results/nine_player_preflop_20261030'
with (d/'nine_player_preflop.csv').open(encoding='utf-8-sig') as f:new=list(csv.DictReader(f))
with (root/'results/multiway_preflop_examples_20261030/multiway_preflop.csv').open(encoding='utf-8-sig') as f:old=list(csv.DictReader(f))
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
fig,axes=plt.subplots(1,2,figsize=(12,5.3),layout='constrained')
for ax,model,title in zip(axes,['random','tight'],['相手全員random','相手全員 99+,AQs+,AKo']):
    for hand,color in [('AA','#9c313e'),('55','#b26f29'),('A9o','#4166a5'),('65s','#168b81'),('72o','#777777')]:
        group=[r for r in old if r['hand']==hand and r['model']==model]+[r for r in new if r['hand']==hand and r['model']==model]
        group.sort(key=lambda r:int(r['opponents']))
        ax.plot([int(r['opponents'])+1 for r in group],[100*float(r['equity']) for r in group],marker='o',color=color,label=hand,lw=2)
    ax.set_xticks([2,3,4,9]);ax.set_ylim(0,95);ax.set_xlabel('参加人数（自分を含む）');ax.set_ylabel('エクイティ（%）');ax.set_title(title,loc='left');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
fig.suptitle('プリフロップ：9人までの人数別エクイティ',fontsize=17,x=.01,ha='left')
fig.supxlabel('各人数は全員参加を条件とした別の配布分布。5〜8人の結果は未計算で、線は補間です。\n9人は各30万提案の推定。厳格レンジでは合法配布に対する重要度重みを使用。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(d/f'nine_player_summary.{ext}',dpi=180,facecolor='white')
print('Saved 9-player comparison chart')
