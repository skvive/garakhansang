"""Ensure that clients never mistake this development API for live commerce."""
import unittest
from backend.mobile_app_contract import build_mobile_bootstrap

class MobileBootstrapContractTests(unittest.TestCase):
    def test_development_release_gates_fail_closed(self):
        body = build_mobile_bootstrap()
        self.assertTrue(body["demo_mode"])
        self.assertEqual(body["environment"], "isolated-development")
        for key in ("real_checkout_enabled", "payments_enabled",
                    "live_tracking_enabled", "delivery_zone_verification_enabled",
                    "merchant_live_orders_enabled", "rider_dispatch_enabled"):
            with self.subTest(feature=key):
                self.assertIs(body["features"][key], False)

    def test_does_not_leak_service_zone_or_eta(self):
        body = build_mobile_bootstrap()
        self.assertEqual(body["delivery_service_zones"], [])
        self.assertIsNone(body["delivery_eta_minutes"])
        self.assertIn("실제 주문", body["message"])

    def test_returns_fresh_mutation_safe_response(self):
        first = build_mobile_bootstrap()
        first["features"]["payments_enabled"] = True
        first["delivery_service_zones"].append("unknown")
        second = build_mobile_bootstrap()
        self.assertIs(second["features"]["payments_enabled"], False)
        self.assertEqual(second["delivery_service_zones"], [])

if __name__ == "__main__":
    unittest.main()
