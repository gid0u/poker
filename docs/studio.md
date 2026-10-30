# Recorded poker video research studio

## Start

The desktop GUI uses Tkinter and the database uses SQLite (Python standard library).
Run from the repository root using Python 3.13+ with Tk installed:

```powershell
uv venv .venv-studio --python 3.14
uv pip install --python .venv-studio/Scripts/python.exe -e ".[media]" pytest
.venv-studio/Scripts/poker-studio.exe
```

Alternatively `scripts/start_studio.ps1` sets the source path and launches the
dedicated environment if present. `python -m poker_evaluator.gui --db PATH` selects
a database. The default is `data/local/poker_studio.sqlite3` relative to the current
directory. The launcher always uses the repository root. Installations without the
optional media extra can import/preview PNG images and evaluate manual inputs.
JPEG preview needs Pillow; video decoding needs OpenCV. Neither is required by
the existing poker engines.

## Workflow

1. Create/select a recording session.
2. Import PNG/JPEG screenshots, or select a local recording and time in seconds.
   Video decoding seeks one frame and records the backend's reported timestamp.
3. Select a region name and drag on the image to define a normalized rectangle.
   Regions persist as the default layout profile and apply to subsequent imports.
   Clear/redefine the profile when the broadcast layout changes.
4. Review recognition candidates and warnings. Currently there is **no trained
   card recognition or OCR**: the manual provider returns no invented values.
5. Enter board, three assumed ranges, pot, bet and stacks. Confirm and evaluate.
   Only five-card river boards are supported by this analysis adapter. Early
   street footage can be retained as evidence but cannot yet be evaluated.
6. View check/bet EV, SE and normal-approximation 95%CI. Export CSV, reload saved
   inputs/results, or back up the entire database from the GUI.

The example button inserts synthetic research assumptions and detaches the frame
reference, so demo values are never presented as facts recognized from video.
Selecting a frame does not overwrite fields: review them before confirming.
Opponent ranges are user assumptions, not something inferred from hidden cards.
Call probabilities are P1, P2 after P1 fold, and P2 after P1 call. This is fixed-model
EV evaluation, **not a live GTO solver or equilibrium certification**.

## Architecture

`capture.sources.FrameSource -> Frame -> capture.recognition.Recognizer ->
RecognitionResult -> SQLite evidence -> human-confirmed snapshot -> StudioService
-> existing MultiwayMonteCarloEngine -> saved analysis`

`FrameSource.frames()` yields images with source and timestamp. Implement this
protocol for a future stream decoder; the current OpenCV adapter deliberately
accepts local recordings only. Do not do unbounded decoding on the Tk UI thread.
An ingest job can store a bounded batch via `OpenCVVideoSource(max_frames=...)`.
Each frame is committed independently; partial batches survive decoder failure.

`Recognizer.recognize(frame, regions)` returns provider/version, typed field
candidates, confidence in [0,1], region names, and warnings. Candidates stay
separate from confirmed game facts. Add recognition implementations without
modifying CFR or card evaluators. The current GUI shows candidates as evidence;
it does not automatically promote them into confirmed values. Future work includes
card templates/models, pot/stack OCR, confidence calibration, temporal tracking,
hand boundaries, player-seat mapping and stream reconnection/backpressure.

Regions are resolution-independent x/y/width/height values in [0,1]. Each captured
frame records the region definitions used by its recognition job. Editing a
profile does not rewrite historical recognition evidence.

## Database and provenance

Schema v1 (`PRAGMA user_version`), foreign keys enabled on every connection,
parameterized statements, explicit transactions, WAL and a 10-second busy timeout:

|Table|Purpose|
|---|---|
|sessions|Recording/research sessions and UTC creation time|
|profiles|Named normalized region definitions|
|frames|Image bytes, source, timestamp, SHA-256, recognition result and regions|
|snapshots|Immutable confirmed state JSON linked to optional frame|
|analyses|Input snapshot, seed, samples, response model, Python/source hash, ActionEV rows|

Images live in BLOBs so backups remain self-contained and source-file deletion
does not lose evidence. File imports are limited to 25 MiB; large archives will
eventually need a managed object store and retention policies. The full source
path is local provenance; database and WAL files are excluded from Git. Use the
GUI's SQLite backup API for consistent copies, rather than copying a live WAL
database file alone. Existing backups are not overwritten. A newer schema is
rejected; future migrations must be sequential and preserve these relationships.

