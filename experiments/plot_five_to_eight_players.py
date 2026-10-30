import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
root=Path(__file__).resolve().parents[1];d=root/'results/five_to_eight_players_20261030'
with (d/'all_2_to_9.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
fig,axes=plt.subplots(1,2,figsize=(12,5.3),layout='constrained')
for ax,model,title in zip(axes,['random','tight'],['相手全員random','相手全員 99+,AQs+,AKo']):
 for hand,color in [('AA','#9c313e'),('55','#b26f29'),('22','#875391'),('A9o','#4166a5'),('65s','#168b81')]:
  group=sorted((r for r in rows if r['hand']==hand and r['model']==model),key=lambda r:int(r['participants']))
  ax.plot([int(r['participants']) for r in group],[100*float(r['equity']) for r in group],marker='o',color=color,label=hand,lw=2)
 ax.set_xticks(range(2,10));ax.set_ylim(0,95);ax.set_xlabel('参加人数（自分を含む）');ax.set_ylabel('エクイティ（%）');ax.set_title(title,loc='left');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
fig.suptitle('プリフロップ：参加2〜9人のエクイティ',fontsize=17,x=.01,ha='left')
fig.supxlabel('新規5〜8人は各10万提案。2〜4人・9人は既存結果。分割ポットを含むショーダウン評価。\n各人数で全員参加・カード重複なしを条件にするため、特に厳格レンジでは人数ごとの配布分布が異なります。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(d/f'players_2_to_9.{ext}',dpi=180,facecolor='white')
print('Saved 2-9 player chart')
