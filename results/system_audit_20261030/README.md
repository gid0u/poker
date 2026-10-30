# システム点検・修正（2026-10-30）

## 修正した問題

1. **相手人数の意図しない増加**：相手番号を飛ばすと未入力の相手がrandomで自動追加されていた。次の相手だけ追加可能に変更。空行は計算時と同様に無視。既存相手の置換・削除は維持。
2. **レンジパネルの表示と実体の不一致**：AK、QQ+等は文字列のまま保持され、対応セルが未選択に見えていた。既存レンジパーサーで169セルへ展開し、表示と適用結果を一致させた。無効入力はエラー表示して元の値を保持。
3. **再計算失敗後の古い結果保存**：相対勝率・ワイルドカードの計算開始時に表示・保存対象をリセット。相対勝率は計算に使ったカードと相手人数を結果に表示し、入力欄を後から編集しても計算条件を確認可能。
4. **抽選処理での重複作業**：相対勝率と3人配布生成で累積重みを事前計算。相対勝率はデッキ生成もループ外へ移動。全配布棄却法と乱数列を維持。

## 検証

- pytest全体：465 passed（23.89秒、6件の入力回帰テスト追加）。
- 実Tk GUI：通常操作、カードパネル、今回の回帰確認の3スクリプトが成功。
- 1万サンプル、seed=733の処理結果を修正前後でSHA-256比較：相対勝率の全結果、3人配布全件が両方とも完全一致。
- 単発計測：相対勝率0.898秒→0.139秒（約6.4倍）、3人配布0.177秒→0.094秒（約1.9倍）。相対勝率計測では抽選処理を測るため軽量な合成スコア関数を使用。実際の役判定・条件を含む全処理で同じ倍率を保証する値ではない。生データはsampling_before.json / sampling_after.json。

再確認：

```powershell
$env:PYTHONPATH="$PWD\src"
.venv-studio/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv-studio/Scripts/python.exe scripts/smoke_gui_audit.py
.venv-studio/Scripts/python.exe scripts/smoke_card_panel.py
.venv-studio/Scripts/python.exe scripts/smoke_studio.py
.venv-studio/Scripts/python.exe experiments/benchmark_sampling_audit.py
```

## 残る課題

画像のカード/OCR自動認識、相対勝率・ワイルドカード結果のSQLite履歴への統合、GUIからの中断操作は今回未実装。サンプリングの95%区間は従来の正規近似のままで、極端な確率や少数標本への改善は別途必要。
