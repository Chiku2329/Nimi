import unittest

from math_utils import calculate_expression, extract_arithmetic_expression


class MathUtilsTests(unittest.TestCase):
    def test_multiply_phrase_is_detected_and_evaluated_without_a_model(self):
        expression = extract_arithmetic_expression("multiply 25 by 4")
        self.assertEqual(expression, "25 * 4")
        self.assertEqual(calculate_expression(expression), "100")

    def test_common_multiplication_wordings(self):
        for prompt in ("25 times 4", "what is 25 multiplied by 4", "25 × 4", "calculate 25 * 4"):
            with self.subTest(prompt=prompt):
                expression = extract_arithmetic_expression(prompt)
                self.assertIsNotNone(expression)
                self.assertEqual(calculate_expression(expression), "100")

    def test_supports_other_basic_operations(self):
        self.assertEqual(calculate_expression(extract_arithmetic_expression("10 divided by 2")), "5.0")
        self.assertEqual(calculate_expression(extract_arithmetic_expression("7 plus 3")), "10")

    def test_ambiguous_text_is_not_interpreted_as_arithmetic(self):
        self.assertIsNone(extract_arithmetic_expression("multiply your impact by working harder"))

    def test_expression_evaluator_rejects_unsupported_python(self):
        with self.assertRaises(ValueError):
            calculate_expression("__import__('os').system('echo unsafe')")


if __name__ == '__main__':
    unittest.main()
