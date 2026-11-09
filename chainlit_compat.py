"""Nimi compatibility shim for Chainlit's synchronous profile-config lookup.

Chainlit 2.12.0 calls the async set_chat_profiles wrapper via
asyncio.get_event_loop().run_until_complete() from WebsocketSession.get_config().
That method can run while the server event loop is already active, causing a
RuntimeError and leaving the newly-created coroutine unawaited.

Nimi's chat profiles are prompt/tool profiles only: none defines
ChatProfile.config_overrides. Returning Chainlit's global config is therefore
equivalent for every Nimi profile and avoids re-entering the running event loop.
If Nimi adds config_overrides to a profile, this shim must be revisited.
"""


def apply_chat_profile_config_compat() -> None:
    """Skip redundant async profile lookup when no profile has config overrides."""
    from chainlit.session import WebsocketSession

    if getattr(WebsocketSession, "_nimi_profile_config_compat", False):
        return

    def get_config(self):
        from chainlit.config import config

        return config

    WebsocketSession.get_config = get_config
    WebsocketSession._nimi_profile_config_compat = True
