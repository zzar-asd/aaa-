"""科学计算器（Scientific Calculator）

一个零第三方依赖的计算器软件，包含：
- calculator/engine.py  —— 安全表达式求值引擎（词法分析 + 调度场算法，不用 eval）
- calculator/cli.py     —— 终端交互式界面（REPL）
- calculator/gui.py     —— Tkinter 图形界面（需系统支持 Tk）
- tests/test_engine.py  —— 单元测试（unittest）

快速开始：
    python calculator/cli.py              # 命令行计算器
    python calculator/cli.py -e "2^10"    # 单次计算
    python calculator/gui.py              # 图形界面（有桌面环境时）
    python -m unittest discover tests -v  # 运行测试
"""

__version__ = "1.0.0"
