import unittest

from agent_registry import (
    AGENTS,
    ALL_TOOL_NAMES,
    get_agent,
    get_agent_prompt,
    get_allowed_tools,
)


class AgentRegistryTests(unittest.TestCase):
    def test_all_profiles_have_server_owned_prompts_and_valid_tools(self):
        for name, config in AGENTS.items():
            with self.subTest(profile=name):
                self.assertTrue(config["prompt"])
                self.assertLessEqual(config["tools"], ALL_TOOL_NAMES)

    def test_unknown_profile_falls_back_to_general(self):
        self.assertIs(get_agent("not-a-real-agent"), AGENTS["General"])
        self.assertIs(get_agent(None), AGENTS["General"])

    def test_research_agent_can_search_but_coding_agent_cannot(self):
        self.assertIn("web_search", get_allowed_tools("Research Agent"))
        self.assertNotIn("web_search", get_allowed_tools("Coding Helper"))

    def test_tool_toggle_disables_every_tool(self):
        for profile in AGENTS:
            with self.subTest(profile=profile):
                self.assertEqual(get_allowed_tools(profile, False), frozenset())

    def test_no_agent_has_code_execution_or_filesystem_tools(self):
        forbidden = {"python_exec", "shell", "filesystem", "write_file", "deploy"}
        for profile in AGENTS:
            with self.subTest(profile=profile):
                self.assertTrue(get_allowed_tools(profile).isdisjoint(forbidden))

    def test_prompts_keep_code_execution_disabled(self):
        for profile in ("Coding Helper", "Debugging Agent"):
            with self.subTest(profile=profile):
                self.assertTrue(get_agent_prompt(profile))


if __name__ == "__main__":
    unittest.main()
