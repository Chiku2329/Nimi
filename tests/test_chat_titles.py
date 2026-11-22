import unittest

from chat_titles import make_chat_title


class ChatTitleTests(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(make_chat_title("  Help me\n\tplan   a trip  "), "Help me plan a trip")

    def test_truncates_at_word_boundary(self):
        title = make_chat_title("Please explain how the model router chooses a fallback provider", 30)
        self.assertLessEqual(len(title), 30)
        self.assertTrue(title)
        self.assertNotEqual(title[-1], " ")

    def test_empty_or_invalid_input_uses_default(self):
        self.assertEqual(make_chat_title(" \n "), "New chat")
        self.assertEqual(make_chat_title(None), "New chat")

    def test_short_message_is_preserved(self):
        self.assertEqual(make_chat_title("Explain photosynthesis"), "Explain photosynthesis")


if __name__ == "__main__":
    unittest.main()
