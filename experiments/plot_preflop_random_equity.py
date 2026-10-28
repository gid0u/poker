"""Heatmap and rank/variance scatter colored by HU random-range equity."""
import argparse,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import TwoSlopeNorm


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    rows=list(csv.DictReader((args.directory/'preflop_random_equity.csv').open(encoding='utf-8-sig')))
    by_hand={r['hand']:r for r in rows}
    font=Path('C:/Windows/Fonts/meiryo.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    ranks='AKQJT98765432'
    matrix=np.zeros((13,13))
    labels={}
    for i,a in enumerate(ranks):
        for j,b in enumerate(ranks):
            hand=a+a if i==j else a+b+'s' if i<j else b+a+'o'
            labels[i,j]=hand
            matrix[i,j]=float(by_hand[hand]['equity'])*100
    norm=TwoSlopeNorm(vmin=30,vcenter=50,vmax=86)
    fig,ax=plt.subplots(figsize=(13,11),layout='constrained')
    image=ax.imshow(matrix,cmap='RdYlBu',norm=norm)
    for (i,j),hand in labels.items():
        value=matrix[i,j]
        ax.text(j,i,f'{hand}\n{value:.1f}%',ha='center',va='center',fontsize=9,
                color='white' if value>73 or value<34 else '#17202a')
    ax.set_xticks(range(13),ranks,fontsize=12)
    ax.set_yticks(range(13),ranks,fontsize=12)
    ax.xaxis.tick_top()
    ax.set_xticks(np.arange(-.5,13,1),minor=True)
    ax.set_yticks(np.arange(-.5,13,1),minor=True)
    ax.grid(which='minor',color='white',linewidth=1.5)
    ax.tick_params(which='minor',bottom=False,left=False)
    ax.set_title('プリフロップ169種類 vs ランダム1人：エクイティ',fontsize=18,loc='left',pad=24)
    fig.colorbar(image,ax=ax,shrink=.75,label='エクイティ（%）：単独勝率 ＋ 引き分け率 ÷ 2')
    fig.supxlabel('ボード未定・各手札100万配布のモンテカルロ推定。右上＝同スート、左下＝異スート、対角＝ペア。\n各手札の95%区間の半幅は最大約0.10ポイント。全員ショーダウン参加、ベット・フォールドなし。',fontsize=10)
    for ext in ('png','svg','pdf'):
        fig.savefig(args.directory/f'preflop_random_equity_heatmap.{ext}',dpi=180,facecolor='white')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,8.5),layout='constrained')
    for kind,marker,title in [('pair','D','ペア'),('suited','o','同スート / s'),('offsuit','^','異スート / o')]:
        group=[r for r in rows if r['kind']==kind]
        dots=ax.scatter([float(r['mean_rank_exact']) for r in group],
            [float(r['variance_rank_exact'])/1e6 for r in group],
            c=[float(r['equity'])*100 for r in group],cmap='RdYlBu',norm=norm,
            marker=marker,s=60 if kind=='pair' else 38,edgecolors='#333333',linewidths=.35,label=title,zorder=3)
    for r in rows:
        if r['kind']=='pair' or r['hand'] in ('AKs','AKo','QJs','JTs','T9s','98s','76s','54s','32s','72o','32o'):
            ax.annotate(r['hand'],(float(r['mean_rank_exact']),float(r['variance_rank_exact'])/1e6),xytext=(5,5),textcoords='offset points',fontsize=8)
    ax.set_title('予想順位 × 順位分散：ランダム1人に対するエクイティで色付け',fontsize=17,loc='left',pad=20)
    ax.set_xlabel('最終7枚の予想順位（← 強い平均 ／ 弱い平均 →）',fontsize=12)
    ax.set_ylabel('最終7枚の順位分散（×1,000,000）',fontsize=12)
    ax.grid(alpha=.16)
    ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='lower right')
    fig.colorbar(dots,ax=ax,shrink=.8,label='エクイティ（%）')
    fig.supxlabel('座標＝ボード全2,118,760通りの正確な順位モーメント。色＝各手札100万配布の推定エクイティ。\n相手1人は残りカードから等確率に2枚、ボードは共有。順位分散はチップ収益の分散ではありません。',fontsize=10)
    for ext in ('png','svg','pdf'):
        fig.savefig(args.directory/f'preflop_random_equity_scatter.{ext}',dpi=180,facecolor='white')
    print('Saved heatmap + scatter: PNG/SVG/PDF')

if __name__=='__main__': main()
