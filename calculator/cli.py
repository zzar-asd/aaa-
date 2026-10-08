"""科学计算器：终端交互界面（无第三方依赖）。

用法：
    python calculator/cli.py            # 交互式 REPL
    python calculator/cli.py -e "1+2*3" # 单次计算

REPL 命令：
    help / ?        查看帮助
    history         查看历史记录
    clear           清空屏幕与输入
    ans             上一次结果（也可直接在表达式中使用 ans）
    quit / exit / q 退出（Ctrl-D 同样可退出）
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator.engine import CalcError, calculate  # noqa: E402

BANNER = """╔══════════════════════════════════════╗
║      科学计算器 Scientific Calc      ║
║   输入表达式回车计算，help 看帮助    ║
║   quit 退出                          ║
╚══════════════════════════════════════╝"""

HELP_TEXT = """支持语法：
  四则运算     + - * / // ** （^ 亦可，如 2^10）
  括号/隐式乘法 (1+2)*3 、 2(3+4) 、 2pi
  百分号后缀   50% -> 0.5 ， 200+10%*200 -> 220
  阶乘后缀     5! -> 120
  常数         pi e tau phi
  函数         sqrt/√ abs round floor ceil sin cos tan asin acos atan
               log(以10为底, 可带底数 log(8,2)) ln exp factorial
  上次结果     ans （如 ans*2）
REPL 命令：history 历史 | clear 清屏 | help 帮助 | quit 退出"""


def repl() -> int:
    print(BANNER)
    history: list[tuple[str, str]] = []  # (表达式, 结果或错误)
    last_ans: str | None = None

    while True:
        try:
            line = input("calc> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        low = line.lower()
        if low in ("quit", "exit", "q"):
            break
        if low in ("help", "?"):
            print(HELP_TEXT)
            continue
        if low == "history":
            if not history:
                print("(暂无记录)")
            for i, (expr, res) in enumerate(history[-20:], start=max(1, len(history) - 19)):
                print(f"{i:>3}. {expr} = {res}")
            continue
        if low == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        # 允许使用 ans 引用上一次结果
        expr = line
        if "ans" in expr.replace("factorial", ""):
            if last_ans is None:
                print("尚无上次结果 (ans)。")
                continue
            import re as _re
            expr = _re.sub(r"\bans\b", f"({last_ans.replace(',', '')})", expr)
        try:
            result = calculate(expr)
            print(f"     = {result}")
            history.append((line, result))
            last_ans = result
        except CalcError as exc:
            print(f"  错误：{exc}")
            history.append((line, f"错误：{exc}"))
    print("再见！")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="科学计算器")
    parser.add_argument("-e", "--expr", help="直接计算一个表达式并退出")
    args = parser.parse_args(argv)
    if args.expr:
        try:
            print(calculate(args.expr))
            return 0
        except CalcError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
    return repl()


if __name__ == "__main__":
    raise SystemExit(main())
