import unittest

from request_routing import select_relevant_tools


ALL = {"web_search", "calculate", "get_weather", "get_time", "remember", "forget", "create_file"}


class RequestRoutingTests(unittest.TestCase):
    def test_general_question_gets_no_tools(self):
        self.assertEqual(select_relevant_tools("Explain photosynthesis simply", ALL), frozenset())

    def test_arithmetic_selects_calculator(self):
        self.assertEqual(select_relevant_tools("multiply 25 by 4", ALL), {"calculate"})

    def test_current_research_selects_search(self):
        self.assertEqual(select_relevant_tools("Research the latest AI news and cite sources", ALL), {"web_search"})

    def test_weather_selects_weather_tool(self):
        self.assertEqual(select_relevant_tools("Will it rain tomorrow? Give me the weather forecast", ALL), {"get_weather"})

    def test_memory_write_requires_explicit_intent(self):
        self.assertEqual(select_relevant_tools("Remember this: I prefer concise answers", ALL), {"remember"})
        self.assertNotIn("remember", select_relevant_tools("What do you remember about me?", ALL))

    def test_file_creation_selects_file_tool(self):
        self.assertEqual(select_relevant_tools("Create a PDF report about solar energy", ALL), {"create_file"})

    def test_agent_allowlist_is_always_enforced(self):
        self.assertEqual(select_relevant_tools("Research the latest news", {"calculate"}), frozenset())


if __name__ == "__main__":
    unittest.main()
