"""SQLite storage. Each operation owns its connection, safe for GUI workers."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


class Repository:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValueError("Database schema is newer than this application")
            conn.execute("PRAGMA journal_mode=WAL")
            if version == 0:
                conn.executescript('''
                    BEGIN;
                    CREATE TABLE sessions(id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE TABLE profiles(name TEXT PRIMARY KEY, regions_json TEXT NOT NULL);
                    CREATE TABLE frames(
                        id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                        source TEXT NOT NULL, timestamp_ms INTEGER NOT NULL CHECK(timestamp_ms >= 0),
                        media_type TEXT NOT NULL, content BLOB NOT NULL, sha256 TEXT NOT NULL,
                        recognition_json TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE TABLE snapshots(
                        id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                        frame_id TEXT REFERENCES frames(id), state_json TEXT NOT NULL,
                        confirmed_at TEXT NOT NULL);
                    CREATE TABLE analyses(
                        id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                        config_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE INDEX frames_session ON frames(session_id, created_at);
                    CREATE INDEX snapshots_session ON snapshots(session_id, confirmed_at);
                    PRAGMA user_version=1;
                    COMMIT;
                ''')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def create_session(self, name):
        if not name.strip():
            raise ValueError("Session name is required")
        identifier = uuid4().hex
        with self.connect() as conn:
            conn.execute("INSERT INTO sessions VALUES(?,?,?)", (identifier, name.strip(), now()))
        return identifier

    def sessions(self):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM sessions ORDER BY created_at DESC")]

    def save_frame(self, session_id, frame, recognition, regions=()):
        identifier = uuid4().hex
        from dataclasses import asdict
        evidence = recognition.to_dict()
        evidence["regions"] = [asdict(r) for r in regions]
        with self.connect() as conn:
            conn.execute("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?,?)", (
                identifier, session_id, frame.source, frame.timestamp_ms, frame.media_type,
                frame.content, hashlib.sha256(frame.content).hexdigest(), encode(evidence), now()))
        return identifier

    def frames(self, session_id):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id,source,timestamp_ms,created_at FROM frames WHERE session_id=? ORDER BY created_at DESC",
                (session_id,))]

    def frame(self, identifier):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM frames WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise ValueError("Frame not found")
            return dict(row)

    def confirm_snapshot(self, session_id, state, frame_id=None):
        identifier = uuid4().hex
        with self.connect() as conn:
            if frame_id is not None:
                frame = conn.execute("SELECT session_id FROM frames WHERE id=?", (frame_id,)).fetchone()
                if frame is None or frame[0] != session_id:
                    raise ValueError("Frame belongs to another session or does not exist")
            conn.execute("INSERT INTO snapshots VALUES(?,?,?,?,?)",
                         (identifier, session_id, frame_id, encode(state), now()))
        return identifier

    def snapshot(self, identifier):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM snapshots WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise ValueError("Snapshot not found")
            result = dict(row)
            result["state"] = json.loads(result.pop("state_json"))
            return result

    def save_analysis(self, snapshot_id, config, results):
        identifier = uuid4().hex
        with self.connect() as conn:
            conn.execute("INSERT INTO analyses VALUES(?,?,?,?,?)",
                         (identifier, snapshot_id, encode(config), encode(results), now()))
        return identifier

    def history(self, session_id):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute('''
                SELECT s.id, s.confirmed_at, s.frame_id, a.id AS analysis_id,
                       a.config_json, a.result_json FROM snapshots s
                LEFT JOIN analyses a ON a.snapshot_id=s.id
                WHERE s.session_id=? ORDER BY s.confirmed_at DESC, a.created_at DESC
            ''', (session_id,))]

    def save_regions(self, name, regions):
        from dataclasses import asdict
        if not name.strip() or len({r.name for r in regions}) != len(regions):
            raise ValueError("Profile and unique region names required")
        with self.connect() as conn:
            conn.execute("INSERT INTO profiles VALUES(?,?) ON CONFLICT(name) DO UPDATE SET regions_json=excluded.regions_json",
                         (name, encode([asdict(r) for r in regions])))

    def regions(self, name):
        from .capture.models import Region
        with self.connect() as conn:
            row = conn.execute("SELECT regions_json FROM profiles WHERE name=?", (name,)).fetchone()
        return tuple(Region(**r) for r in json.loads(row[0])) if row else ()

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path or destination.exists():
            raise ValueError("Choose a new backup filename")
        with self.connect() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
            finally:
                target.close()
