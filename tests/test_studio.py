import base64
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from poker_evaluator.capture.models import Candidate, Frame, RecognitionResult, Region
from poker_evaluator.capture.sources import ImageFileSource, OpenCVVideoSource
from poker_evaluator.storage import Repository
from poker_evaluator.studio import StudioService, validate_state

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII=")
STATE = dict(board=["Ks", "8h", "7d", "3c", "2s"], ranges=["AA,QQ", "KK,JJ", "88,TT"],
             pot=100, bet=50, stacks=[100, 100, 100])


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = Repository(self.root / "test.sqlite3")
        self.session = self.db.create_session("Recorded table")
        self.service = StudioService(self.db)
        self.image = self.root / "frame.png"
        self.image.write_bytes(PNG)

    def test_schema_reopen_and_foreign_keys(self):
        reopened = Repository(self.db.path)
        self.assertEqual(reopened.sessions()[0]["id"], self.session)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.confirm_snapshot("missing", STATE)

    def test_newer_schema_rejected(self):
        with self.db.connect() as conn:
            conn.execute("PRAGMA user_version=2")
        with self.assertRaises(ValueError):
            Repository(self.db.path)

    def test_image_evidence_and_manual_recognition(self):
        frame_id = self.service.ingest(self.session, ImageFileSource(self.image))[0]
        row = self.db.frame(frame_id)
        self.assertEqual(row["content"], PNG)
        self.assertEqual(len(row["sha256"]), 64)
        result = json.loads(row["recognition_json"])
        self.assertEqual(result["candidates"], [])
        self.assertTrue(result["warnings"])
        self.assertEqual(self.db.history(self.session), [])

    def test_fake_recognizer_keeps_uncertain_observations_separate(self):
        class Recognizer:
            def recognize(self, frame, regions):
                return RecognitionResult("test", "2", (Candidate("pot", 100, .6, "pot"),))
        region = Region("pot", .1, .2, .3, .4)
        service = StudioService(self.db, Recognizer())
        identifier = service.ingest(self.session, ImageFileSource(self.image), [region])[0]
        evidence = json.loads(self.db.frame(identifier)["recognition_json"])
        self.assertEqual(evidence["candidates"][0]["confidence"], .6)
        self.assertEqual(evidence["regions"][0]["name"], "pot")
        self.assertEqual(self.db.history(self.session), [])

    def test_confirm_analyze_roundtrip_and_reproducibility(self):
        frame_id = self.service.ingest(self.session, ImageFileSource(self.image))[0]
        snapshot = self.service.confirm(self.session, STATE, frame_id)
        first, rows = self.service.analyze(snapshot, samples=200, seed=42)
        second, repeated = self.service.analyze(snapshot, samples=200, seed=42)
        self.assertEqual(rows, repeated)
        self.assertNotEqual(first, second)
        self.assertEqual(len(self.db.history(self.session)), 2)
        self.assertEqual(self.db.snapshot(snapshot)["state"], STATE)
        config = json.loads(self.db.history(self.session)[0]["config_json"])
        self.assertEqual(config["seed"], 42)
        self.assertEqual(len(config["source_sha256"]), 64)

    def test_frame_session_mismatch_rejected(self):
        identifier = self.service.ingest(self.session, ImageFileSource(self.image))[0]
        other = self.db.create_session("Other")
        with self.assertRaises(ValueError):
            self.service.confirm(other, STATE, identifier)
        self.assertEqual(self.db.history(other), [])

    def test_invalid_state_does_not_create_snapshot(self):
        for change in (dict(board=["As"]*5), dict(pot=float("nan")), dict(stacks=[1, 100, 100]),
                       dict(ranges=["AA", "KK"]), dict(board=["As", "Ks", "Qs"])):
            with self.assertRaises(ValueError):
                self.service.confirm(self.session, {**STATE, **change})
        self.assertEqual(self.db.history(self.session), [])

    def test_analysis_limits(self):
        identifier = self.service.confirm(self.session, STATE)
        for samples in (1, 100001):
            with self.assertRaises(ValueError):
                self.service.analyze(identifier, samples=samples)
        with self.assertRaises(ValueError):
            self.service.analyze(identifier, samples=20, calls=(1.1, .5, .5))

    def test_profile_roundtrip_and_validation(self):
        region = Region("board", .1, .1, .8, .5)
        self.db.save_regions("default", [region])
        self.assertEqual(self.db.regions("default"), (region,))
        self.db.save_regions("default", [])
        self.assertEqual(self.db.regions("default"), ())
        for args in (("bad", 0, 0, 2, 1), ("bad", 0, 0, 0, 1)):
            with self.assertRaises(ValueError):
                Region(*args)
        with self.assertRaises(ValueError):
            Candidate("pot", 100, float("nan"))

    def test_database_backup_contains_binary_evidence(self):
        identifier = self.service.ingest(self.session, ImageFileSource(self.image))[0]
        destination = self.root / "backup.sqlite3"
        self.db.backup(destination)
        backup = Repository(destination)
        self.assertEqual(backup.frame(identifier)["content"], PNG)
        with self.assertRaises(ValueError):
            self.db.backup(destination)
        with self.assertRaises(ValueError):
            self.db.backup(self.db.path)

    def test_image_type_and_empty_video(self):
        bad = self.root / "bad.png"
        bad.write_text("not image")
        with self.assertRaises(ValueError):
            list(ImageFileSource(bad).frames())
        with self.assertRaises(ValueError):
            list(OpenCVVideoSource(self.root / "missing.mp4").frames())
        class Empty:
            def frames(self):
                return iter(())
        with self.assertRaises(ValueError):
            self.service.ingest(self.session, Empty())

    def test_session_name_is_not_sql(self):
        self.db.create_session("'; DROP TABLE sessions; --")
        self.assertEqual(len(self.db.sessions()), 2)

    def test_real_video_decode_when_media_installed(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("Optional media dependencies not installed")
        path = self.root / "sample.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
        self.assertTrue(writer.isOpened())
        try:
            for i in range(10):
                writer.write(np.full((48, 64, 3), i*20, dtype=np.uint8))
        finally:
            writer.release()
        frames = list(OpenCVVideoSource(path, start_ms=100, interval_ms=200, max_frames=3).frames())
        self.assertEqual(len(frames), 3)
        self.assertTrue(all(frame.content.startswith(b"\x89PNG") for frame in frames))
        self.assertEqual([f.timestamp_ms for f in frames], [100, 300, 500])
        self.assertEqual(list(OpenCVVideoSource(path, start_ms=10000).frames()), [])


if __name__ == "__main__":
    unittest.main()
