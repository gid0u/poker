"""Exercise distribution input, background computation, persistence and reload."""
import json,tempfile,time,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from poker_evaluator.gui import PokerStudio
from poker_evaluator.storage import Repository
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary

with tempfile.TemporaryDirectory() as directory:
    root=tk.Tk();root.withdraw()
    try:
        repo=Repository(Path(directory)/'studio.sqlite3');app=PokerStudio(root,repo);app.new_session()
        for key,value in [('hero','As Ah'),('board','Ts 9s 2c')]:
            app.relative_fields[key].delete(0,'end');app.relative_fields[key].insert(0,value)
        app.relative_ranges.delete('1.0','end');app.relative_ranges.insert('1.0','99+,AQs+,AKo')
        with patch('poker_evaluator.seven_card_dictionary.SevenCardRankDictionary',side_effect=lambda:SevenCardRankDictionary('C:/research/poker-evaluator/data/processed/seven_card_dictionary')):
            app.analyze_board_distribution();deadline=time.monotonic()+30
            while app.busy and time.monotonic()<deadline:
                root.update();time.sleep(.02)
        assert not app.busy and app.board_distribution_result
        assert abs(app.board_distribution_result['mean']-.7703751803751804)<1e-10
        app.save_research('board_distribution')
        assert len(repo.research_results(app.session_id()))==1
        app.board_distribution_result=None
        app.research_history();root.update()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        listing=next(w for w in dialog.winfo_children() if isinstance(w,tk.Listbox))
        listing.selection_set(0)
        button=next(w for w in dialog.winfo_children() if w.winfo_class()=='TButton')
        button.invoke()
        assert app.board_distribution_result and '中央値' in app.relative_text.get('1.0','end')
        print('GUI distribution smoke passed: calculate, save, reopen, display')
    finally:root.destroy()
