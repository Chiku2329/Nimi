import unittest

from response_security import build_security_headers


class ResponseSecurityHeaderTests(unittest.TestCase):
    def test_baseline_browser_security_headers_are_present(self):
        headers = build_security_headers()
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("X-Frame-Options", headers)
        self.assertEqual(
            headers["Content-Security-Policy"],
            "frame-ancestors 'self' https://dashboard.blitz.cloud https://*.blitz.cloud https://*.prod.page",
        )
        self.assertEqual(headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(headers["Permissions-Policy"], "camera=(), microphone=(), geolocation=()")
        self.assertNotIn("Strict-Transport-Security", headers)

    def test_hsts_is_added_only_for_https_responses(self):
        headers = build_security_headers(is_https=True)
        self.assertEqual(
            headers["Strict-Transport-Security"],
            "max-age=31536000; includeSubDomains",
        )


if __name__ == "__main__":
    unittest.main()
