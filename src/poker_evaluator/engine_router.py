"""Routing boundary only: callers must construct a valid conditioned HU state."""
from dataclasses import dataclass, field
from .cfr import CFRTrainer


@dataclass
class EngineRouter:
    multiway_engine: object
    hu_engine: CFRTrainer = field(default_factory=CFRTrainer)

    def route(self, active_players):
        if active_players == 2:
            return self.hu_engine
        if active_players == 3:
            return self.multiway_engine
        raise ValueError("Supported active player counts are two and three")

    def train_hu(self, distribution, iterations):
        if any(len(d.state.players) != 2 for d in distribution.outcomes):
            raise ValueError("HU adapter requires a remapped two-player distribution")
        return self.hu_engine.train_distribution(distribution, iterations)
