from typing import Protocol
from .models import Frame, Region, RecognitionResult


class Recognizer(Protocol):
    def recognize(self, frame: Frame, regions: tuple[Region, ...]) -> RecognitionResult: ...


class ManualRecognizer:
    """Honest placeholder: no fabricated cards, pots or confidence scores."""
    def recognize(self, frame, regions=()):
        return RecognitionResult("manual", "1", warnings=(
            "カード認識・OCRは未接続です。画像を確認し、入力欄を手動で補完してください。",))
