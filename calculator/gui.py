"""科学计算器：Tkinter 图形界面。

用法：python calculator/gui.py

特性：
- 类 Windows 计算器布局：MC MR M+ M- MS | ← C CE ÷ | 7 8 9 × | 4 5 6 −
  | 1 2 3 + | ± 0 . =，另加科学函数行：( ) % √ ^ !
- 表达式实时求值预览（输入即显示结果）
- 键盘支持：数字、运算符、回车=、退格=←、Esc=CE、Del=C、%、()、^、!
- 内存功能 MC/MR/M+/M-/MS
- 历史记录面板（最近 50 条），点击可复用
- 深色主题，按钮悬停/按下反馈
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import font as tkfont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator.engine import CalcError, calculate  # noqa: E402

# ----------------------------- 主题配色 -----------------------------
BG = "#202124"
PANEL = "#2b2d31"
DISPLAY_BG = "#202124"
EXPR_FG = "#9aa0a6"
RESULT_FG = "#ffffff"
NUM_BG = "#3c4043"
NUM_HOVER = "#4a4e51"
OP_BG = "#333639"
OP_HOVER = "#45484c"
FN_BG = "#2b2d31"
FN_HOVER = "#3a3d40"
EQ_BG = "#8ab4f8"
EQ_FG = "#17181c"
MEM_FG = "#8ab4f8"
ERR_FG = "#f28b82"
BTN_FG = "#e8eaed"


class CalculatorGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("科学计算器")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("380x580")

        self.expr = ""            # 当前表达式
        self.memory = 0.0         # 内存值
        self.just_evaluated = False
        self.history: list[tuple[str, str]] = []

        self._build_fonts()
        self._build_display()
        self._build_buttons()
        self._build_history()
        self._bind_keys()
        self._update_display()

    # ---------------------------- 字体 ----------------------------
    def _build_fonts(self) -> None:
        base = "Segoe UI" if sys.platform == "win32" else "Helvetica"
        self.f_expr = tkfont.Font(family=base, size=14)
        self.f_result = tkfont.Font(family=base, size=30, weight="bold")
        self.f_btn = tkfont.Font(family=base, size=13)
        self.f_btn_small = tkfont.Font(family=base, size=11)
        self.f_hist = tkfont.Font(family=base, size=10)

    # ---------------------------- 显示屏 ----------------------------
    def _build_display(self) -> None:
        frame = tk.Frame(self, bg=DISPLAY_BG)
        frame.pack(fill="x", padx=8, pady=(8, 4))
        self.lbl_expr = tk.Label(frame, text="", anchor="e", bg=DISPLAY_BG,
                                 fg=EXPR_FG, font=self.f_expr, height=1)
        self.lbl_expr.pack(fill="x")
        self.lbl_result = tk.Label(frame, text="0", anchor="e", bg=DISPLAY_BG,
                                   fg=RESULT_FG, font=self.f_result)
        self.lbl_result.pack(fill="x")

    # ---------------------------- 按钮区 ----------------------------
    def _make_btn(self, parent, text, command, *, kind="num", colspan=1, small=False):
        bg, hover = {"num": (NUM_BG, NUM_HOVER),
                     "op": (OP_BG, OP_HOVER),
                     "fn": (FN_BG, FN_HOVER),
                     "eq": (EQ_BG, EQ_BG)}[kind]
        fg = EQ_FG if kind == "eq" else BTN_FG
        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                        relief="flat", bd=0, highlightthickness=0,
                        font=self.f_btn_small if small else self.f_btn,
                        cursor="hand2")
        btn.grid(sticky="nsew", columnspan=colspan)
        if kind != "eq":
            btn.bind("<Enter>", lambda e, b=btn, c=hover: b.config(bg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=bg: b.config(bg=c))
        return btn

    def _build_buttons(self) -> None:
        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=8, pady=4)
        rows, cols = 8, 4
        for r in range(rows):
            grid.rowconfigure(r, weight=1, uniform="row")
        for c in range(cols):
            grid.columnconfigure(c, weight=1, uniform="col")
        grid.columnconfigure(0, minsize=80)

        # 第0行：内存
        mem_cmds = [("MC", self.mem_clear), ("MR", self.mem_recall),
                    ("M+", self.mem_add), ("M-", self.mem_sub), ("MS", self.mem_store)]
        span = cols / len(mem_cmds)
        for i, (label, cmd) in enumerate(mem_cmds):
            b = self._make_btn(grid, label, cmd, kind="fn", small=True)
            b.grid(row=0, column=int(i * span) if i < 4 else 3, sticky="nsew")
        # 简化：均分 5 个按钮到 4 列 -> 改为放在一个子 frame
        for w in grid.grid_slaves(row=0):
            w.destroy()
        membar = tk.Frame(grid, bg=BG)
        membar.grid(row=0, column=0, columnspan=cols, sticky="nsew")
        for i in range(len(mem_cmds)):
            membar.columnconfigure(i, weight=1)
            label, cmd = mem_cmds[i]
            b = tk.Button(membar, text=label, command=cmd, bg=FN_BG, fg=MEM_FG,
                          activebackground=FN_HOVER, relief="flat", bd=0,
                          highlightthickness=0, font=self.f_btn_small, cursor="hand2")
            b.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)

        # 第1行：科学函数
        sci = [("( ", lambda: self.append("(")),
               (" )", lambda: self.append(")")),
               (" %", lambda: self.append("%")),
               (" ←", self.backspace)]
        for i, (label, cmd) in enumerate(sci):
            self._make_btn(grid, label, cmd, kind="fn")
            grid.grid_slaves(row=1, column=i)[0].grid_configure(padx=2, pady=2)

        sci2 = [("√", lambda: self.append("sqrt(")),
                ("^", lambda: self.append("^")),
                ("!", lambda: self.append("!")),
                ("log", lambda: self.append("log("))]
        for i, (label, cmd) in enumerate(sci2):
            self._make_btn(grid, label, cmd, kind="fn")
            grid.grid_slaves(row=2, column=i)[0].grid_configure(padx=2, pady=2)

        # 主键盘区（行 3..7）
        keys = [
            [("C", self.clear_all, "fn"), ("CE", self.clear_entry, "fn"),
             ("÷", lambda: self.append_op("/"), "op"), ("×", lambda: self.append_op("*"), "op")],
            [("7", lambda: self.append("7"), "num"), ("8", lambda: self.append("8"), "num"),
             ("9", lambda: self.append("9"), "num"), ("−", lambda: self.append_op("-"), "op")],
            [("4", lambda: self.append("4"), "num"), ("5", lambda: self.append("5"), "num"),
             ("6", lambda: self.append("6"), "num"), ("+", lambda: self.append_op("+"), "op")],
            [("1", lambda: self.append("1"), "num"), ("2", lambda: self.append("2"), "num"),
             ("3", lambda: self.append("3"), "num"),
             ("±", self.negate, "fn")],
            [("0", lambda: self.append("0"), "num"), (".", lambda: self.append("."), "num"),
             ("ANS", self.recall_ans, "fn"), ("=", self.evaluate, "eq")],
        ]
        for r, rowkeys in enumerate(keys):
            for c, (label, cmd, kind) in enumerate(rowkeys):
                self._make_btn(grid, label, cmd, kind=kind)
                grid.grid_slaves(row=3 + r, column=c)[0].grid_configure(padx=2, pady=2)

    # ---------------------------- 历史面板 ----------------------------
    def _build_history(self) -> None:
        self.hist_frame = tk.Frame(self, bg=PANEL)
        self.hist_canvas = tk.Canvas(self.hist_frame, bg=PANEL, highlightthickness=0,
                                     width=360, height=200)
        sb = tk.Scrollbar(self.hist_frame, orient="vertical",
                          command=self.hist_canvas.yview)
        self.hist_inner = tk.Frame(self.hist_canvas, bg=PANEL)
        self.hist_inner.bind("<Configure>",
                             lambda e: self.hist_canvas.configure(scrollregion=self.hist_canvas.bbox("all")))
        self.hist_canvas.create_window((0, 0), window=self.hist_inner, anchor="nw")
        self.hist_canvas.configure(yscrollcommand=sb.set)
        self.hist_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        toggle = tk.Button(self, text="🕘 历史记录", command=self.toggle_history,
                           bg=BG, fg=EXPR_FG, relief="flat", bd=0,
                           activebackground=BG, activeforeground=BTN_FG,
                           font=self.f_btn_small, cursor="hand2")
        toggle.pack(anchor="w", padx=12, pady=(0, 6))
        self.hist_visible = False

    def toggle_history(self) -> None:
        if self.hist_visible:
            self.hist_frame.pack_forget()
        else:
            self.hist_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.hist_visible = not self.hist_visible

    def _add_history(self, expr: str, result: str) -> None:
        self.history.append((expr, result))
        row = tk.Button(self.hist_inner, text=f"{expr} = {result}",
                        bg=PANEL, fg=BTN_FG, relief="flat", bd=0, anchor="e",
                        activebackground=FN_HOVER, font=self.f_hist, cursor="hand2",
                        command=lambda e=expr: self._reuse(e))
        row.pack(fill="x", padx=4, pady=1)
        self.hist_canvas.update_idletasks()
        self.hist_canvas.yview_moveto(1.0)

    def _reuse(self, expr: str) -> None:
        self.expr = expr
        self.just_evaluated = False
        self._update_display()

    # ---------------------------- 输入逻辑 ----------------------------
    def append(self, s: str) -> None:
        if self.just_evaluated:
            if s.isdigit() or s in (".", "(") or s in ("sqrt(", "log("):
                self.expr = ""
            self.just_evaluated = False
        self.expr += s
        self._update_display()

    def append_op(self, op: str) -> None:
        if self.just_evaluated:
            self.just_evaluated = False
        if not self.expr and op != "-":
            self.expr = "0"
        # 替换末尾运算符
        while self.expr and self.expr[-1] in "+-*/^":
            self.expr = self.expr[:-1]
        self.expr += op
        self._update_display()

    def backspace(self) -> None:
        self.expr = self.expr[:-1]
        self.just_evaluated = False
        self._update_display()

    def clear_entry(self) -> None:
        self.expr = ""
        self.just_evaluated = False
        self._update_display()

    def clear_all(self) -> None:
        self.expr = ""
        self.just_evaluated = False
        self._update_display(reset_result=True)

    def negate(self) -> None:
        """对当前输入的最后一个数字取反。"""
        i = len(self.expr)
        j = i
        while j > 0 and (self.expr[j - 1].isdigit() or self.expr[j - 1] == "."):
            j -= 1
        if j == i:
            return
        num = self.expr[j:i]
        if j >= 2 and self.expr[j - 2] == "(" and self.expr[j - 1] == "-":
            # 已是负数 -> 去掉负号
            self.expr = self.expr[:j - 2] + num
        elif j >= 1 and self.expr[j - 1] == "-" and (j == 1 or self.expr[j - 2] in "+-*/^("):
            self.expr = self.expr[:j - 1] + num
        else:
            self.expr = self.expr[:j] + f"(-{num})"
        self._update_display()

    def recall_ans(self) -> None:
        if self.history:
            self.append(self.history[-1][1].replace(",", ""))

    # ---------------------------- 计算 ----------------------------
    def evaluate(self) -> None:
        expr = self.expr.strip()
        if not expr:
            return
        try:
            result = calculate(expr)
        except CalcError as exc:
            self.lbl_result.config(text=str(exc), fg=ERR_FG)
            self._add_history(expr, f"错误：{exc}")
            return
        self.lbl_result.config(text=result, fg=RESULT_FG)
        self.lbl_expr.config(text=expr + " =")
        self._add_history(expr, result)
        self.expr = result.replace(",", "")
        self.just_evaluated = True

    def _live_preview(self) -> None:
        if not self.expr:
            self.lbl_result.config(text="0", fg=RESULT_FG)
            return
        try:
            preview = calculate(self.expr)
            self.lbl_result.config(text=preview, fg=RESULT_FG)
        except CalcError:
            pass  # 保留上一次结果

    def _update_display(self, reset_result: bool = False) -> None:
        self.lbl_expr.config(text=self.expr if self.expr else " ")
        if reset_result:
            self.lbl_result.config(text="0", fg=RESULT_FG)
        else:
            self._live_preview()

    # ---------------------------- 内存 ----------------------------
    def _current_value(self) -> float | None:
        try:
            return float(calculate(self.expr).replace(",", "")) if self.expr else None
        except CalcError:
            return None

    def mem_store(self) -> None:
        v = self._current_value()
        if v is not None:
            self.memory = v

    def mem_recall(self) -> None:
        self.append(repr(self.memory))

    def mem_add(self) -> None:
        v = self._current_value()
        if v is not None:
            self.memory += v

    def mem_sub(self) -> None:
        v = self._current_value()
        if v is not None:
            self.memory -= v

    def mem_clear(self) -> None:
        self.memory = 0.0

    # ---------------------------- 键盘绑定 ----------------------------
    def _bind_keys(self) -> None:
        table = {
            "Return": lambda: self.evaluate(),
            "KP_Enter": lambda: self.evaluate(),
            "BackSpace": lambda: self.backspace(),
            "Escape": lambda: self.clear_entry(),
            "Delete": lambda: self.clear_all(),
        }
        for ch in "0123456789.()!%^":
            table[ch] = (lambda c: (lambda e: self.append(c)))(ch)
        for ch in "+-*/":
            table[ch] = (lambda c: (lambda e: self.append_op(c)))(ch)
        for key, fn in table.items():
            self.bind(key, fn)
        self.bind("%", lambda e: self.append("%"))


def main() -> int:
    app = CalculatorGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
