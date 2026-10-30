"""Regression smoke: displayed inputs, failed runs and opponent panel safety."""
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from poker_evaluator.gui import PokerStudio
from poker_evaluator.storage import Repository
from poker_evaluator.relative_strength import evaluate_relative_strength
from poker_evaluator.card_panel import RangePanel

with tempfile.TemporaryDirectory() as directory:
    root=tk.Tk()
    root.withdraw()
    try:
        app=PokerStudio(root,Repository(Path(directory)/'studio.sqlite3'))
        result=evaluate_relative_strength('As Ah','Ks 8h 7d 3c 2s',['KK,QQ'],mode='exact')
        app.relative_done(result)
        assert 'As Ah' in app.relative_text.get('1.0','end')
        app.relative_fields['samples'].delete(0,'end')
        app.relative_fields['samples'].insert(0,'invalid')
        with patch('poker_evaluator.gui.messagebox.showerror') as error:
            app.analyze_relative()
            assert error.called and app.relative_result is None
            assert not app.relative_text.get('1.0','end').strip()
        app.wildcard_result={'old':True}
        app.wildcard_entry.delete(0,'end')
        app.wildcard_entry.insert(0,'invalid')
        with patch('poker_evaluator.gui.messagebox.showerror') as error:
            app.analyze_wildcards()
            assert error.called and app.wildcard_result is None
        before=app.relative_ranges.get('1.0','end')
        app.opponent_number.set('4')
        with patch('poker_evaluator.gui.messagebox.showerror') as error:
            app.relative_range_panel()
            assert error.called
        assert app.relative_ranges.get('1.0','end')==before
        panel=RangePanel(root,'AK,QQ+',lambda value:None)
        assert all(panel.buttons[t].cget('relief')=='sunken' for t in ('AKs','AKo','QQ','KK','AA'))
        panel.buttons['AKs'].invoke()
        assert 'AKs' not in panel.selected and 'AKo' in panel.selected
        panel.destroy()
        print('GUI audit smoke passed: range normalization, no phantom opponents, input provenance, no old export after failure')
    finally:
        root.destroy()