Each worker operation uses its own connection. GUI widgets are touched only on
the main thread via a queue. Closing and switching sessions are blocked while a
worker is saving/evaluating. State validation rejects illegal cards, unsupported
streets/player counts and stacks too small for the no-side-pot game. Confirmation
and analysis are separate: if analysis fails, the confirmed input remains in
history as unevaluated.

## Validation

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv-studio/Scripts/python.exe -B -m pytest -p no:cacheprovider -q
.venv-studio/Scripts/python.exe -B -m unittest discover -s tests -q
.venv-studio/Scripts/python.exe -B scripts/smoke_studio.py
```

Tests cover persistence, backup, session isolation, invalid state handling,
recognizer separation, reproducibility, and a generated video decoded by real
OpenCV when media dependencies are installed. The GUI smoke exercise uses real
Tk widgets with a temporary database and a generated image. It needs Tk/Pillow
and a desktop session. It opens no persistent user database.

## パネルによるカード入力

「2 確認・評価」「4 ワイルドカード」「5 相対勝率」の選択ボタンから、文字を打たずに入力できます。

1. 「パネルで選択」を押し、必要なら「全消去」で例のカードを消します。
2. 52枚のカードをクリックします。入力済みの枠を押すと置換、＋追加で末尾追加、選択枠を削除で削除できます。
3. ワイルドカード一覧の「X 無条件」「X♠」「QO」などを直接クリックすると、無条件X、X1s、Qoを追加できます。X番号は削除・置換後も出現順に振り直します。
4. 「適用」で元の入力欄へ反映。「キャンセル」では元の値を保持します。
5. 相対勝率の未知カードは「詳細X条件」のパネルで手札2枚・フロップ3枚・ターン・リバーの順に7枚選び、exactで計算します。通常の手札・ボード欄より優先されます。

相手レンジは「相手番号」を選んで「相手レンジをパネルで選択」を押します。13×13表のペア・同スート(s)・異スート(o)をクリックして切り替えます。「全ハンド(random)」も選択可能です。空のレンジを適用するとその相手を削除します。相手は1人目から順番に追加します。途中の相手を自動でrandomとして追加することはありません。

実カードの同一欄内の重複は選択できません。別欄との重複や成立しないスート条件は計算時の既存検証でエラーになります。数値や任意のカード重みJSONは従来どおり入力します。


## 入力パネルと再計算の整合性（2026-10-30）

- `AK`はAKsとAKo、`QQ+`はQQ/KK/AAのセルを選択状態で表示します。既存パーサーと同じ範囲を保持します。無効なレンジはエラーを表示し、元の入力を保持します。
- 新しい相手は現在人数の次の番号に追加します。番号を飛ばして相手を増やせません。
- 相対勝率・ワイルドカードで計算をやり直すと、前回の表示と保存対象を消去します。入力検証や計算が失敗した場合、前回の結果を新しい結果と取り違えて保存できません。
- 相対勝率の結果欄には、計算に実際に使用したカード条件と相手人数を表示します。
- 相対勝率と3人配布のサンプリングは累積重みを事前計算します。合法配布の分布と同seedの抽選順を維持します。

## ボード別エクイティ分布と研究履歴

「5 相対勝率」で実カードの手札2枚、ボード3・4・5枚、相手レンジ1人を入力し「ボード別分布を計算」を押します。最終ボードごとに相手レンジに対するエクイティを全列挙し、平均・分散・10%点・中央値・90%点・10区間のヒストグラムを表示します。相手と両立するコンボの重みで最終ボードを重み付けするため、狭いレンジでも単純な等平均になりません。計算上限は200万配布です。

「分布をDB保存」「相対勝率をDB保存」は上部の選択中セッションにそれぞれ保存します。「研究結果の履歴」で選択・再表示できます。データベースは初回起動時にv1からv2へ移行し、従来の映像・EV履歴を保持します。DBの一貫したバックアップには上部の「DBバックアップ」を使用してください。

ボード別分布は現時点では実カード、相手1人、フロップ以降、全列挙のみです。詳細X条件、複数相手、プリフロップ、分布のサンプリング推定は未対応です。相対勝率の従来機能は利用できます。分布はボードごとに相手レンジを平均したショーダウンエクイティの分布であり、ベットEVや単一配布の勝敗分布ではありません。
