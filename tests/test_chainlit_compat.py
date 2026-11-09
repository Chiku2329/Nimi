import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from chainlit.config import config
from chainlit.session import WebsocketSession

from chainlit_compat import apply_chat_profile_config_compat


class ChainlitCompatibilityTests(unittest.TestCase):
    def test_profile_config_lookup_does_not_reinvoke_async_callback(self):
        callback = AsyncMock()
        with patch.object(config.code, "set_chat_profiles", callback):
            apply_chat_profile_config_compat()
            session = SimpleNamespace(chat_profile="General")
            self.assertIs(WebsocketSession.get_config(session), config)
            callback.assert_not_awaited()

    def test_compatibility_patch_is_idempotent(self):
        apply_chat_profile_config_compat()
        patched_method = WebsocketSession.get_config
        apply_chat_profile_config_compat()
        self.assertIs(WebsocketSession.get_config, patched_method)


if __name__ == "__main__":
    unittest.main()
