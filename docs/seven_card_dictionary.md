# 全52C7ハンド評価辞書

標準52枚・ジョーカーなしの7枚集合 **133,784,560通り**をすべて保存する
読取専用辞書です。7枚から最強の5枚を選ぶ通常のポーカールールを使い、
既存の `evaluate7` と同じ評価・キッカー比較を行います。

## 使い方

生成済みの [辞書ZIP](../data/processed/seven_card_dictionary.zip) を展開して使えます。
リポジトリ内の既定場所へ展開する場合は、ルートで次を実行してください。

```powershell
Expand-Archive data/processed/seven_card_dictionary.zip data/processed/seven_card_dictionary
```

ZIPは約10MiB、展開後の本体は約255MiBです。付属 `query.py` なら
プロジェクトをインストールせず、標準ライブラリだけで検索できます。

```python
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary

with SevenCardRankDictionary() as table:
    cards = "As Ks Qs Js Ts 2c 3d"
    print(len(table))        # 133784560
    print(table[cards])      # 1: 最強のロイヤルストレートフラッシュ
    print(table.value(cards))     # (8, 14): 既存評価器と同じタプル
    print(table.category(cards))  # straight_flush
```

空白区切りのカード文字列、`Card` の7要素列、カード文字列の7要素列、
カードIDの7要素列を受け付けます。並び順は問いません。重複カード、不正なID、
7枚以外はエラーになります。同じ強さの別ハンドには同じ順位を返します。
スート自体の優劣はなく、A2345のストレートにも対応します。

順位は既存5枚役7462クラスの **1が最強、7462が最弱** です。
ただし7枚の「ベスト5枚」で実現しない弱い5枚役クラスもあるため、
7枚辞書内で7462種類すべてが使われるわけではありません。
順位は勝率・パーセンタイル・相手レンジに対するequityではありません。

## 保存形式

既定保存先: `data/processed/seven_card_dictionary/`

|ファイル|内容|
|---|---|
|seven_card_ranks.u16|133,784,560個のlittle-endian uint16、267,569,120 bytes|
|seven_card_ranks.json|カード規約、7462役タプル、ハッシュ、生成環境・日時|
|verification.json|全件走査、役別件数、既存評価器との照合結果|
|build_progress.json|再開用の完了位置と役クラス定義|

本体は約255.17 MiB。Pythonの巨大なhash dictやJSONオブジェクトではなく、
メモリマップされた密な配列です。検索時に全件をRAMへ展開しません。
読取は標準ライブラリだけで動作し、生成・全件検査にのみNumPyが必要です。
`dict(table)` や `list(table)` は全件展開になるため避けてください。

カードIDは `4*(rank-2)+suit`、スートは既存実装と同じ `s,c,h,d = 0,1,2,3`。
昇順の7枚IDを `c0,...,c6` とすると、辞書の位置は
`C(c0,1)+C(c1,2)+...+C(c6,7)` です。これは全7枚集合と
0〜133,784,559を一対一に対応させるcombinadic/colex番号です。
`hand_index()` と `index_cards()` で相互変換できます。

通常の読取では形式・完成フラグ・ファイルサイズを確認します。
転送後に内容の破損も検出したい場合は
`SevenCardRankDictionary(directory, verify_checksum=True)` を使用してください。
これは起動時に本体全体のSHA-256を走査します。

## 再生成・検証

リポジトリルートで実行:

```powershell
uv pip install --python .venv-studio/Scripts/python.exe -e ".[dictionary]"
.venv-studio/Scripts/python.exe scripts/build_seven_card_dictionary.py
.venv-studio/Scripts/python.exe scripts/build_seven_card_dictionary.py --verify-only
```

`--output DIRECTORY`、`--chunk-size 500000`、`--oracle-samples 10000`、
`--seed 20261028` を指定できます。同一出力先への同時生成は行わないでください。
生成中は `.partial` と進捗ファイルを保存し、中断後の再実行で完了チャンクから
再開します。完成済みなら上書きせず再検証します。検証に失敗した辞書は
`complete=false` のままになり、検索APIは読み込みを拒否します。
進捗ファイルの書換えや、生成器のアルゴリズムを変えたままの再開は避けてください。

全件を7枚の物理カード集合として列挙します。計算の高速化のため、
49,205種類の合法なランク多重集合の非フラッシュ評価を既存 `evaluate7` で準備し、
実際の各7枚のスート情報からフラッシュ／ストレートフラッシュを別に判定します。
フラッシュでない役とフラッシュ系の強い方を、そのハンドの評価として格納します。
ランク多重集合への圧縮は計算内部だけで、出力には全133,784,560件を保存します。

検証は以下を行います:

- 全件の値域、チェックサム、役カテゴリ件数の検査。
- 境界2件とseed固定で抽出した1万件について、既存 `evaluate7` の
  21通りの5枚評価を使った順位と照合。
- 追加unittestで番号の一意性・逆変換、順序不変性、境界、無効入力、
  2,000件のランダムハンド、wheel SF・2組のtrips・3組のpair等を検査。

全件の別アルゴリズムによる二重評価ではありません。全件格納・全件集計と
抽出照合を組み合わせた検証です。既存CFR・GUI・通常の評価器は変更しません。
展開後の大きいバイナリはGit管理から除外し、圧縮ZIP・生成コード・検証結果を管理します。
