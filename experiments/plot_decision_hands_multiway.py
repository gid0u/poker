import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
root=Path(__file__).resolve().parents[1];d=root/'results/decision_hands_multiway_20261030'
with (d/'all_hands.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
fig,axes=plt.subplots(1,2,figsize=(13,5.6),layout='constrained')
for ax,model,title in zip(axes,['random','tight'],['相手全員random','相手全員 99+,AQs+,AKo']):
 for hand,color in [('JJ','#9c313e'),('99','#bd772d'),('A9o','#4166a5'),('A5s','#945ab6'),('JTs','#00a079'),('65s','#168b81')]:
  group=sorted((r for r in rows if r['hand']==hand and r['model']==model),key=lambda r:int(r['participants']))
  ax.plot([int(r['participants']) for r in group],[100*float(r['equity']) for r in group],marker='o',color=color,label=hand,lw=1.8,markersize=4)
 ax.set_xticks(range(2,10));ax.set_ylim(0,85);ax.set_xlabel('参加人数（自分を含む）');ax.set_ylabel('エクイティ（%）');ax.set_title(title,loc='left');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
fig.suptitle('判断に注意したい手札：参加2〜9人の比較',fontsize=17,x=.01,ha='left')
fig.supxlabel('新たに追加した手札の3〜9人は各10万提案。既存結果は標本数が異なります。全員ショーダウン・引き分けを分配。\n人数ごとに全員が参加しカード重複なしという条件で配布し直します。厳格レンジは重要度重みを使用。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(d/f'decision_hands_multiway.{ext}',dpi=180,facecolor='white')
print('Saved decision hands chart')
