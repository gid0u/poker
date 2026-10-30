"""Render exact postflop hypothesis counterexamples."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

root=Path(__file__).resolve().parents[1];directory=root/'results/postflop_hypotheses_20261030'
r=json.loads((directory/'results.json').read_text());flops=list(csv.DictReader((directory/'flop_states.csv').open(encoding='utf-8-sig')))
font=Path('C:/Windows/Fonts/meiryo.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(1,3,figsize=(16,5.8),layout='constrained')
ax=axes[0];case=r['H1']['largest_increase'];f=next(f for f in flops if f['hero']==case['hero'] and f['flop']==case['flop'])
values=[float(f['rank_variance'])/1e6,float(f['expected_turn_rank_variance'])/1e6,case['rank_variance']/1e6]
bars=ax.bar(range(3),values,color=['#4866aa','#168a80','#c35663'],width=.6);ax.bar_label(bars,fmt='%.2f',padding=4)
ax.set_xticks(range(3),['フロップ','全ターンの平均','9♠のターン']);ax.set_ylabel('残る順位分散（×1,000,000）');ax.set_ylim(0,6.4)
ax.set_title('① 平均では減るが、分岐では増える\n自分7♣2♥ / フロップQ♠J♠8♠',loc='left',fontsize=12)
ax=axes[1];pair=r['H2']['largest_same_hero_flop_rank_equity_gap'];states=[pair['low_equity_state'],pair['high_equity_state']]
bars=ax.bar([0,1],[s['equity']*100 for s in states],color=['#c35663','#168a80'],width=.6);ax.bar_label(bars,fmt='%.2f%%',padding=4)
ax.set_xticks([0,1],['T♠9♠2♣7♠8♠','T♠9♠2♣3♣7♥'],fontsize=9);ax.set_ylim(0,103);ax.set_ylabel('ランダム1人に対するエクイティ（%）')
ax.set_title('② 同じ順位・分散0でも勝率は違う\n自分7♣2♥ / 最終順位は両方3209',loc='left',fontsize=12)
ax=axes[2];states=r['H4']['states'];pos=np.arange(2)
for offset,field,label,color in [(-.17,'random_equity','相手random','#4866aa'),(.17,'set_range_equity','相手TT・99','#c35663')]:
    bars=ax.bar(pos+offset,[s[field]*100 for s in states],width=.33,color=color,label=label);ax.bar_label(bars,fmt='%.1f%%',padding=3,fontsize=9)
ax.set_xticks(pos,['A♠A♥','Q♠J♠']);ax.set_ylim(0,103);ax.set_ylabel('エクイティ（%）');ax.legend(fontsize=9)
ax.set_title('④ 相手レンジで手札の優劣が逆転\nフロップT♠9♠2♣',loc='left',fontsize=12)
for ax in axes:
    ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
fig.suptitle('フロップ・ターン・リバーへ拡張した仮説検証',fontsize=18,x=.01,ha='left')
fig.supxlabel('46フロップ局面・2,162ターン局面・49,726リバー局面。図の数値は全列挙値。\n相手1人、全員ショーダウン参加。設計した局面集合での結果であり、全ポストフロップ局面の頻度を表すものではありません。',fontsize=9,color='#4b5563')
for ext in ('png','svg','pdf'):fig.savefig(directory/f'postflop_summary.{ext}',dpi=180,facecolor='white')
print('Saved postflop summary PNG/SVG/PDF')
