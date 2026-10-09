"""Unit tests for the calculator module."""

import unittest

from calculator import add, subtract


class TestAdd(unittest.TestCase):
    def test_add_positive_numbers(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative_numbers(self):
        self.assertEqual(add(-1, -1), -2)

    def test_add_zero(self):
        self.assertEqual(add(0, 5), 5)


class TestSubtract(unittest.TestCase):
    def test_subtract_positive_numbers(self):
        self.assertEqual(subtract(5, 3), 2)

    def test_subtract_result_negative(self):
        self.assertEqual(subtract(3, 5), -2)

    def test_subtract_negative_numbers(self):
        self.assertEqual(subtract(-1, -1), 0)

    def test_subtract_zero(self):
        self.assertEqual(subtract(0, 0), 0)

    def test_subtract_floats(self):
        self.assertAlmostEqual(subtract(2.5, 1.25), 1.25)


if __name__ == "__main__":
    unittest.main()
