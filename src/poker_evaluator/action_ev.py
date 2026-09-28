"""Decision-time chip EV: payout minus future contributions; folding is zero."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ActionEV:
    action: str
    ev_chips: float
    ev_bb: float | None = None
    standard_error: float | None = None
    samples: int | None = None
    strategy_probability: float | None = None
    source: str = "unknown"
    ci95_low: float | None = None
    ci95_high: float | None = None


def hu_utility_to_stack_delta(utility: float, initial_pot: float,
                              committed_before_decision: float = 0) -> float:
    """Convert legacy HU river-baseline utility to decision-time stack delta."""
    return utility + initial_pot / 2 + committed_before_decision
