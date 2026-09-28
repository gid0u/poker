"""Desktop research studio. Launch with python -m poker_evaluator.gui."""
import argparse
import base64
import csv
import io
import json
from pathlib import Path
from queue import Queue, Empty
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .capture.models import Region
from .capture.sources import ImageFileSource, OpenCVVideoSource
from .storage import Repository
from .studio import StudioService


class PokerStudio(ttk.Frame):
    def __init__(self, root, repository):
        super().__init__(root, padding=16)
        self.root, self.repository = root, repository
        self.service = StudioService(repository)
        self.pack(fill="both", expand=True)
        self.events = Queue()
        self.busy = False
        self.frame_id = None
        self.snapshot_id = None
        self.result_rows = []
        self.regions = list(repository.regions("default"))
        self.preview = None
        self.drag_start = None
        self.status = tk.StringVar(value="セッションを選択し、画像または動画を取り込んでください。")
        root.title("Poker Research Studio")
        root.geometry("1150x800")
        root.minsize(920, 680)
        ttk.Label(self, text="Poker Research Studio", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(self, text="映像の記録 → 内容の確認 → 研究用EV評価", foreground="#546477").pack(anchor="w", pady=(2, 12))
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        self.session_choice = ttk.Combobox(top, state="readonly", width=38)
        self.session_choice.pack(side="left")
        self.session_choice.bind("<<ComboboxSelected>>", self.change_session)
        self.session_name = ttk.Entry(top, width=24)
        self.session_name.pack(side="left", padx=8)
        self.session_name.insert(0, "映像研究")
        ttk.Button(top, text="セッション作成", command=self.new_session).pack(side="left")
        ttk.Button(top, text="DBバックアップ", command=self.backup).pack(side="right")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self.input_tab, self.analysis_tab, self.history_tab = (ttk.Frame(self.tabs, padding=12) for _ in range(3))
        for title, frame in (("1  映像入力", self.input_tab), ("2  確認・評価", self.analysis_tab), ("3  保存履歴", self.history_tab)):
            self.tabs.add(frame, text=title)
        self.build_input()
        self.build_analysis()
        self.build_history()
        ttk.Label(self, textvariable=self.status, wraplength=1050).pack(fill="x", pady=(10, 0))
        ttk.Label(self, text=f"保存先: {repository.path}", foreground="#667788").pack(anchor="w")
        self.refresh_sessions()
        self.after(100, self.poll)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def build_input(self):
        toolbar = ttk.Frame(self.input_tab)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="画像を取り込む", command=self.import_image).pack(side="left")
        ttk.Label(toolbar, text="動画の時刻（秒）").pack(side="left", padx=(20, 4))
        self.video_seconds = ttk.Entry(toolbar, width=9)
        self.video_seconds.insert(0, "0")
        self.video_seconds.pack(side="left")
        ttk.Button(toolbar, text="動画から1枚取得", command=self.import_video).pack(side="left", padx=8)
        ttk.Label(self.input_tab, text="録画ファイル・配信映像のスクリーンショットを保存。自動認識は未接続です。内容は次のタブで確認します。").pack(anchor="w", pady=8)
        content = ttk.Frame(self.input_tab)
        content.pack(fill="both", expand=True)
        self.frame_list = tk.Listbox(content, width=30, exportselection=False)
        self.frame_list.pack(side="left", fill="y", padx=(0, 10))
        self.frame_list.bind("<<ListboxSelect>>", self.select_frame)
        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(right, background="#152334", height=340, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.start_region)
        self.canvas.bind("<B1-Motion>", self.drag_region)
        self.canvas.bind("<ButtonRelease-1>", self.finish_region)
        regions = ttk.Frame(right)
        regions.pack(fill="x", pady=8)
        ttk.Label(regions, text="読取領域").pack(side="left")
        self.region_name = ttk.Combobox(regions, values=("board", "pot", "seat_0", "seat_1", "seat_2"), width=15)
        self.region_name.set("board")
        self.region_name.pack(side="left", padx=8)
        ttk.Label(regions, text="画像をドラッグして指定・保存").pack(side="left")
        ttk.Button(regions, text="領域を全消去", command=self.clear_regions).pack(side="right")
        self.region_label = ttk.Label(right, text=self.region_summary(), wraplength=720)
        self.region_label.pack(anchor="w")
        self.evidence = tk.Text(right, height=5, wrap="word", state="disabled")
        self.evidence.pack(fill="x", pady=(8, 0))

    def build_analysis(self):
        ttk.Label(self.analysis_tab, text="3人・固定リバー専用。画像内に見えない相手レンジは研究上の仮定として入力してください。", wraplength=1000).pack(anchor="w")
        form = ttk.Frame(self.analysis_tab)
        form.pack(fill="x", pady=12)
        self.fields = {}
        definitions = (("board", "ボード（例: Ks 8h 7d 3c 2s）"), ("pot", "現在のポット"),
                       ("bet", "ベット額"), ("stacks", "3人の残スタック（空白区切り）"),
                       ("p0", "P0 レンジ"), ("p1", "P1 レンジ"), ("p2", "P2 レンジ"),
                       ("calls", "コール確率 P1 / P2対fold / P2対call"), ("samples", "サンプル数"), ("seed", "乱数seed"))
        for i, (name, label) in enumerate(definitions):
            col, row = (i // 5) * 2, i % 5
            ttk.Label(form, text=label).grid(row=row, column=col, sticky="w", pady=6, padx=(0, 12))
            entry = ttk.Entry(form, width=28)
            entry.grid(row=row, column=col+1, sticky="ew", padx=(0, 20))
            self.fields[name] = entry
        for name, value in (("calls", "0.5 0.5 0.5"), ("samples", "10000"), ("seed", "42")):
            self.fields[name].insert(0, value)
        bar = ttk.Frame(self.analysis_tab)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="研究用の入力例を入れる", command=self.example).pack(side="left")
        ttk.Button(bar, text="確認済みとして保存・EV評価", command=self.analyze).pack(side="left", padx=12)
        ttk.Button(bar, text="結果CSVを保存", command=self.export_csv).pack(side="right")
        self.results = self.make_table(self.analysis_tab, ("action", "EV", "SE", "95% CI"), height=6)
        ttk.Label(self.analysis_tab, text="固定した相手応答モデルに対するEVです。GTO推奨ではありません。95%CIはサンプリング誤差のみを示します。", wraplength=1000).pack(anchor="w", pady=10)

    def build_history(self):
        ttk.Button(self.history_tab, text="履歴を更新", command=self.refresh_history).pack(anchor="w", pady=(0, 8))
        self.history_table = self.make_table(self.history_tab, ("保存時刻", "画像", "評価"), height=15)
        self.history_table.bind("<<TreeviewSelect>>", self.load_history)

    @staticmethod
    def make_table(parent, columns, height):
        table = ttk.Treeview(parent, columns=columns, show="headings", height=height)
        for name in columns:
            table.heading(name, text=name)
            table.column(name, width=200, anchor="w")
        table.pack(fill="both", expand=True)
        return table

    def session_id(self):
        index = self.session_choice.current()
        if index < 0:
            raise ValueError("セッションを作成してください")
        return self.session_rows[index]["id"]

    def guard(self):
        if self.busy:
            self.status.set("処理中です。完了までお待ちください。")
            return False
        return True

    def run(self, task, done):
        if not self.guard():
            return
        self.busy = True
        self.session_choice.configure(state="disabled")
        self.status.set("処理中…")
        def work():
            try:
                self.events.put((done, task(), None))
            except Exception as exc:
                self.events.put((done, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            done, result, error = self.events.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            self.session_choice.configure(state="readonly")
            if error:
                self.status.set(f"処理できませんでした: {error}")
                messagebox.showerror("入力・処理エラー", error, parent=self.root)
            else:
                try:
                    done(result)
                except Exception as exc:
                    self.status.set(str(exc))
                    messagebox.showerror("表示エラー", str(exc), parent=self.root)
        self.after(100, self.poll)

    def new_session(self):
        if not self.guard():
            return
        try:
            self.repository.create_session(self.session_name.get())
            self.refresh_sessions()
        except ValueError as exc:
            messagebox.showerror("セッション", str(exc))

    def refresh_sessions(self):
        self.session_rows = self.repository.sessions()
        self.session_choice["values"] = [f"{s['name']}  [{s['id'][:8]}]" for s in self.session_rows]
        if self.session_rows:
            self.session_choice.current(0)
        self.change_session()

    def change_session(self, event=None):
        self.frame_id = self.snapshot_id = None
        self.result_rows = []
        self.preview = None
        self.canvas.delete("all")
        self.results.delete(*self.results.get_children())
        self.set_evidence("")
        for key in ("board", "pot", "bet", "stacks", "p0", "p1", "p2"):
            self.fields[key].delete(0, "end")
        self.refresh_frames()
        self.refresh_history()

    def refresh_frames(self):
        self.frame_list.delete(0, "end")
        self.frame_rows = self.repository.frames(self.session_id()) if self.session_rows else []
        for row in self.frame_rows:
            self.frame_list.insert("end", f"{Path(row['source']).name}  {row['timestamp_ms']/1000:.2f}s")

    def import_image(self):
        self.import_media(False)

    def import_video(self):
        self.import_media(True)

    def import_media(self, video):
        if not self.guard():
            return
        try:
            session = self.session_id()
            timestamp = round(float(self.video_seconds.get()) * 1000) if video else 0
            path = filedialog.askopenfilename(filetypes=[("動画", "*.mp4 *.mkv *.avi *.mov")] if video else [("画像", "*.png *.jpg *.jpeg")])
            if not path:
                return
            source = OpenCVVideoSource(path, start_ms=timestamp) if video else ImageFileSource(path)
            regions = tuple(self.regions)
            self.run(lambda: self.service.ingest(session, source, regions), self.imported)
        except (ValueError, OverflowError) as exc:
            messagebox.showerror("入力", str(exc))

    def imported(self, identifiers):
        self.refresh_frames()
        self.frame_list.selection_set(0)
        self.select_frame()
        self.status.set("フレームを保存しました。「確認・評価」で内容を入力してください。")

    def select_frame(self, event=None):
        if self.busy or not self.frame_list.curselection():
            return
        row = self.frame_rows[self.frame_list.curselection()[0]]
        self.frame_id = row["id"]
        self.show_frame(self.repository.frame(self.frame_id))
        self.status.set("表示フレームを選択しました。入力欄は自動更新されません。内容を見直してください。")

    def set_evidence(self, text):
        self.evidence.configure(state="normal")
        self.evidence.delete("1.0", "end")
        self.evidence.insert("end", text)
        self.evidence.configure(state="disabled")

    def show_frame(self, frame):
        self.canvas.delete("all")
        self.preview = None
        data = frame["content"]
        try:
            from PIL import Image, ImageTk
            pixels = Image.open(io.BytesIO(data))
            pixels.thumbnail((740, 360))
            self.preview = ImageTk.PhotoImage(pixels, master=self.root)
        except ImportError:
            try:
                original = tk.PhotoImage(data=base64.b64encode(data), master=self.root)
                scale = max(1, (original.width()+739)//740, (original.height()+359)//360)
                self.preview = original.subsample(scale)
            except tk.TclError:
                self.canvas.create_text(25, 30, anchor="nw", fill="white", text="プレビューできません。PNG画像をご利用ください。\nJPEG表示には Pillow を追加してください。")
        except Exception as exc:
            self.canvas.create_text(25, 30, anchor="nw", fill="white", text=f"画像を読み取れません: {exc}")
        if self.preview:
            self.canvas.create_image(0, 0, anchor="nw", image=self.preview)
            self.draw_regions()
        evidence = json.loads(frame["recognition_json"])
        messages = list(evidence.get("warnings", []))
        for candidate in evidence.get("candidates", []):
            messages.append(f"候補 {candidate['field']}: {candidate['value']}（信頼度 {candidate['confidence']:.0%}）")
        self.set_evidence("\n".join(messages))

    def region_summary(self):
        return "保存済み領域: " + (", ".join(r.name for r in self.regions) or "なし")

    def draw_regions(self):
        self.canvas.delete("region")
        if not self.preview:
            return
        w, h = self.preview.width(), self.preview.height()
        for region in self.regions:
            self.canvas.create_rectangle(region.x*w, region.y*h, (region.x+region.width)*w,
                                         (region.y+region.height)*h, outline="#50dfbc", width=2, tags="region")
            self.canvas.create_text(region.x*w+3, region.y*h+3, text=region.name,
                                    anchor="nw", fill="#50dfbc", tags="region")

    def start_region(self, event):
        if self.preview and not self.busy:
            self.drag_start = (max(0, min(event.x, self.preview.width())), max(0, min(event.y, self.preview.height())))

    def drag_region(self, event):
        if self.drag_start:
            self.canvas.delete("drag")
            self.canvas.create_rectangle(*self.drag_start, event.x, event.y, outline="#ffc65c", tags="drag")

    def finish_region(self, event):
        if not self.drag_start or not self.preview:
            return
        start = self.drag_start
        self.drag_start = None
        self.canvas.delete("drag")
        w, h = self.preview.width(), self.preview.height()
        x1, x2 = sorted((start[0], max(0, min(event.x, w))))
        y1, y2 = sorted((start[1], max(0, min(event.y, h))))
        if x2-x1 < 4 or y2-y1 < 4:
            return
        try:
            region = Region(self.region_name.get().strip(), x1/w, y1/h, (x2-x1)/w, (y2-y1)/h)
            self.regions = [r for r in self.regions if r.name != region.name] + [region]
            self.repository.save_regions("default", self.regions)
            self.region_label.configure(text=self.region_summary())
            self.draw_regions()
            self.status.set("読取領域を保存しました。次の取込みから認識モジュールへ渡されます。")
        except ValueError as exc:
            messagebox.showerror("領域", str(exc))

    def clear_regions(self):
        if not self.guard():
            return
        self.regions = []
        self.repository.save_regions("default", ())
        self.region_label.configure(text=self.region_summary())
        self.draw_regions()

    def example(self):
        if not self.guard():
            return
        # Example inputs are deliberately detached from imported video evidence.
        self.frame_id = None
        values = dict(board="Ks 8h 7d 3c 2s", pot="100", bet="50", stacks="100 100 100",
                      p0="AA,QQ", p1="KK,JJ", p2="88,TT", calls="0.5 0.5 0.5", samples="10000", seed="42")
        for name, value in values.items():
            self.fields[name].delete(0, "end")
            self.fields[name].insert(0, value)
        self.status.set("研究用の入力例です。映像から読み取った値ではありません。")

    def analyze(self):
        if not self.guard():
            return
        try:
            session = self.session_id()
            values = {k: e.get().strip() for k, e in self.fields.items()}
            state = dict(board=values["board"].split(), pot=float(values["pot"]), bet=float(values["bet"]),
                         stacks=[float(s) for s in values["stacks"].split()],
                         ranges=[values[p] for p in ("p0", "p1", "p2")])
            calls = tuple(float(x) for x in values["calls"].split())
            if len(calls) != 3:
                raise ValueError("コール確率は3個指定してください")
            samples, seed, frame = int(values["samples"]), int(values["seed"]), self.frame_id
            def task():
                snapshot = self.service.confirm(session, state, frame)
                identifier, rows = self.service.analyze(snapshot, samples=samples, seed=seed, calls=calls)
                return snapshot, rows
            self.run(task, self.analyzed)
        except (ValueError, OverflowError) as exc:
            messagebox.showerror("入力", str(exc))

    def analyzed(self, result):
        self.snapshot_id, self.result_rows = result
        self.render_results()
        self.refresh_history()
        self.status.set("確認済み入力と評価結果を保存しました。")

    def render_results(self):
        self.results.delete(*self.results.get_children())
        for row in self.result_rows:
            self.results.insert("", "end", values=(row["action"], f"{row['ev_chips']:.4f}",
                                f"{row['standard_error']:.4f}", f"[{row['ci95_low']:.4f}, {row['ci95_high']:.4f}]"))

    def refresh_history(self):
        if self.busy:
            return
        self.history_table.delete(*self.history_table.get_children())
        self.history_rows = self.repository.history(self.session_id()) if self.session_rows else []
        for i, row in enumerate(self.history_rows):
            self.history_table.insert("", "end", iid=str(i), values=(row["confirmed_at"],
                                      "あり" if row["frame_id"] else "手動", "完了" if row["analysis_id"] else "未評価"))

    def load_history(self, event=None):
        if self.busy or not self.history_table.selection():
            return
        row = self.history_rows[int(self.history_table.selection()[0])]
        state = self.repository.snapshot(row["id"])["state"]
        values = dict(board=" ".join(state["board"]), pot=str(state["pot"]), bet=str(state["bet"]),
                      stacks=" ".join(map(str, state["stacks"])), **dict(zip(("p0", "p1", "p2"), state["ranges"])))
        if row["config_json"]:
            config = json.loads(row["config_json"])
            values.update(samples=str(config["samples"]), seed=str(config["seed"]),
                          calls=" ".join(map(str, config["call_probabilities"])))
        for name, value in values.items():
            self.fields[name].delete(0, "end")
            self.fields[name].insert(0, value)
        self.snapshot_id, self.frame_id = row["id"], row["frame_id"]
        if self.frame_id:
            self.show_frame(self.repository.frame(self.frame_id))
        else:
            self.preview = None
            self.canvas.delete("all")
            self.set_evidence("")
        self.result_rows = json.loads(row["result_json"]) if row["result_json"] else []
        self.render_results()
        self.tabs.select(self.analysis_tab)
        self.status.set("保存した入力・評価を読み込みました。再評価時は新しい履歴として保存します。")

    def export_csv(self):
        if not self.result_rows:
            messagebox.showinfo("CSV", "評価結果がありません")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            try:
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(self.result_rows[0]))
                    writer.writeheader()
                    writer.writerows(self.result_rows)
                self.status.set("CSVを保存しました。")
            except OSError as exc:
                messagebox.showerror("保存", str(exc))

    def backup(self):
        if not self.guard():
            return
        path = filedialog.asksaveasfilename(defaultextension=".sqlite3", filetypes=[("SQLite", "*.sqlite3")])
        if path:
            self.run(lambda: self.repository.backup(path), lambda _: self.status.set("DBバックアップを保存しました。"))

    def close(self):
        if self.busy:
            self.status.set("保存・計算が完了してから閉じてください。")
            return
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Poker Research Studio")
    parser.add_argument("--db", type=Path, default=Path("data/local/poker_studio.sqlite3"))
    args = parser.parse_args()
    repository = Repository(args.db)
    root = tk.Tk()
    PokerStudio(root, repository)
    root.mainloop()


if __name__ == "__main__":
    main()
