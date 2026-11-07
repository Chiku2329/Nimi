"""Regression tests for guest identity and persisted chat-history access control."""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from guest_auth import guest_identifier_from_cookie, make_guest_cookie
from chainlit.data.acl import is_thread_author


class GuestIdentityIsolationTests(unittest.TestCase):
    def test_each_browser_cookie_maps_to_a_distinct_guest_identity(self):
        first_cookie = make_guest_cookie()
        second_cookie = make_guest_cookie()

        first = guest_identifier_from_cookie(f"nimi_guest={first_cookie}")
        second = guest_identifier_from_cookie(f"nimi_guest={second_cookie}")

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)

    def test_same_valid_cookie_keeps_the_same_guest_identity(self):
        cookie = make_guest_cookie()
        header = f"nimi_guest={cookie}"

        self.assertEqual(
            guest_identifier_from_cookie(header),
            guest_identifier_from_cookie(header),
        )

    def test_tampered_cookie_is_rejected(self):
        cookie = make_guest_cookie()
        replacement = "0" if cookie[-1] != "0" else "1"
        tampered = cookie[:-1] + replacement

        self.assertIsNone(guest_identifier_from_cookie(f"nimi_guest={tampered}"))


class PersistedChatHistoryAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_can_access_their_thread(self):
        data_layer = type("DataLayer", (), {})()
        data_layer.get_thread_author = AsyncMock(return_value="guest_alpha")

        with patch("chainlit.data.acl.get_data_layer", return_value=data_layer):
            self.assertTrue(await is_thread_author("guest_alpha", "thread_alpha"))

    async def test_another_guest_cannot_access_the_thread(self):
        data_layer = type("DataLayer", (), {})()
        data_layer.get_thread_author = AsyncMock(return_value="guest_alpha")

        with patch("chainlit.data.acl.get_data_layer", return_value=data_layer):
            with self.assertRaises(HTTPException) as raised:
                await is_thread_author("guest_beta", "thread_alpha")

        self.assertEqual(raised.exception.status_code, 401)

    async def test_missing_thread_is_not_found(self):
        data_layer = type("DataLayer", (), {})()
        data_layer.get_thread_author = AsyncMock(return_value=None)

        with patch("chainlit.data.acl.get_data_layer", return_value=data_layer):
            with self.assertRaises(HTTPException) as raised:
                await is_thread_author("guest_alpha", "missing_thread")

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
