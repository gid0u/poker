import unittest
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from collections import Counter
from itertools import product
from math import sqrt

from poker_evaluator.cards import parse_card
from poker_evaluator.range_parser import HandCombo
from poker_evaluator.action_ev import hu_utility_to_stack_delta
from poker_evaluator.cfr import CFRTrainer
from poker_evaluator.engine_router import EngineRouter
from poker_evaluator.multiway import (MultiwayDealDistribution, WeightedRange, RiverGame,
                                     MultiwayMonteCarloEngine, SequentialResponseModel)
from poker_evaluator.multiway.regret_solver import RegretSolver
from poker_evaluator.multiway.response_model import TabularPolicy, info_key

BOARD = ("Ks", "8h", "7d", "3c", "2s")


def hand(a, b):
    return HandCombo(parse_card(a), parse_card(b))


class TestMultiwayResearch(unittest.TestCase):
    def setUp(self):
        self.hands = (hand("As", "Ah"), hand("Kc", "Kh"), hand("Qc", "Qh"))
        self.dist = MultiwayDealDistribution([[h] for h in self.hands], BOARD)
        self.game = RiverGame(BOARD)

    def test_all_terminal_paths_conserve_initial_pot(self):
        for history in [("check",)] + [("bet",) + x for x in product(("fold", "call"), repeat=2)]:
            self.assertAlmostEqual(sum(self.game.payoff(self.hands, history)), 100)

    def test_known_payoffs_and_fold_zero(self):
        self.assertEqual(self.game.payoff(self.hands, ("check",)), (0, 100, 0))
        self.assertEqual(self.game.payoff(self.hands, ("bet", "fold", "fold")), (100, 0, 0))
        self.assertEqual(self.game.payoff(self.hands, ("bet", "call", "call")), (-50, 200, -50))

    def test_split_pot(self):
        game = RiverGame(("As", "Ks", "Qs", "Js", "Ts"))
        hands = (hand("2c", "3c"), hand("4c", "5c"), hand("6c", "7c"))
        for value in game.payoff(hands, ("bet", "call", "call")):
            self.assertAlmostEqual(value, 100 / 3)

    def test_illegal_cards_and_history(self):
        with self.assertRaises(ValueError):
            self.game.payoff((self.hands[0],) * 3, ("check",))
        with self.assertRaises(ValueError):
            self.game.actions(("bet", "raise"))

    def test_validation(self):
        for kwargs in (dict(bet=-1), dict(pot=float("nan")), dict(stacks=(10, 100, 100))):
            with self.assertRaises(ValueError):
                RiverGame(BOARD, **kwargs)
        with self.assertRaises(ValueError):
            RiverGame(("As",) * 5)
        with self.assertRaises(ValueError):
            SequentialResponseModel(p1_call=2)
        with self.assertRaises(ValueError):
            WeightedRange(((self.hands[0], -1),))

    def test_exact_weights_and_sampling_no_sequential_bias(self):
        a, b = hand("As", "Ah"), hand("Qc", "Qh")
        c, d = hand("As", "Ac"), hand("Jc", "Jh")
        dist = MultiwayDealDistribution([WeightedRange(((a, 2), (b, 1))), [c, d], [hand("Tc", "Th")]], BOARD)
        exact = dist.exact()
        self.assertEqual(len(exact), 3)
        self.assertAlmostEqual(sum(x.probability for x in exact), 1)
        expected = {x.hands: x.probability for x in exact}
        draws = dist.sample(12000, seed=123)
        counts = Counter(x.hands for x in draws)
        for hands, p in expected.items():
            self.assertLess(abs(counts[hands] / len(draws) - p), 5 * sqrt(p * (1-p) / len(draws)))
        self.assertEqual(dist.sample(10, 2), dist.sample(10, 2))

    def test_impossible_deals_and_limits(self):
        dist = MultiwayDealDistribution([[self.hands[0]]] * 3, BOARD)
        with self.assertRaises(ValueError):
            dist.exact()
        with self.assertRaises(RuntimeError):
            dist.sample(1, max_attempts=10)
        with self.assertRaises(ValueError):
            self.dist.exact(max_candidates=0)

    def test_sequential_response_ev(self):
        policy = SequentialResponseModel(0, 1, 0)
        engine = MultiwayMonteCarloEngine(self.game, self.dist)
        ev = {x.action: x for x in engine.evaluate(policy, mode="exact")}
        self.assertEqual(ev["check"].ev_chips, 0)
        self.assertEqual(ev["bet"].ev_chips, 150)
        self.assertEqual(ev["bet"].standard_error, 0)

    def test_mc_exact_ci_and_reproducibility(self):
        dist = MultiwayDealDistribution(["AA,QQ", "KK,JJ", "88,TT"], BOARD)
        engine = MultiwayMonteCarloEngine(self.game, dist)
        policy = SequentialResponseModel(.4, .7, .2)
        exact = engine.evaluate(policy, mode="exact")
        sampled = engine.evaluate(policy, samples=3000, seed=42, bb=2)
        self.assertEqual(sampled, engine.evaluate(policy, samples=3000, seed=42, bb=2))
        for a, b in zip(exact, sampled):
            self.assertLess(abs(a.ev_chips-b.ev_chips), 5*b.standard_error)
            self.assertAlmostEqual(b.ci95_high-b.ev_chips, 1.96*b.standard_error)
            self.assertEqual(b.ev_bb, b.ev_chips/2)

    def test_history_conditions_hidden_range(self):
        weak = hand("Jc", "Jh")
        dist = MultiwayDealDistribution([[self.hands[0]], [self.hands[1], weak], [self.hands[2]]], BOARD)
        policy = TabularPolicy({info_key(1, self.hands[1], ("bet",)): (0, 1),
                                info_key(1, weak, ("bet",)): (1, 0)})
        engine = MultiwayMonteCarloEngine(self.game, dist)
        values = engine.evaluate(policy, history=("bet", "call"), mode="exact")
        self.assertEqual([v.ev_chips for v in values], [0, -50])
        values = engine.evaluate(policy, history=("bet", "call"), samples=20)
        self.assertEqual([v.ev_chips for v in values], [0, -50])

    def test_zero_reach_and_bad_sample_count(self):
        engine = MultiwayMonteCarloEngine(self.game, self.dist)
        with self.assertRaises(ValueError):
            engine.evaluate(SequentialResponseModel(0), history=("bet", "call"), mode="exact")
        with self.assertRaises(ValueError):
            engine.evaluate(SequentialResponseModel(), samples=1)

    def test_fixed_hand_conditioning(self):
        dist = MultiwayDealDistribution(["AA,QQ", "KK", "JJ"], BOARD)
        engine = MultiwayMonteCarloEngine(self.game, dist)
        values = engine.evaluate(SequentialResponseModel(), hand=self.hands[0], mode="exact")
        self.assertEqual(values[0].ev_chips, 0)

    def test_regret_matching_learns_dominant_actions(self):
        solver = RegretSolver(self.game, self.dist)
        policy = solver.train(200, 20)
        self.assertGreater(policy.probabilities(1, self.hands[1], ("bet",))[1], .98)
        self.assertLess(solver.convergence[-1]["max_regret_bound"], solver.convergence[0]["max_regret_bound"])
        for p in policy.table.values():
            self.assertAlmostEqual(sum(p), 1)
        # Two calls must be identical to one longer call.
        other = RegretSolver(self.game, self.dist)
        other.train(100)
        self.assertEqual(policy.table, other.train(100).table)

    def test_router_and_legacy_conversion(self):
        engine = MultiwayMonteCarloEngine(self.game, self.dist)
        router = EngineRouter(engine)
        self.assertIsInstance(router.route(2), CFRTrainer)
        self.assertIs(router.route(3), engine)
        self.assertEqual(hu_utility_to_stack_delta(-50, 100), 0)
        with self.assertRaises(ValueError):
            router.route(4)

    def test_router_runs_existing_hu_cfr(self):
        from poker_evaluator.deal_distribution import build_deal_distribution
        router = EngineRouter(None)
        distribution = build_deal_distribution("AA", "KK", board=BOARD)
        self.assertIsInstance(router.train_hu(distribution, 2), float)
        self.assertEqual(router.hu_engine.iterations_completed, 2)

    def test_experiment_writes_reproducible_artifact_schema(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", str(root / "experiments" / "three_player_river.py"),
                                     "--iterations", "2", "--samples", "5", "--output", directory],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in Path(directory).iterdir()},
                             {"config.json", "strategy.csv", "action_ev.csv", "convergence.csv", "run_metadata.json"})
            metadata = json.loads((Path(directory) / "run_metadata.json").read_text())
            self.assertGreater(metadata["legal_deals"], 0)
            self.assertTrue(metadata["source_sha256"])


if __name__ == "__main__":
    unittest.main()
