"""Exact 34-SKU seasonal shortlist is review-only, never auto-published."""
from __future__ import annotations

import json
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

from admin_core.partner_release_audit import audit_batch, assert_ready_for_activation

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "garak_order_34_candidates_20261108.json"


def load():
    with MANIFEST.open(encoding="utf-8") as f:
        return json.load(f)


class Exact34ReleaseShortlistTests(unittest.TestCase):
    def test_exact_34_selected_and_three_held(self):
        m = load()
        self.assertEqual(m["selection_type"], "review_candidates_only")
        self.assertEqual(m["requested_count"], 34)
        self.assertEqual(len(m["candidate_skus"]), 34)
        self.assertEqual(len(set(m["candidate_skus"])), 34)
        self.assertEqual([x["sku"] for x in m["excluded"]],
                         ["GYS-037", "GYS-038", "GYS-039"])
        self.assertEqual(set(m["candidate_skus"]) | {x["sku"] for x in m["excluded"]},
                         {f"GYS-{k:03d}" for k in range(11, 48)})
        self.assertFalse(set(m["candidate_skus"]) & {x["sku"] for x in m["excluded"]})

    def test_never_marks_live_merchant_catalog_paid_or_approved(self):
        m = load()
        self.assertEqual(m["product_approval"], "NOT_APPROVED")
        self.assertFalse(m["product_visibility"])
        self.assertFalse(m["payment_activation"])
        self.assertFalse(m["shipping_activation"])

    def test_unverified_merchant_products_must_fail_go_live(self):
        m = load()
        products = [
            {"sku": f"GYS-{n:03d}", "merchant_slug": m["merchant_slug"],
             "category_code": "gys-pending", "status": "pending", "stock": 0,
             "price_krw": 12000, "currency": "KRW",
             "image_verified": False, "image_ref": "images_800/demo.jpg"}
            for n in range(11, 48)
        ]
        audited = audit_batch(products, {"gys-pending": "pending"}, [],
                              m["candidate_skus"], requested_count=34,
                              at=datetime(2026, 11, 8, tzinfo=timezone.utc))
        self.assertFalse(audited.batch_eligible)
        self.assertEqual(len(audited.per_sku), 34)
        self.assertEqual(len(audited.excluded_skus), 3)
        for problems in audited.per_sku.values():
            self.assertIn("stock_zero", problems)
            self.assertIn("category_not_approved", problems)
            self.assertIn("real_image_unverified", problems)
            self.assertIn("merchant_evidence_missing:business_registration", problems)
        with self.assertRaisesRegex(ValueError, "GO-LIVE BLOCKED"):
            assert_ready_for_activation(
                audited, stripe_account_verified=True,
                stripe_test_webhook_passed=True,
                shipping_provider_contract_verified=True,
                signed_delivery_e2e_passed=True)

    def test_staging_migration_is_draft_only_and_never_mutates_operational_catalog(self):
        sql = (ROOT / "db" / "migrations" /
               "20261108_garak_order_v2_34_draft_catalog.sql").read_text(encoding="utf-8")
        self.assertIn("'draft'", sql)
        self.assertIn("ON CONFLICT(merchant_id,slug) DO NOTHING", sql)
        self.assertIn("p.stock=0 AND p.image_verified=false", sql)
        self.assertIn("p.status='pending'", sql)
        self.assertIn("IF n <> 34", sql)
        for sku in ("GYS-037", "GYS-038", "GYS-039"):
            self.assertIn(sku, sql)
        self.assertIsNone(re.search(r"(?im)^\\s*(UPDATE|DELETE|TRUNCATE|DROP)\\s+", sql))
        self.assertNotIn("DO UPDATE", sql)

    def test_linkrpay_approved_does_not_imply_merchant_of_record_authorization(self):
        m = load()
        self.assertTrue(m["release_conditions"]["merchant_authorized_payment_account"])
        self.assertTrue(m["release_conditions"]["stripe_test_webhook_verified"])
        self.assertTrue(m["release_conditions"]["contracted_delivery_provider_verified"])


if __name__ == "__main__":
    unittest.main()
