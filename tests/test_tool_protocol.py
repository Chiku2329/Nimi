import unittest

from tool_protocol import build_tool_exchange


class ToolProtocolTests(unittest.TestCase):
    def test_builds_assistant_tool_calls_and_matching_tool_results(self):
        messages = build_tool_exchange(
            "I will check that.",
            [
                {"id": "call_abc", "name": "web_search", "args": '{"query":"Nimi"}'},
                {"id": "call_def", "name": "calculate", "args": '{"expression":"2+2"}'},
            ],
            ["Search result", "4"],
            round_no=0,
        )

        self.assertEqual(len(messages), 3)
        assistant, search_result, calculation_result = messages
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["content"], "I will check that.")
        self.assertEqual(assistant["tool_calls"][0]["function"]["name"], "web_search")
        self.assertEqual(assistant["tool_calls"][0]["function"]["arguments"], '{"query":"Nimi"}')
        self.assertEqual(search_result, {
            "role": "tool", "tool_call_id": "call_abc", "content": "Search result"
        })
        self.assertEqual(calculation_result, {
            "role": "tool", "tool_call_id": "call_def", "content": "4"
        })

    def test_uses_deterministic_ids_when_provider_omits_them(self):
        messages = build_tool_exchange(
            "", [{"name": "calculate", "args": '{"expression":"2+2"}'}], ["4"], 2
        )
        self.assertIsNone(messages[0]["content"])
        self.assertEqual(messages[0]["tool_calls"][0]["id"], "nimi_tool_2_0")
        self.assertEqual(messages[1]["tool_call_id"], "nimi_tool_2_0")

    def test_rejects_mismatched_call_and_result_counts(self):
        with self.assertRaises(ValueError):
            build_tool_exchange("", [{"name": "calculate", "args": "{}"}], [], 0)

    def test_rejects_missing_tool_name(self):
        with self.assertRaises(ValueError):
            build_tool_exchange("", [{"args": "{}"}], ["result"], 0)


if __name__ == "__main__":
    unittest.main()
