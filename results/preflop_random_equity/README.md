# プリフロップ169種類 vs ランダム1人

自分は各種類の代表実カード2枚を固定、ボード未定、相手は残り50枚から選ぶ全合法2枚を等確率としました。各種類100万配布、合計1億6900万配布のモンテカルロ推定です。相手2枚とボード5枚は同じ配布の中で重複なく抽選します。スート対称性で169種類が1326実コンボを代表します。

- `preflop_random_equity.csv`：全169種類の実カード、単独勝率、引き分け率、敗率、エクイティ、標準誤差、95%区間、標本数、seed、前回の正確な順位平均・分散。
- `preflop_random_equity_heatmap.*`：169種類のエクイティ表。
- `preflop_random_equity_scatter.*`：正確な予想順位×順位分散の座標に、推定エクイティを色付けした散布図。
- `run_metadata.json`：配布条件、辞書checksum、計算環境、検証結果。

エクイティ＝単独勝率＋引き分け率÷2です。相手は1人です。各手札の区間は独立した単一手札の正規近似95%区間で、169手札すべてを同時に95%で覆う区間ではありません。推定順位が近い手札の順序は誤差内で入れ替わり得ます。

前回の順位平均・分散はC(50,5)全列挙の値を再使用しています。相手が完全ランダムなので、相手のカードを周辺化したボード分布は一様となり、この再使用が可能です。今回のサンプル順位平均も正確な平均との整合性を確認しました。

計算の検証：ベクトル化辞書参照128例を独立した既存役判定と照合、カード順序不変性を確認、勝敗件数の合計を検証、実コンボ数重み付きエクイティが理論上の50%と整合することを確認。既存の相対勝率テスト10件も成功しました。

全列挙なら1種類あたりC(50,2)×C(48,5)=2,097,572,400配布となるため、今回は推定です。全員がショーダウンに参加し、ベット・フォールド・レークは考慮しません。このエクイティ順は収益性や最適な参加レンジの順序ではありません。

再生成（numpy必要。図にはmatplotlib必要）：

```powershell
$env:PYTHONPATH="$PWD\src"
.venv-studio/Scripts/python.exe experiments/preflop_random_equity.py --dictionary data/processed/seven_card_dictionary --moments results/preflop_rank_scatter/preflop_rank_scatter.csv --output results/preflop_random_equity --samples 1000000 --seed 20261028
.venv-studio/Scripts/python.exe experiments/plot_preflop_random_equity.py --directory results/preflop_random_equity
```

代表結果：55（5s 5c）は単独勝率59.6667%、引き分け率1.3868%、エクイティ60.3601%（95%区間60.2649〜60.4553%）。全実コンボ数で重み付けしたエクイティは50.002985%です。
