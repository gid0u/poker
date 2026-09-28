# Poker evaluator / three-player river research

## Desktop studio / 映像入力・データベース・GUI

録画・配信映像のスクリーンショット／動画フレームを取り込み、読取領域を指定し、
確認済みの入力と研究用EVをSQLiteへ保存できるデスクトップGUIを追加しました。
起動: `powershell -ExecutionPolicy Bypass -File scripts/start_studio.ps1`
（初回の環境構築・操作・拡張方法は [Studio documentation](docs/studio.md)）。
カード自動認識・OCRは今後接続する接口を用意した段階です。現時点では人が確認・入力します。

Existing heads-up CFR, DealDistribution, game state and card evaluation code are
preserved. The experimental engine lives independently in `multiway/` and reuses
the existing real-card `HandCombo`, range parser and seven-card evaluator.

## Game and EV convention

Exactly three players, five fixed board cards, one fixed bet size, no raises,
no side pots, no rake. P0 checks directly to a three-way showdown or bets;
P1 folds/calls, then P2 folds/calls after observing P1. All stacks cover the bet.
Checks do not permit opponents to initiate a bet. Four or more players are not
implemented. Ties split chips fractionally (no odd-chip rule).

`ActionEV.ev_chips = final stack - stack at the decision being evaluated`.
Past contributions are sunk. Fold EV is zero; the three root payoffs sum to the
initial pot, rather than zero. Legacy HU utility retains its original zero-sum
baseline. `hu_utility_to_stack_delta` adds half the initial river pot and the
player's contributions already made before the decision; do not mix raw HU
utility with ActionEV.

## Distributions and estimates

`WeightedRange` accepts `(HandCombo, weight)` entries. Plain range strings (AA,
KK, QQ, AKs, etc.) or HandCombo iterables are uniform sets. Duplicate weighted
entries are merged; weights must be finite and nonnegative. Board blockers are
removed. Joint deal probability is proportional to the product of the three
range weights, conditioned on no card overlap.

`MultiwayDealDistribution.exact()` enumerates up to two million candidate deals.
`sample(n, seed)` rejects complete independent draws, avoiding the bias of
sequential range renormalization. Very incompatible ranges may exhaust a bounded
rejection budget; this is an explicit error, never silent biased output.

`MultiwayMonteCarloEngine.evaluate(policy, history=(), hand=None, mode='sampling')`
returns the legal action EVs (check/bet or fold/call). A supplied hand conditions
on the acting player's private cards. Without it results are range averages.
Observed histories condition the hidden-card distribution by policy reach.
Policies receive only own hand and public history, never opponents' cards.
Future fold/call branches are integrated exactly for each sampled deal to reduce
variance. Standard error uses unbiased sample variance / n; 95% CIs are normal
approximations `mean +/- 1.96 SE`, not finite-sample guarantees. They quantify
sampling error only, not opponent-model error or equilibrium uncertainty. Exact
evaluation reports zero sampling SE and a degenerate CI, with sample count
meaning enumerated positive-reach deals. Across actions common deals induce
correlation; marginal CIs are not CIs for EV differences.

## Approximate strategy, not multiplayer GTO

これは多人数GTOソルバーではなく、限定ゲームの近似均衡／低後悔戦略を
研究する基盤です。低後悔であってもNash均衡への収束は保証しません。

`RegretSolver` uses simultaneous counterfactual regret matching, freezing each
iteration's policies across all deals. Information sets contain player, own
exact cards and public history. It exports averaged behavioral strategies and
per-player sums of positive maximum cumulative counterfactual regrets divided by
iteration count. These are external-regret upper bounds for the sequence of play,
NOT exploitability/Nash-gap measurements of the averaged profile. Multiplayer
no-regret learning does not imply that the product of averaged strategies is a
Nash equilibrium. No equilibrium certification or best-response gap is claimed.
Training currently enumerates all deals; sampling is available for EV estimation.

`EngineRouter.route(2)` selects existing CFR, and `train_hu` accepts an explicitly
prepared two-player ChanceDistribution. It is a skeleton: automatic continuation
conversion, posterior ranges, folded-player card removal, stack/commitment
mapping and action-tree equivalence remain to be implemented. A fold inside this
restricted three-player game continues under its own no-raise rules; blindly
switching to legacy HU would change the game.

## Reproduce

With a working Python >=3.13 environment and the project's test dependencies:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m pytest -q
python -m unittest discover -s tests -q
python experiments/three_player_river.py --iterations 1000 --samples 10000 --seed 42
```

On the inspected machine the old `.venv` Python launcher no longer starts.
Validation used installed Python 3.14 with the existing pure-Python pytest
packages, disabling unrelated plugin autoload (the old Hypothesis native module
is incompatible). No existing tests import Hypothesis. The exact working commands:

```powershell
$env:PYTHONPATH = "$PWD\src;$PWD\.venv\Lib\site-packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -B -m pytest -p no:cacheprovider -q
python -B -m unittest discover -s tests -q
```

Results default to `results/three_player_river/`: config.json, strategy.csv,
action_ev.csv (exact and Monte Carlo for all four decision histories),
convergence.csv, run_metadata.json (UTC, Python, seed via config, git revision
when available, and source SHA-256 hashes). Reusing an output directory replaces
its five result files; use `--output` to preserve separate runs.

New tests cover accounting, splits, blockers, weighted rejection distributions,
sequential/posterior responses, exact-vs-MC estimates, CI arithmetic,
reproducibility, validation, regret matching and routing. Existing tests remain
unchanged. Follow-up research: more boards/ranges/seeds/bet sizes, independent
best-response diagnostics, sampled training, general betting trees and a fully
validated HU continuation adapter.
