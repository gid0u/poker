from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class Region:
    name: str
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        if (not self.name or any(not isfinite(v) or v < 0 for v in
                                (self.x, self.y, self.width, self.height))
                or self.width <= 0 or self.height <= 0
                or self.x + self.width > 1.000001 or self.y + self.height > 1.000001):
            raise ValueError("Region coordinates must fit within normalized image bounds")


@dataclass(frozen=True)
class Frame:
    source: str
    timestamp_ms: int
    content: bytes
    media_type: str

    def __post_init__(self):
        if not self.source or self.timestamp_ms < 0 or not self.content:
            raise ValueError("Frame needs source, nonnegative timestamp and image bytes")
        if self.media_type not in ("image/png", "image/jpeg"):
            raise ValueError("Supported frame types: PNG and JPEG")


@dataclass(frozen=True)
class Candidate:
    field: str
    value: Any
    confidence: float
    region: str | None = None

    def __post_init__(self):
        if not self.field or not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between zero and one")


@dataclass(frozen=True)
class RecognitionResult:
    provider: str
    version: str
    candidates: tuple[Candidate, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)
