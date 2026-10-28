"""Render exact preflop moments as PNG, SVG and PDF (requires matplotlib)."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    rows=list(csv.DictReader((args.directory/'preflop_rank_scatter.csv').open(encoding='utf-8-sig')))
    meta=json.loads((args.directory/'preflop_rank_metadata.json').read_text())
    font=Path('C:/Windows/Fonts/meiryo.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig,ax=plt.subplots(figsize=(13,8.5),layout='constrained')
    colors={'pair':'#bc4650','suited':'#188c84','offsuit':'#4363ae'}
    markers={'pair':'D','suited':'o','offsuit':'^'}
    for kind,title in [('pair','ペア（13種類）'),('suited','同スート / s（78種類）'),('offsuit','異スート / o（78種類）')]:
        group=[r for r in rows if r['kind']==kind]
        ax.scatter([float(r['mean_rank']) for r in group],[float(r['variance_rank'])/1e6 for r in group],s=58 if kind=='pair' else 30,c=colors[kind],marker=markers[kind],label=title,alpha=.85,edgecolors='white',linewidths=.45,zorder=3)
    for r in rows:
        if r['kind']=='pair' or r['hand'] in ('AKs','AKo','AQs','A2s','KQs','QJs','JTs','T9s','98s','87s','76s','65s','54s','32s','72o','32o','T9o'):
            ax.annotate(r['hand'],(float(r['mean_rank']),float(r['variance_rank'])/1e6),xytext=(5,5),textcoords='offset points',fontsize=8,color=colors[r['kind']],zorder=4)
    ax.axvline(meta['baseline_mean'],color='#777777',ls='--',lw=1,label='全7枚の平均順位')
    ax.axhline(meta['baseline_variance']/1e6,color='#999999',ls=':',lw=1,label='全7枚の順位分散')
    ax.set_title('プリフロップ169種類：予想順位 × 順位分散',fontsize=19,loc='left',pad=20)
    ax.set_xlabel('完成した7枚の予想順位（← 強い平均 ／ 弱い平均 →）',fontsize=12)
    ax.set_ylabel('完成した7枚の順位分散（×1,000,000）',fontsize=12)
    ax.grid(alpha=.16)
    ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='lower right',fontsize=9,framealpha=.95)
    fig.supxlabel('各点は手札1種類。残り50枚からボード5枚の全2,118,760通りを等確率で全列挙。\n順位は1が最強・7462が最弱。相手レンジは指定せず、勝率ではなく最終ハンド順位の分布を評価。',fontsize=10,color='#4b5563')
    for ext in ('png','svg','pdf'):
        fig.savefig(args.directory/f'preflop_rank_scatter.{ext}',dpi=190,facecolor='white')
    print('Saved PNG/SVG/PDF')
if __name__=='__main__': main()
