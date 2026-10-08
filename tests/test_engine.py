"""engine 单元测试。"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator.engine import (  # noqa: E402
    CalcError,
    MathErr,
    SyntaxErr,
    add,
    calculate,
    divide,
    multiply,
    subtract,
)


class TestBasicOperations(unittest.TestCase):
    """add / subtract / multiply / divide 基础运算函数单元测试。"""

    def test_subtract_basic(self):
        self.assertEqual(subtract(10, 3), Decimal("7"))
        self.assertEqual(subtract(3, 10), Decimal("-7"))
        self.assertEqual(subtract(5, 5), Decimal("0"))

    def test_subtract_decimals_no_float_error(self):
        # Decimal 精确计算，避免二进制浮点误差（0.3 - 0.1 != 0.19999...）
        self.assertEqual(subtract(0.3, 0.1), Decimal("0.2"))
        self.assertEqual(subtract("1.5", "0.25"), Decimal("1.25"))

    def test_subtract_negative_operands(self):
        self.assertEqual(subtract(-2, -3), Decimal("1"))
        self.assertEqual(subtract(-2, 3), Decimal("-5"))

    def test_subtract_accepts_strings_and_decimal(self):
        self.assertEqual(subtract("100", "1"), Decimal("99"))
        self.assertEqual(subtract(Decimal("2.5"), Decimal("0.5")), Decimal("2.0"))

    def test_subtract_invalid_input(self):
        with self.assertRaises(SyntaxErr):
            subtract("abc", 1)
        with self.assertRaises(SyntaxErr):
            subtract(1, "x y")

    def test_add(self):
        self.assertEqual(add(1, 2), Decimal("3"))
        self.assertEqual(add(0.1, 0.2), Decimal("0.3"))

    def test_multiply(self):
        self.assertEqual(multiply(6, 7), Decimal("42"))
        self.assertEqual(multiply(-3, 4), Decimal("-12"))

    def test_divide(self):
        self.assertEqual(divide(10, 4), Decimal("2.5"))
        with self.assertRaises(MathErr):
            divide(1, 0)


class TestBasicArithmetic(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(calculate("1+2*3"), "7")
        self.assertEqual(calculate("(1+2)*3"), "9")
        self.assertEqual(calculate("3 + 4 * 2 / (1 - 5) ** 2"), "3.5")

    def test_left_assoc(self):
        self.assertEqual(calculate("7-3-2"), "2")
        self.assertEqual(calculate("100/5/4"), "5")

    def test_unary(self):
        self.assertEqual(calculate("-5+3"), "-2")
        self.assertEqual(calculate("--5"), "5")
        self.assertEqual(calculate("3*-2"), "-6")
        self.assertEqual(calculate("-(2+3)*2"), "-10")

    def test_decimal_precision(self):
        self.assertEqual(calculate("0.1+0.2"), "0.3")
        self.assertEqual(calculate("100/3*3"), "100")
        self.assertEqual(calculate("1/3*3"), "1")

    def test_division_by_zero(self):
        with self.assertRaises(MathErr):
            calculate("1/0")
        with self.assertRaises(MathErr):
            calculate("5//0")


class TestPower(unittest.TestCase):
    def test_power(self):
        self.assertEqual(calculate("2^10"), "1,024")
        self.assertEqual(calculate("2**10"), "1,024")
        self.assertEqual(calculate("2^3^2"), "512")   # 右结合
        self.assertEqual(calculate("2^-1"), "0.5")
        self.assertEqual(calculate("-2^2"), "-4")     # 一元优先于幂（同多数计算器）
        self.assertEqual(calculate("(sqrt(2))^2"), "2")

    def test_negative_base_fractional_exp(self):
        with self.assertRaises(MathErr):
            calculate("(-8)**0.5")


class TestFunctionsAndConstants(unittest.TestCase):
    def test_sqrt(self):
        self.assertEqual(calculate("sqrt(16)"), "4")
        self.assertEqual(calculate("√9"), "3")
        with self.assertRaises(MathErr):
            calculate("sqrt(-4)")

    def test_logs(self):
        self.assertEqual(calculate("log(100)"), "2")
        self.assertEqual(calculate("log(8, 2)"), "3")
        self.assertEqual(calculate("ln(e)"), "1")
        with self.assertRaises(MathErr):
            calculate("log(0)")

    def test_trig(self):
        self.assertEqual(calculate("sin(0)"), "0")
        self.assertEqual(calculate("cos(0)"), "1")
        self.assertEqual(calculate("sin(pi)"), "0")
        with self.assertRaises(MathErr):
            calculate("asin(2)")

    def test_misc_funcs(self):
        self.assertEqual(calculate("abs(-8)"), "8")
        self.assertEqual(calculate("round(3.14159, 2)"), "3.14")
        self.assertEqual(calculate("floor(3.7)"), "3")
        self.assertEqual(calculate("ceil(3.2)"), "4")
        self.assertEqual(calculate("exp(0)"), "1")

    def test_constants(self):
        self.assertEqual(calculate("pi"), "3.141592653589793")
        self.assertEqual(calculate("2pi"), "6.283185307179586")


class TestPostfix(unittest.TestCase):
    def test_factorial(self):
        self.assertEqual(calculate("5!"), "120")
        self.assertEqual(calculate("factorial(6)"), "720")
        with self.assertRaises(MathErr):
            calculate("(-3)!")
        with self.assertRaises(MathErr):
            calculate("171!")

    def test_percent(self):
        self.assertEqual(calculate("50%"), "0.5")
        self.assertEqual(calculate("200+10%*200"), "220")
        self.assertEqual(calculate("2*3%"), "0.06")


class TestImplicitMultiplication(unittest.TestCase):
    def test_implicit(self):
        self.assertEqual(calculate("2(3+4)"), "14")
        self.assertEqual(calculate("(1+2)(3+4)"), "21")


class TestSafetyAndErrors(unittest.TestCase):
    def test_rejects_injection(self):
        for bad in ["__import__('os')", "open('/etc/passwd')", "1;2", "{}", "a=1"]:
            with self.assertRaises(CalcError):
                calculate(bad)

    def test_syntax_errors(self):
        for bad in ["1+", "*3", "(1", "1)", "", "%5", "1,,2", "1,2", ")(", "2 **"]:
            with self.assertRaises(SyntaxErr):
                calculate(bad)

    def test_unknown_identifier(self):
        with self.assertRaises(SyntaxErr):
            calculate("foo(3)")


class TestFormatting(unittest.TestCase):
    def test_thousands_separator(self):
        self.assertEqual(calculate("1000*1000"), "1,000,000")

    def test_scientific_notation_input(self):
        self.assertEqual(calculate("1e3+1"), "1,001")
        self.assertEqual(calculate("2.5E2"), "250")


if __name__ == "__main__":
    unittest.main()
