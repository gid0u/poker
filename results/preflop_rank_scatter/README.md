# プリフロップの予想順位 × 順位分散（全列挙）

`preflop_rank_scatter.png` / `.svg` / `.pdf` が散布図、CSVが169種類すべての数値、metadata.jsonが計算条件です。

各手札の代表的な実カード2枚を固定し、残り50枚から5枚を選ぶ全2,118,760ボードを等確率で評価しました。スート置換による対称性で169種類を代表させています。相手・除外カードの条件はありません。総評価数は358,070,440です。計算はサンプリングではなく全列挙で、整数の順位和・二乗和から平均と母分散を求めます。

- 横軸：最終7枚の平均順位。左ほど平均順位が強い（順位1が最強）。
- 縦軸：最終7枚の順位分散。高いほど完成時の順位がばらつく。
- 赤：ペア、緑：同スート、青：異スート。
- 破線・点線：全52C7の平均順位・分散。点線の分散は条件付き分散の平均ではなく、手札間の平均順位の差も含む全体分散です。

各種類の実コンボ数（ペア6、同スート4、異スート12）で重み付けした平均と、全分散の公式で復元した分散は、既存の全7枚辞書の集計値に一致しました。公開APIとの個別参照チェックも行っています。

順位は役の順序を数値化した指標で、その差が勝率差やチップEV差を表すわけではありません。高分散が有利・不利かは相手・ボード・意思決定条件によります。プリフロップの戦略推奨や相手に対する勝率ではありません。

再生成（リポジトリのルートで実行、numpyが必要）：

```powershell
$env:PYTHONPATH="$PWD\src"
.venv-studio/Scripts/python.exe experiments/preflop_rank_scatter.py --dictionary data/processed/seven_card_dictionary --output results/preflop_rank_scatter
# 描画はmatplotlibが必要
.venv-studio/Scripts/python.exe experiments/plot_preflop_rank_scatter.py --directory results/preflop_rank_scatter
```
