"""Exercise click editors with real Tk widgets and no persistent user data."""
import tkinter as tk
from poker_evaluator.card_panel import CardPanel, RangePanel

root=tk.Tk()
root.withdraw()
try:
    entry=tk.Entry(root)
    panel=CardPanel(root,entry,wild=True)
    panel.card_buttons['As'].invoke()
    panel.card_buttons['As'].invoke()
    assert panel.tokens==['As']
    panel.rank.set('X'); panel.suit.set(''); panel.choose_wild()
    panel.suit.set('s'); panel.choose_wild()
    assert panel.tokens==['As','X1','X2s']
    panel.select(1); panel.remove()
    assert panel.tokens==['As','X1s']
    panel.rank.set('Q'); panel.suit.set('o'); panel.choose_wild()
    panel.apply()
    assert entry.get()=='As X1s Qo'
    panel=CardPanel(root,entry,wild=True)
    panel.clear(); panel.destroy()
    assert entry.get()=='As X1s Qo', 'Cancel must preserve original'
    entry.delete(0,'end')
    panel=CardPanel(root,entry,limit=2)
    for token in ('As','Ah','Ks'): panel.choose(token)
    assert panel.tokens==['As','Ah']
    panel.select(0); panel.choose('Ks'); panel.apply()
    assert entry.get()=='Ks Ah'
    result=[]
    panel=RangePanel(root,'KK',result.append)
    panel.buttons['QQ'].invoke(); panel.apply()
    assert result==['KK,QQ']
    panel=RangePanel(root,'random',result.append)
    panel.buttons['AA'].invoke()
    assert len(panel.selected)==168 and 'AA' not in panel.selected
    panel.destroy()
    print('Card panel smoke passed: clicks, duplicates, limits, replace, delete, numbering, cancel, ranges')
finally:
    root.destroy()
