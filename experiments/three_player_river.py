"""Run from repository root: python experiments/three_player_river.py."""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from poker_evaluator.multiway import MultiwayDealDistribution, RiverGame, MultiwayMonteCarloEngine
from poker_evaluator.multiway.regret_solver import RegretSolver


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(output, iterations=1000, samples=10000, seed=42):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = dict(board=["Ks", "8h", "7d", "3c", "2s"], ranges=["AA,QQ", "KK,JJ", "88,TT"],
                  pot=100, bet=50, stacks=[100, 100, 100], iterations=iterations,
                  samples=samples, seed=seed, training_mode="exact", evaluation_mode="sampling")
    dist = MultiwayDealDistribution(config["ranges"], config["board"])
    game = RiverGame(tuple(config["board"]), config["pot"], config["bet"])
    solver = RegretSolver(game, dist)
    policy = solver.train(iterations, max(1, iterations // 20))
    strategy = []
    for (p, cards, history), probs in sorted(policy.table.items()):
        for action, probability in zip(game.actions(history), probs):
            strategy.append(dict(player=p, hand=" ".join("23456789TJQKA"[c.rank-2] + "schd"[c.suit] for c in cards),
                                 history="/".join(history), action=action, probability=probability))
    engine = MultiwayMonteCarloEngine(game, dist)
    evs = []
    for history in ((), ("bet",), ("bet", "fold"), ("bet", "call")):
        for mode in ("exact", "sampling"):
            for value in engine.evaluate(policy, history=history, mode=mode, samples=samples, seed=seed):
                evs.append(dict(player=len(history), history="/".join(history), **asdict(value)))
    write_csv(output / "strategy.csv", strategy)
    write_csv(output / "action_ev.csv", evs)
    write_csv(output / "convergence.csv", solver.convergence)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ("src", "experiments") for p in sorted((ROOT / folder).rglob("*.py"))}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    metadata = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                    revision=revision.stdout.strip() if revision.returncode == 0 else None,
                    source_sha256=hashes, legal_deals=len(solver.deals),
                    ev_baseline="final stack minus decision-time stack", ci="normal 1.96 SE; sampling error only",
                    limitation="Low-regret experimental strategy; not multiplayer GTO or certified Nash equilibrium")
    for name, data in (("config.json", config), ("run_metadata.json", metadata)):
        (output / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(dict(output=str(output), legal_deals=len(solver.deals), final=solver.convergence[-1])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "three_player_river")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(args.output, args.iterations, args.samples, args.seed)
