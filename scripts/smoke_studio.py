"""Exercise actual Tk widgets + background evaluation against a disposable DB."""
from pathlib import Path
import tempfile
import time
import tkinter as tk
from PIL import Image

from poker_evaluator.capture.sources import ImageFileSource
from poker_evaluator.gui import PokerStudio
from poker_evaluator.storage import Repository


def run():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        root = tk.Tk()
        root.withdraw()
        try:
            app = PokerStudio(root, Repository(path / "studio.sqlite3"))
            app.new_session()
            image = path / "sample.png"
            Image.new("RGB", (640, 360), "#223344").save(image)
            identifiers = app.service.ingest(app.session_id(), ImageFileSource(image))
            app.imported(identifiers)
            assert app.preview and app.frame_id
            app.example()
            assert app.frame_id is None
            app.fields["samples"].delete(0, "end")
            app.fields["samples"].insert(0, "200")
            app.analyze()
            deadline = time.monotonic() + 20
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(.02)
            assert not app.busy, "Worker timeout"
            assert len(app.result_rows) == 2
            assert len(app.history_rows) == 1
            app.history_table.selection_set("0")
            app.load_history()
            assert app.fields["board"].get() == "Ks 8h 7d 3c 2s"
            assert len(app.results.get_children()) == 2
            app.change_session()
            assert not app.fields["board"].get()
            assert not app.result_rows
            print("GUI smoke passed: image preview, session, review, background EV, history reload")
        finally:
            root.destroy()


if __name__ == "__main__":
    run()
