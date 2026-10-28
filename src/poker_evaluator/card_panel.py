"""Click-only card and range editors; edits are applied only on confirmation."""
import re
import tkinter as tk
from tkinter import ttk

RANKS = 'AKQJT98765432'


def renumber(tokens):
    result, ordinal = [], 0
    for token in tokens:
        if token.upper().startswith('X'):
            ordinal += 1
            token = re.sub(r'^X\d*', f'X{ordinal}', token, flags=re.I)
        result.append(token)
    return result


class CardPanel(tk.Toplevel):
    def __init__(self, parent, entry, *, limit=7, wild=False, title='カードを選択'):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.entry, self.limit = entry, limit
        self.tokens = entry.get().split()
        self.selected = None
        self.slots = ttk.Frame(self, padding=10)
        self.slots.pack(fill='x')
        ttk.Label(self, text='空き枠へ追加します。入力済みの枠を押すと、そのカードを置換できます。').pack(padx=10)
        deck = ttk.Frame(self, padding=10)
        deck.pack()
        self.card_buttons = {}
        for row, (suit, symbol, color) in enumerate((('s','♠','#202830'),('c','♣','#202830'),('h','♥','#bc263c'),('d','♦','#bc263c'))):
            for col, rank in enumerate(RANKS):
                token = rank+suit
                button = tk.Button(deck, text=rank+symbol, width=4, foreground=color,
                                   command=lambda t=token: self.choose(t))
                button.grid(row=row, column=col, padx=2, pady=2)
                self.card_buttons[token] = button
        self.wild_buttons = {}
        if wild:
            area = ttk.LabelFrame(self, text='ワイルドカード一覧：カードを直接クリック', padding=8)
            area.pack(fill='x', padx=10)
            for col, (label, token) in enumerate((('X 無条件','X'),('X♠','Xs'),('X♣','Xc'),('X♥','Xh'),('X♦','Xd'),('XO','Xo'),('XP','Xp'),('XQ','Xq'),('XR','Xr'))):
                button = tk.Button(area, text=label, width=7 if col==0 else 4,
                                   background='#e5dcfa', command=lambda t=token:self.choose(t))
                button.grid(row=0,column=col,padx=2,pady=3)
                self.wild_buttons[token] = button
            for row, suit in enumerate('opqr', start=1):
                for col, rank in enumerate(RANKS):
                    token = rank+suit
                    button = tk.Button(area,text=rank+suit.upper(),width=4,
                                       background='#e5dcfa',command=lambda t=token:self.choose(t))
                    button.grid(row=row,column=col,padx=2,pady=2)
                    self.wild_buttons[token] = button
            ttk.Label(area,text='Xは押すたびX1、X2…になります。同じO/P/Q/Rは同じ未知スート。').grid(row=5,column=0,columnspan=13,sticky='w')
        self.note = tk.StringVar()
        ttk.Label(self, textvariable=self.note).pack(padx=10,pady=5)
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill='x')
        for label, callback in (('選択枠を削除',self.remove),('全消去',self.clear),('適用',self.apply),('キャンセル',self.destroy)):
            ttk.Button(bar,text=label,command=callback).pack(side='left',padx=4)
        self.refresh()
        self.grab_set()

    def refresh(self):
        self.tokens = renumber(self.tokens)
        for child in self.slots.winfo_children():
            child.destroy()
        for i, token in enumerate(self.tokens):
            ttk.Button(self.slots, text=f'{i+1}: {token}'+(' ◀' if self.selected==i else ''),
                       command=lambda n=i:self.select(n)).grid(row=i//7,column=i%7,padx=3,pady=3)
        ttk.Button(self.slots,text='＋ 追加',command=lambda:self.select(None)).grid(row=len(self.tokens)//7,column=len(self.tokens)%7)
        occupied = {t.upper() for i,t in enumerate(self.tokens) if i != self.selected}
        for token, button in self.card_buttons.items():
            button.configure(state='disabled' if token.upper() in occupied else 'normal')

    def select(self, index):
        self.selected = index
        self.refresh()

    def choose(self, token):
        others = [t.upper() for i,t in enumerate(self.tokens) if i != self.selected]
        if not token.upper().startswith('X') and token[-1:].lower() in 'schd' and token.upper() in others:
            self.note.set('同じ実カードは二度選べません。')
            return
        if self.selected is None:
            if len(self.tokens) >= self.limit:
                self.note.set(f'最大{self.limit}枚です。置換する枠を選んでください。')
                return
            self.tokens.append(token)
        else:
            self.tokens[self.selected] = token
        self.selected = None
        self.note.set('')
        self.refresh()

    def remove(self):
        if self.tokens:
            self.tokens.pop(self.selected if self.selected is not None else -1)
        self.selected = None
        self.refresh()

    def clear(self):
        self.tokens = []
        self.selected = None
        self.refresh()

    def apply(self):
        self.entry.delete(0,'end')
        self.entry.insert(0,' '.join(self.tokens))
        self.destroy()


class RangePanel(tk.Toplevel):
    def __init__(self, parent, value, callback):
        super().__init__(parent)
        self.title('相手レンジを選択')
        self.transient(parent.winfo_toplevel())
        self.callback = callback
        self.selected = set(value.replace(' ','').split(',')) - {''}
        ttk.Label(self,text='対角線：ペア ／ 右上：同スート(s) ／ 左下：異スート(o)').pack(padx=10,pady=8)
        grid = ttk.Frame(self,padding=8)
        grid.pack()
        self.buttons = {}
        for i,a in enumerate(RANKS):
            for j,b in enumerate(RANKS):
                token = a+a if i==j else (a+b+'s' if i<j else b+a+'o')
                button = tk.Button(grid,text=token,width=5,command=lambda t=token:self.toggle(t))
                button.grid(row=i,column=j,padx=1,pady=1)
                self.buttons[token]=button
        bar=ttk.Frame(self,padding=8)
        bar.pack()
        for label,callback in (('全ハンド(random)',self.random),('全消去',self.clear),('適用',self.apply),('キャンセル',self.destroy)):
            ttk.Button(bar,text=label,command=callback).pack(side='left',padx=3)
        self.refresh()
        self.grab_set()

    def refresh(self):
        for token,button in self.buttons.items():
            button.configure(relief='sunken' if token in self.selected or 'random' in self.selected else 'raised',
                             background='#b8dfed' if token in self.selected or 'random' in self.selected else '#f0f0f0')

    def toggle(self,token):
        if 'random' in self.selected:
            self.selected=set(self.buttons)
        if token in self.selected:
            self.selected.remove(token)
        else:
            self.selected.add(token)
        self.refresh()

    def random(self):
        self.selected={'random'}
        self.refresh()

    def clear(self):
        self.selected=set()
        self.refresh()

    def apply(self):
        self.callback(','.join(sorted(self.selected)))
        self.destroy()
