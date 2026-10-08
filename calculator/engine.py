"""计算器核心引擎：安全的表达式求值（不使用 eval）。

支持功能：
- 四则运算 + - * / // ** （^ 作为 ** 的别名）
- 括号嵌套、隐式乘法（如 2(3+4)）
- 一元正负号（如 -5、-(2+3)）
- 常数：pi, e, tau, phi
- 函数：sqrt/√, abs, round, floor, ceil, sin, cos, tan, asin, acos, atan,
        log (以10为底，可带底数), ln, exp, factorial
- 百分号后缀：数字后加 % 表示除以 100（如 50% -> 0.5, 200+10%*200 -> 220）
- 阶乘后缀：5! -> 120

所有输入先经过词法分析，再经调度场算法转为逆波兰表达式求值，
从根本上杜绝任意代码执行。数值计算基于 Decimal，避免二进制浮点误差。
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_UP, getcontext

# 提高精度，避免浮点误差（如 0.1+0.2）
getcontext().prec = 28

# ---------------------------------------------------------------------------
# 异常定义
# ---------------------------------------------------------------------------


class CalcError(Exception):
    """计算器计算错误基类。"""


class SyntaxErr(CalcError):
    """表达式语法错误。"""


class MathErr(CalcError):
    """数学错误（除零、定义域等）。"""


# ---------------------------------------------------------------------------
# 词法分析
# ---------------------------------------------------------------------------

TOKEN_NUM = "NUM"
TOKEN_OP = "OP"
TOKEN_FUNC = "FUNC"
TOKEN_CONST = "CONST"
TOKEN_LPAR = "LPAR"
TOKEN_RPAR = "RPAR"
TOKEN_POSTFIX = "POSTFIX"  # ! 或 %
TOKEN_COMMA = "COMMA"

FUNCS = {
    "sqrt", "abs", "round", "floor", "ceil",
    "sin", "cos", "tan", "asin", "acos", "atan",
    "log", "ln", "exp", "factorial",
}

CONSTS = {
    "pi": Decimal(str(math.pi)),
    "e": Decimal(str(math.e)),
    "tau": Decimal(str(math.tau)),
    "phi": Decimal("1.618033988749895"),
}


def tokenize(expr: str) -> list[tuple[str, str]]:
    """将表达式字符串切分为 token 列表。"""
    expr = (
        expr.replace("，", ",")
        .replace("（", "(")
        .replace("）", ")")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
    )
    tokens: list[tuple[str, str]] = []
    i, n = 0, len(expr)

    while i < n:
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and expr[i + 1].isdigit()):
            j = i
            seen_dot = False
            seen_e = False
            while j < n:
                c = expr[j]
                if c.isdigit():
                    j += 1
                elif c == "." and not seen_dot and not seen_e:
                    seen_dot = True
                    j += 1
                elif c in "eE" and not seen_e and j > i and expr[j - 1].isdigit():
                    # 科学计数法 1e3, 2.5E-4
                    seen_e = True
                    j += 1
                    if j < n and expr[j] in "+-":
                        j += 1
                else:
                    break
            tokens.append((TOKEN_NUM, expr[i:j]))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            name = expr[i:j].lower()
            if name in FUNCS:
                tokens.append((TOKEN_FUNC, name))
            elif name in CONSTS:
                tokens.append((TOKEN_CONST, name))
            else:
                raise SyntaxErr(f"未知标识符 '{name}'")
            i = j
            continue
        if ch == "√":
            tokens.append((TOKEN_FUNC, "sqrt"))
            i += 1
            continue
        if ch == "(":
            tokens.append((TOKEN_LPAR, ch))
            i += 1
            continue
        if ch == ")":
            tokens.append((TOKEN_RPAR, ch))
            i += 1
            continue
        if ch in "!%":
            tokens.append((TOKEN_POSTFIX, ch))
            i += 1
            continue
        if ch == ",":
            tokens.append((TOKEN_COMMA, ch))
            i += 1
            continue
        two = expr[i:i + 2]
        if two in ("**", "//"):
            tokens.append((TOKEN_OP, two))
            i += 2
            continue
        if ch in "+-*/^":
            tokens.append((TOKEN_OP, ch))
            i += 1
            continue
        raise SyntaxErr(f"非法字符 '{ch}'")

    return tokens


# ---------------------------------------------------------------------------
# 调度场算法（中缀 -> 逆波兰）
# ---------------------------------------------------------------------------

PRECEDENCE = {
    "+": 1, "-": 1,
    "*": 2, "/": 2, "//": 2,
    "^": 3, "**": 3,
    "u-": 4, "u+": 4,   # 一元符号：优先级高于幂（-2^2 = (-2)^2 = 4）
    "!": 5, "%": 5,     # 后缀运算符
}
RIGHT_ASSOC = {"^", "**", "u-", "u+"}   # 幂与一元符号均右结合


def _prec(name: str) -> int:
    """查询优先级；栈中的 '-'/'+' 一定是一元（二元在入栈前已被改名）。"""
    if name in ("-", "+"):
        return PRECEDENCE["u" + name]
    return PRECEDENCE[name]
# 函数参数个数：固定值或 (min, max)
ARG_COUNT = {
    "sqrt": 1, "abs": 1, "round": (1, 2), "floor": 1, "ceil": 1,
    "sin": 1, "cos": 1, "tan": 1, "asin": 1, "acos": 1, "atan": 1,
    "log": (1, 2), "ln": 1, "exp": 1, "factorial": 1,
}


def to_rpn(tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    stack: list[tuple[str, str]] = []  # kind ∈ OP/FUNC/LPAR/COMMA
    prev_value = None  # 上一个 token，用于判断一元运算 / 隐式乘法

    def expect_operand() -> bool:
        """是否处于需要操作数的位置（据此区分一元/二元运算符）。"""
        return prev_value is None or prev_value[0] in (
            TOKEN_OP, TOKEN_LPAR, TOKEN_FUNC, TOKEN_COMMA)

    def ends_operand() -> bool:
        return prev_value is not None and prev_value[0] in (
            TOKEN_NUM, TOKEN_CONST, TOKEN_RPAR, TOKEN_POSTFIX)

    for kind, val in tokens:
        if kind == TOKEN_NUM:
            if ends_operand():
                # 隐式乘法：2 3 -> 2*3，以及 (2)(3)、2pi 等
                _pop_to(out, stack, 2)
                stack.append((TOKEN_OP, "*"))
            out.append((TOKEN_NUM, val))
            prev_value = (TOKEN_NUM, val)
        elif kind == TOKEN_CONST:
            if ends_operand():
                _pop_to(out, stack, 2)
                stack.append((TOKEN_OP, "*"))
            out.append((TOKEN_CONST, val))
            prev_value = (TOKEN_CONST, val)
        elif kind == TOKEN_FUNC:
            if ends_operand():
                _pop_to(out, stack, 2)
                stack.append((TOKEN_OP, "*"))
            stack.append((TOKEN_FUNC, val))
            prev_value = (TOKEN_FUNC, val)
        elif kind == TOKEN_LPAR:
            if not expect_operand():
                # 隐式乘法：2(3+4)、(2)(3)
                _pop_to(out, stack, 2)
                stack.append((TOKEN_OP, "*"))
            stack.append((TOKEN_LPAR, val))
            prev_value = (TOKEN_LPAR, val)
        elif kind == TOKEN_RPAR:
            if expect_operand():
                raise SyntaxErr("括号不匹配")
            while stack and stack[-1][0] != TOKEN_LPAR:
                out.append(stack.pop())
            if not stack:
                raise SyntaxErr("括号不匹配")
            stack.pop()  # 弹出左括号
            if stack and stack[-1][0] == TOKEN_FUNC:
                out.append(stack.pop())
            prev_value = (TOKEN_RPAR, val)
        elif kind == TOKEN_COMMA:
            if expect_operand():
                raise SyntaxErr("',' 前缺少参数")
            # 弹出运算符直到最近的左括号（逗号只在函数调用的括号内出现）
            found_lpar = False
            while stack:
                if stack[-1][0] == TOKEN_LPAR:
                    found_lpar = True
                    break
                out.append(stack.pop())
            if not found_lpar:
                raise SyntaxErr("',' 只能用于函数参数之间")
            prev_value = (TOKEN_COMMA, val)
        elif kind == TOKEN_POSTFIX:
            if expect_operand():
                raise SyntaxErr(f"'{val}' 前缺少数值")
            out.append((TOKEN_OP, val))
            prev_value = (TOKEN_POSTFIX, val)
        elif kind == TOKEN_OP:
            if val in ("-", "+") and expect_operand():
                # 一元运算符：以前缀形式直接写入 RPN（u- 位于其操作数之前），
                # 天然右结合（--5 -> u- u- 5），且不会误弹栈中的其他运算符。
                out.append((TOKEN_OP, "u" + val))
                prev_value = (TOKEN_OP, "u" + val)
                continue
            op = val
            prec = PRECEDENCE[op]
            while (stack and stack[-1][0] == TOKEN_OP
                   and (PRECEDENCE[stack[-1][1]] > prec
                        or (PRECEDENCE[stack[-1][1]] == prec
                            and op not in RIGHT_ASSOC))):
                out.append(stack.pop())
            stack.append((TOKEN_OP, op))
            prev_value = (TOKEN_OP, op)
        else:
            raise SyntaxErr("无法解析的输入")

    while stack:
        item = stack.pop()
        if item[0] == TOKEN_LPAR:
            raise SyntaxErr("括号不匹配")
        out.append(item)
    return out


def _pop_to(out, stack, min_prec):
    """弹出栈中优先级 >= min_prec 的二元运算符（用于隐式乘法）。"""
    while stack and stack[-1][0] == "OP" and PRECEDENCE[stack[-1][1]] >= min_prec:
        out.append(stack.pop())


# ---------------------------------------------------------------------------
# RPN 求值
# ---------------------------------------------------------------------------


def _to_number(s: str) -> Decimal:
    try:
        return Decimal(s)
    except InvalidOperation:
        raise SyntaxErr(f"非法数字 '{s}'")


def _f(x: Decimal) -> float:
    v = float(x)
    if math.isnan(v) or math.isinf(v):
        raise MathErr("数值超出范围")
    return v


def _d(x: float) -> Decimal:
    if math.isnan(x) or math.isinf(x):
        raise MathErr("数值超出范围")
    return Decimal(repr(x))


def _factorial(x: Decimal) -> Decimal:
    if x < 0 or x != x.to_integral_value():
        raise MathErr("阶乘仅支持非负整数")
    if x > 170:
        raise MathErr("阶乘参数过大（≤170）")
    return Decimal(math.factorial(int(x)))


def _clean(value: Decimal) -> Decimal:
    """消除除法/超越函数产生的末位舍入误差，如 99.99...9 -> 100。"""
    if value == 0 or not value.is_finite():
        return value
    sign = -1 if value < 0 else 1
    av = abs(value)
    # 极小值（量级 < 1e-14）直接归零，如 sin(pi) ≈ 1.2e-16
    if av.adjusted() < -14:
        return Decimal(0)
    digits = "".join(str(d) for d in av.as_tuple().digits)
    exp10 = av.adjusted()  # 最高有效位的十进制指数

    def try_round(k: int) -> Decimal | None:
        """把 av 舍入到小数点后 k 位；若相对改动 < 1e-13 则接受。"""
        scale = Decimal(1) if k <= 0 else Decimal(10) ** (-k)
        candidate = av.quantize(scale, rounding=ROUND_HALF_UP)
        if candidate == 0 or candidate == av:
            return None
        if abs(candidate - av) / av < Decimal("1e-13"):
            return sign * candidate.normalize()
        return None

    # 1) 尾部连续 6 个以上 9（或 0）：在噪声段起始处截断取整
    for run in ("9" * 6, "0" * 6):
        pos = len(digits) - len(run)
        if pos >= 0 and digits.endswith(run) and digits[pos - 1] != run[0]:
            kept = len(digits) - pos
            r = try_round(exp10 + 1 - kept)
            if r is not None:
                return r
    # 2) 前导数字之后几乎全是噪声（如 2.00000000000000014...）：保留 12 位有效数字
    if len(digits) > 13:
        r = try_round(exp10 + 1 - 12)
        if r is not None:
            return r
    return value


def _apply_func(name: str, args: list[Decimal]) -> Decimal:
    try:
        if name == "sqrt":
            if args[0] < 0:
                raise MathErr("负数不能开平方")
            return _d(math.sqrt(_f(args[0])))
        if name == "abs":
            return abs(args[0])
        if name == "round":
            if len(args) == 1:
                return round(args[0])
            return round(args[0], int(args[1]))
        if name == "floor":
            return Decimal(math.floor(args[0]))
        if name == "ceil":
            return Decimal(math.ceil(args[0]))
        if name == "sin":
            return _d(math.sin(_f(args[0])))
        if name == "cos":
            return _d(math.cos(_f(args[0])))
        if name == "tan":
            return _d(math.tan(_f(args[0])))
        if name == "asin":
            if not (-1 <= args[0] <= 1):
                raise MathErr("asin 定义域为 [-1, 1]")
            return _d(math.asin(_f(args[0])))
        if name == "acos":
            if not (-1 <= args[0] <= 1):
                raise MathErr("acos 定义域为 [-1, 1]")
            return _d(math.acos(_f(args[0])))
        if name == "atan":
            return _d(math.atan(_f(args[0])))
        if name == "exp":
            return _d(math.exp(_f(args[0])))
        if name == "ln":
            if args[0] <= 0:
                raise MathErr("ln 要求参数 > 0")
            return _d(math.log(_f(args[0])))
        if name == "log":
            if args[0] <= 0:
                raise MathErr("log 要求参数 > 0")
            if len(args) == 2:
                if args[1] <= 0 or args[1] == 1:
                    raise MathErr("log 底数需 > 0 且 ≠ 1")
                return _d(math.log(_f(args[0]), _f(args[1])))
            return _d(math.log10(_f(args[0])))
        if name == "factorial":
            return _factorial(args[0])
    except MathErr:
        raise
    except (ValueError, OverflowError) as exc:
        raise MathErr(f"{name}: {exc}")
    raise MathErr(f"未知函数 {name}")


def _apply_binop(op: str, a: Decimal, b: Decimal) -> Decimal:
    try:
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise MathErr("除数不能为零")
            return a / b
        if op == "//":
            if b == 0:
                raise MathErr("除数不能为零")
            return a // b
        if op in ("**", "^"):
            return _pow(a, b)
    except MathErr:
        raise
    except (ArithmeticError, ValueError, OverflowError) as exc:
        raise MathErr(str(exc))
    raise MathErr(f"未知运算符 {op}")


def _pow(a: Decimal, b: Decimal) -> Decimal:
    # 整数幂用 Decimal 精确计算
    if b == b.to_integral_value() and abs(b) < 10000:
        bi = int(b)
        if bi >= 0:
            return a ** bi
        if a == 0:
            raise MathErr("0 不能取负指数幂")
        return Decimal(1) / (a ** (-bi))
    if a < 0:
        raise MathErr("负数的非整数次幂无实数解")
    if a == 0 and b < 0:
        raise MathErr("0 不能取负指数幂")
    return _d(_f(a) ** _f(b))


def eval_rpn(rpn: list[tuple[str, str]]) -> Decimal:
    stack: list[Decimal] = []
    pending_neg = 0   # 已读取、尚未配对操作数的前置一元负号个数
    pending_pos = 0   # 前置一元正号个数（无实际作用，仅消费操作数）

    def pop1() -> Decimal:
        if not stack:
            raise SyntaxErr("表达式不完整")
        return stack.pop()

    def apply_pending() -> None:
        """把一个刚完成的操作数交给等待中的一元符号（后读入的先应用 -> 右结合）。"""
        nonlocal pending_neg, pending_pos
        while pending_neg or pending_pos:
            if pending_neg:
                stack.append(-pop1())
                pending_neg -= 1
            else:
                pending_pos -= 1

    for kind, val in rpn:
        if kind == TOKEN_NUM:
            stack.append(_to_number(val))
            apply_pending()
        elif kind == TOKEN_CONST:
            stack.append(CONSTS[val])
            apply_pending()
        elif kind == "FUNC":
            spec = ARG_COUNT[val]
            if isinstance(spec, tuple):
                lo, hi = spec
                count = min(hi, len(stack))
                if count < lo:
                    raise SyntaxErr(f"函数 {val} 参数不足")
            else:
                count = spec
                if len(stack) < count:
                    raise SyntaxErr(f"函数 {val} 参数不足")
            args = [stack.pop() for _ in range(count)][::-1]
            stack.append(_apply_func(val, args))
            apply_pending()
        elif kind == "OP":
            if val == "u-":
                pending_neg += 1
            elif val == "u+":
                pending_pos += 1
            elif val == "!":
                stack.append(_factorial(pop1()))
                apply_pending()
            elif val == "%":
                stack.append(pop1() / Decimal(100))
                apply_pending()
            else:
                apply_pending()
                b = pop1()
                a = pop1()
                stack.append(_apply_binop(val, a, b))
        else:
            raise SyntaxErr("无法计算的输入")

    if pending_neg or pending_pos:
        raise SyntaxErr("表达式不完整")
    if len(stack) != 1:
        raise SyntaxErr("表达式不完整")
    return stack[0]


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------


def format_result(value: Decimal) -> str:
    """把结果格式化为易读字符串（千分位、去尾零）。"""
    normalized = value.normalize()
    exponent = normalized.adjusted()
    if normalized == normalized.to_integral_value() and -6 <= exponent < 21:
        return f"{int(normalized):,}"
    if abs(exponent) >= 21 or exponent < -7:
        # 科学计数法
        s = f"{float(normalized):.10e}".rstrip("0").rstrip(".")
        return s.replace("e+", "e")
    s = format(normalized, "f")
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    int_part, _, frac_part = s.partition(".")
    int_part = f"{int(int_part):,}" if int_part else "0"
    s = f"{int_part}.{frac_part}" if frac_part else int_part
    return ("-" if neg else "") + s


def add(left, right):
    """加法：返回 left + right（Decimal 精确计算）。"""
    return _to_number(str(left)) + _to_number(str(right))


def subtract(left, right):
    """减法：返回 left - right（Decimal 精确计算）。

    >>> subtract(10, 3)
    Decimal('7')
    >>> subtract(0.3, 0.1)
    Decimal('0.2')
    """
    return _to_number(str(left)) - _to_number(str(right))


def multiply(left, right):
    """乘法：返回 left * right（Decimal 精确计算）。"""
    return _to_number(str(left)) * _to_number(str(right))


def divide(left, right):
    """除法：返回 left / right；除数为零时抛出 MathErr。"""
    a = _to_number(str(left))
    b = _to_number(str(right))
    if b == 0:
        raise MathErr("除数不能为零")
    return a / b


def calculate(expression: str) -> str:
    """计算表达式字符串并返回格式化结果。出错抛出 CalcError 子类。"""
    expression = expression.strip()
    if not expression:
        raise SyntaxErr("表达式为空")
    # 双保险：拒绝明显非法字符（词法分析本身已白名单化）
    if any(c in expression for c in "{}[];\"'`\\="):
        raise SyntaxErr("包含非法字符")
    tokens = tokenize(expression)
    rpn = to_rpn(tokens)
    if not rpn:
        raise SyntaxErr("表达式为空")
    result = eval_rpn(rpn)
    return format_result(_clean(result))
