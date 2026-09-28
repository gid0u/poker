# Recorded poker video research studio

## Start

The desktop GUI uses Tkinter and the database uses SQLite (Python standard library).
Run from the repository root using Python 3.13+ with Tk installed:

```powershell
uv venv .venv-studio --python 3.14
uv pip install --python .venv-studio/Scripts/python.exe -e ".[media]" pytest
.venv-studio/Scripts/poker-studio.exe
```

Alternatively `scripts/start_studio.ps1` sets the source path and launches the
dedicated environment if present. `python -m poker_evaluator.gui --db PATH` selects
a database. The default is `data/local/poker_studio.sqlite3` relative to the current
directory. The launcher always uses the repository root. Installations without the
optional media extra can import/preview PNG images and evaluate manual inputs.
JPEG preview needs Pillow; video decoding needs OpenCV. Neither is required by
the existing poker engines.

## Workflow

1. Create/select a recording session.
2. Import PNG/JPEG screenshots, or select a local recording and time in seconds.
   Video decoding seeks one frame and records the backend's reported timestamp.
3. Select a region name and drag on the image to define a normalized rectangle.
   Regions persist as the default layout profile and apply to subsequent imports.
   Clear/redefine the profile when the broadcast layout changes.
4. Review recognition candidates and warnings. Currently there is **no trained
   card recognition or OCR**: the manual provider returns no invented values.
5. Enter board, three assumed ranges, pot, bet and stacks. Confirm and evaluate.
   Only five-card river boards are supported by this analysis adapter. Early
   street footage can be retained as evidence but cannot yet be evaluated.
6. View check/bet EV, SE and normal-approximation 95%CI. Export CSV, reload saved
   inputs/results, or back up the entire database from the GUI.

The example button inserts synthetic research assumptions and detaches the frame
reference, so demo values are never presented as facts recognized from video.
Selecting a frame does not overwrite fields: review them before confirming.
Opponent ranges are user assumptions, not something inferred from hidden cards.
Call probabilities are P1, P2 after P1 fold, and P2 after P1 call. This is fixed-model
EV evaluation, **not a live GTO solver or equilibrium certification**.

## Architecture

`capture.sources.FrameSource -> Frame -> capture.recognition.Recognizer ->
RecognitionResult -> SQLite evidence -> human-confirmed snapshot -> StudioService
-> existing MultiwayMonteCarloEngine -> saved analysis`

`FrameSource.frames()` yields images with source and timestamp. Implement this
protocol for a future stream decoder; the current OpenCV adapter deliberately
accepts local recordings only. Do not do unbounded decoding on the Tk UI thread.
An ingest job can store a bounded batch via `OpenCVVideoSource(max_frames=...)`.
Each frame is committed independently; partial batches survive decoder failure.

`Recognizer.recognize(frame, regions)` returns provider/version, typed field
candidates, confidence in [0,1], region names, and warnings. Candidates stay
separate from confirmed game facts. Add recognition implementations without
modifying CFR or card evaluators. The current GUI shows candidates as evidence;
it does not automatically promote them into confirmed values. Future work includes
card templates/models, pot/stack OCR, confidence calibration, temporal tracking,
hand boundaries, player-seat mapping and stream reconnection/backpressure.

Regions are resolution-independent x/y/width/height values in [0,1]. Each captured
frame records the region definitions used by its recognition job. Editing a
profile does not rewrite historical recognition evidence.

## Database and provenance

Schema v1 (`PRAGMA user_version`), foreign keys enabled on every connection,
parameterized statements, explicit transactions, WAL and a 10-second busy timeout:

|Table|Purpose|
|---|---|
|sessions|Recording/research sessions and UTC creation time|
|profiles|Named normalized region definitions|
|frames|Image bytes, source, timestamp, SHA-256, recognition result and regions|
|snapshots|Immutable confirmed state JSON linked to optional frame|
|analyses|Input snapshot, seed, samples, response model, Python/source hash, ActionEV rows|

Images live in BLOBs so backups remain self-contained and source-file deletion
does not lose evidence. File imports are limited to 25 MiB; large archives will
eventually need a managed object store and retention policies. The full source
path is local provenance; database and WAL files are excluded from Git. Use the
GUI's SQLite backup API for consistent copies, rather than copying a live WAL
database file alone. Existing backups are not overwritten. A newer schema is
rejected; future migrations must be sequential and preserve these relationships.

Each worker operation uses its own connection. GUI widgets are touched only on
the main thread via a queue. Closing and switching sessions are blocked while a
worker is saving/evaluating. State validation rejects illegal cards, unsupported
streets/player counts and stacks too small for the no-side-pot game. Confirmation
and analysis are separate: if analysis fails, the confirmed input remains in
history as unevaluated.

## Validation

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv-studio/Scripts/python.exe -B -m pytest -p no:cacheprovider -q
.venv-studio/Scripts/python.exe -B -m unittest discover -s tests -q
.venv-studio/Scripts/python.exe -B scripts/smoke_studio.py
```

Tests cover persistence, backup, session isolation, invalid state handling,
recognizer separation, reproducibility, and a generated video decoded by real
OpenCV when media dependencies are installed. The GUI smoke exercise uses real
Tk widgets with a temporary database and a generated image. It needs Tk/Pillow
and a desktop session. It opens no persistent user database.
