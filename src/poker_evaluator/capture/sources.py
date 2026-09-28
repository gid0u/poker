"""File input works without optional dependencies; video decoding uses OpenCV."""
from pathlib import Path
from typing import Protocol, Iterator
from .models import Frame

MAX_IMAGE_BYTES = 25 * 1024 * 1024


class FrameSource(Protocol):
    def frames(self) -> Iterator[Frame]: ...


class ImageFileSource:
    def __init__(self, path, timestamp_ms=0):
        self.path = Path(path).resolve()
        self.timestamp_ms = timestamp_ms

    def frames(self):
        if self.path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds 25 MiB limit")
        content = self.path.read_bytes()
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            kind = "image/png"
        elif content.startswith(b"\xff\xd8\xff"):
            kind = "image/jpeg"
        else:
            raise ValueError("Select a PNG or JPEG image")
        yield Frame(str(self.path), self.timestamp_ms, content, kind)


class OpenCVVideoSource:
    """Bounded recorded-video sampling. URL/network capture is intentionally separate."""
    def __init__(self, path, start_ms=0, interval_ms=1000, max_frames=1):
        self.path = Path(path).resolve()
        if start_ms < 0 or interval_ms <= 0 or max_frames <= 0:
            raise ValueError("Invalid video sampling parameters")
        self.start_ms, self.interval_ms, self.max_frames = start_ms, interval_ms, max_frames

    def frames(self):
        if not self.path.is_file():
            raise ValueError("Select a local video file")
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("動画入力には opencv-python が必要です。python -m pip install opencv-python") from exc
        capture = cv2.VideoCapture(str(self.path))
        try:
            if not capture.isOpened():
                raise ValueError("Cannot open video")
            for i in range(self.max_frames):
                requested = self.start_ms + i * self.interval_ms
                if not capture.set(cv2.CAP_PROP_POS_MSEC, requested):
                    raise ValueError("Video backend cannot seek to this timestamp")
                ok, pixels = capture.read()
                if not ok:
                    break
                actual = max(0, round(capture.get(cv2.CAP_PROP_POS_MSEC)))
                ok, encoded = cv2.imencode(".png", pixels)
                if not ok:
                    raise ValueError("Cannot encode video frame")
                yield Frame(str(self.path), actual, encoded.tobytes(), "image/png")
        finally:
            capture.release()
