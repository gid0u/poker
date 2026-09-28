"""Application boundary: reviewable evidence -> confirmed state -> engine."""
from dataclasses import asdict
import hashlib
from pathlib import Path
import platform

from .capture.recognition import ManualRecognizer
from .multiway import MultiwayDealDistribution, RiverGame, MultiwayMonteCarloEngine, SequentialResponseModel


def validate_state(state):
    # Serialize only the supported fields, never silently interpret OCR as facts.
    required = ("board", "ranges", "pot", "bet", "stacks")
    if any(k not in state for k in required):
        raise ValueError("Board, three ranges, pot, bet and stacks are required")
    game = RiverGame(tuple(state["board"]), float(state["pot"]), float(state["bet"]),
                     tuple(float(s) for s in state["stacks"]))
    if len(state["ranges"]) != 3 or any(not isinstance(r, str) for r in state["ranges"]):
        raise ValueError("Three range strings are required")
    dist = MultiwayDealDistribution(state["ranges"], game.board)
    # Bounded legality check, independent of GUI state. Reject impossible inputs.
    dist.sample(1, seed=0, max_attempts=10000)
    return dict(board=list(state["board"]), ranges=list(state["ranges"]), pot=game.pot,
                bet=game.bet, stacks=list(game.stacks))


class StudioService:
    def __init__(self, repository, recognizer=None):
        self.repository = repository
        self.recognizer = recognizer or ManualRecognizer()

    def ingest(self, session_id, source, regions=()):
        saved = []
        for frame in source.frames():
            result = self.recognizer.recognize(frame, tuple(regions))
            identifier = self.repository.save_frame(session_id, frame, result, regions)
            saved.append(identifier)
        if not saved:
            raise ValueError("指定した時刻のフレームを取得できませんでした")
        return saved

    def confirm(self, session_id, state, frame_id=None):
        return self.repository.confirm_snapshot(session_id, validate_state(state), frame_id)

    def analyze(self, snapshot_id, *, samples=10000, seed=42, calls=(.5, .5, .5)):
        if not isinstance(samples, int) or not 2 <= samples <= 100000:
            raise ValueError("Samples must be between 2 and 100000")
        state = self.repository.snapshot(snapshot_id)["state"]
        state = validate_state(state)
        game = RiverGame(tuple(state["board"]), state["pot"], state["bet"], tuple(state["stacks"]))
        dist = MultiwayDealDistribution(state["ranges"], game.board)
        policy = SequentialResponseModel(*calls)
        values = MultiwayMonteCarloEngine(game, dist).evaluate(policy, samples=samples, seed=seed)
        root = Path(__file__).parent
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*.py")):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
        config = dict(samples=samples, seed=seed, call_probabilities=list(calls),
                      python=platform.python_version(), source_sha256=digest.hexdigest(),
                      baseline="decision-time stack delta", engine="three-player-monte-carlo",
                      note="Fixed opponent model; not GTO. CI measures sampling error only.")
        rows = [asdict(v) for v in values]
        identifier = self.repository.save_analysis(snapshot_id, config, rows)
        return identifier, rows
