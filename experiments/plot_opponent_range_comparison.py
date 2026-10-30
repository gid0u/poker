"""Plot random vs tight range comparisons across preflop and flop."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

root=Path(__file__).resolve().parents[1];d=root/'results/opponent_range_comparison_20261030'
def read(name):return list(csv.DictReader((d/name).open(encoding='utf-8-sig')))
pre=read('preflop_comparison.csv');flops=read('flop_comparison.csv')
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(1,3,figsize=(17,5.7),layout='constrained')
ax=axes[0]
for kind,color,label in [('pair','#bc4650','ペア'),('suited','#188c84','同スート'),('offsuit','#4363ae','異スート')]:
    rows=[r for r in pre if r['opponent']=='tight' and r['kind']==kind]
    ax.scatter([100*float(r['random_equity']) for r in rows],[100*float(r['equity']) for r in rows],c=color,s=22,label=label)
for hand in ('AA','KK','QQ','55','AKs','65s','72o'):
    row=next(r for r in pre if r['opponent']=='tight' and r['hand']==hand)
    ax.annotate(hand,(100*float(row['random_equity']),100*float(row['equity'])),xytext=(3,4),textcoords='offset points',fontsize=8)
ax.plot([0,100],[0,100],'--',color='#888',lw=1);ax.set_xlim(25,90);ax.set_ylim(10,90)
ax.set_xlabel('random相手のエクイティ（%）');ax.set_ylabel('狭い参加レンジ相手のエクイティ（%）');ax.set_title('169手札：相手レンジで評価が変わる',loc='left',fontsize=12);ax.legend(fontsize=8)
ax=axes[1]
for range_name,color,label in [('tight','#4363ae','99+,AQs+,AKo'),('ultra_tight','#bc4650','QQ+,AK')]:
    rows=[r for r in flops if r['opponent']==range_name]
    ax.scatter([100*float(r['random_equity']) for r in rows],[100*float(r['equity']) for r in rows],c=color,s=23,label=label,alpha=.8)
ax.plot([0,100],[0,100],'--',color='#888',lw=1);ax.set_xlim(0,100);ax.set_ylim(0,100)
ax.set_xlabel('random相手のエクイティ（%）');ax.set_ylabel('狭い参加レンジ相手のエクイティ（%）');ax.set_title('46フロップ：強い参加レンジが有利な例も',loc='left',fontsize=12);ax.legend(fontsize=8)
ax=axes[2];labels=['AA','KK','AKs','55'];pos=np.arange(4)
for offset,range_name,color,label in [(-.25,'random','#8c9ba9','random'),(0,'tight','#4363ae','99+,AQs+,AKo'),(.25,'ultra_tight','#bc4650','QQ+,AK')]:
    values=[]
    for hand in labels:
        row=next(r for r in pre if r['opponent']=='tight' and r['hand']==hand) if range_name=='random' else next(r for r in pre if r['opponent']==range_name and r['hand']==hand)
        values.append(100*float(row['random_equity'] if range_name=='random' else row['equity']))
    bars=ax.bar(pos+offset,values,width=.24,color=color,label=label);ax.bar_label(bars,fmt='%.1f',padding=3,fontsize=7)
ax.set_xticks(pos,labels);ax.set_ylim(0,100);ax.set_ylabel('プリフロップのエクイティ（%）');ax.set_title('より狭い＝各手札に常に強い、とは限らない',loc='left',fontsize=11);ax.legend(fontsize=8)
for ax in axes:ax.grid(alpha=.15);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
fig.suptitle('ランダム相手と、強いレンジだけ参加する相手の比較',fontsize=18,x=.01,ha='left')
fig.supxlabel('相手1人・参加済みを条件としたショーダウン評価。99+,AQs+,AKo＝56コンボ、QQ+,AK＝34コンボ（ブロッカー適用前）。\nプリフロップ：狭い各レンジ30万配布/手札。フロップ：全列挙。参加後の追加フォールド・ベットは扱っていません。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(d/f'opponent_range_summary.{ext}',dpi=180,facecolor='white')
print('Saved range comparison PNG/SVG/PDF')
