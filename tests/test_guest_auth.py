import unittest
from unittest.mock import patch

from guest_auth import COOKIE_NAME, guest_identifier_from_cookie, make_guest_cookie


class GuestAuthTests(unittest.TestCase):
    def test_cookie_round_trip_has_stable_private_identifier(self):
        with patch.dict("os.environ", {"NIMI_GUEST_SECRET": "x" * 48}):
            cookie = make_guest_cookie()
            header = f"{COOKIE_NAME}={cookie}"
            first = guest_identifier_from_cookie(header)
            second = guest_identifier_from_cookie(header)
            self.assertIsNotNone(first)
            self.assertEqual(first, second)
            self.assertTrue(first.startswith("guest_"))

    def test_tampered_cookie_is_rejected(self):
        with patch.dict("os.environ", {"NIMI_GUEST_SECRET": "x" * 48}):
            cookie = make_guest_cookie()
            token, signature = cookie.split(".", 1)
            tampered = f"{COOKIE_NAME}={token}.{signature[:-1]}0"
            self.assertIsNone(guest_identifier_from_cookie(tampered))

    def test_missing_cookie_is_rejected(self):
        with patch.dict("os.environ", {"NIMI_GUEST_SECRET": "x" * 48}):
            self.assertIsNone(guest_identifier_from_cookie(None))
            self.assertIsNone(guest_identifier_from_cookie("other=value"))

    def test_missing_secret_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                make_guest_cookie()


if __name__ == "__main__":
    unittest.main()
