"""Independent release readiness checks; no actual DB, Stripe or courier writes."""
import unittest
from datetime import datetime, timedelta, timezone
from admin_core.partner_release_audit import (
    audit_batch, inspect_product, assert_ready_for_activation,
    MERCHANT_EVIDENCE, SKU_EVIDENCE,
)
NOW = datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc)
MERCHANT = "gwangyang-fisheries"


def prepared_products():
    return [
        {"sku": f"GYS-{n:03d}", "merchant_slug": MERCHANT,
         "category_code": "gys-approved", "status": "pending",
         "price_krw": 12000, "stock": 4, "currency": "KRW",
         "image_verified": True, "image_ref": "https://merchant.example.invalid/authentic-photo.jpg"}
        for n in range(11, 48)
    ]


def prepared_evidence(products):
    rows = [
        {"merchant_slug": MERCHANT, "sku": None, "evidence_type": typ,
         "status": "verified", "reviewed_at": NOW.isoformat()}
        for typ in MERCHANT_EVIDENCE
    ]
    for p in products:
        rows.extend([
            {"merchant_slug": MERCHANT, "sku": p["sku"],
             "evidence_type": typ, "status": "verified",
             "reviewed_at": NOW.isoformat()}
            for typ in SKU_EVIDENCE
        ])
    return rows


class PartnerReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.products = prepared_products()
        self.categories = {"gys-approved": "approved"}
        self.evidence = prepared_evidence(self.products)
        self.skus = [p["sku"] for p in self.products[:34]]

    def audit(self, **changes):
        args = {"products": self.products, "category_statuses": self.categories,
                "evidence": self.evidence, "selected_skus": self.skus, "at": NOW}
        args.update(changes)
        return audit_batch(**args)

    def test_valid_34_staged_skus_are_eligible_not_automatically_published(self):
        r = self.audit()
        self.assertTrue(r.batch_eligible)
        self.assertEqual(r.catalog_count, 37)
        self.assertEqual(r.selected_count, 34)
        self.assertEqual(len(r.excluded_skus), 3)
        self.assertTrue(all(p["status"] == "pending" for p in self.products))

    def test_no_selected_sku_list_never_chooses_arbitrary_34(self):
        r = self.audit(selected_skus=[])
        self.assertFalse(r.batch_eligible)
        self.assertEqual(r.selected_count, 0)

    def test_sku_missing_and_duplicate_block(self):
        r = self.audit(selected_skus=self.skus[:-1] + ["GYS-999"])
        self.assertFalse(r.batch_eligible)
        self.assertEqual(r.missing_skus, ["GYS-999"])
        with self.assertRaises(ValueError):
            self.audit(selected_skus=self.skus[:-1] + [self.skus[0]])

    def test_zero_stock_image_and_unapproved_category_block(self):
        p = dict(self.products[0], stock=0, image_verified=False)
        r = self.audit(products=[p] + self.products[1:],
                       category_statuses={"gys-approved": "pending"})
        self.assertFalse(r.batch_eligible)
        errors = r.per_sku[self.skus[0]]
        self.assertIn("stock_zero", errors)
        self.assertIn("real_image_unverified", errors)
        self.assertIn("category_not_approved", errors)

    def test_no_merchant_evidence_blocks_all(self):
        e = [x for x in self.evidence if x["sku"] is not None]
        r = self.audit(evidence=e)
        self.assertFalse(r.batch_eligible)
        self.assertIn("merchant_evidence_missing:business_registration", r.per_sku[self.skus[0]])

    def test_no_product_evidence_blocks_sku(self):
        e = [x for x in self.evidence if x["sku"] != self.skus[0]]
        r = self.audit(evidence=e)
        self.assertFalse(r.batch_eligible)
        self.assertIn("sku_evidence_missing:product_real_photo", r.per_sku[self.skus[0]])

    def test_evidence_expiry_24h_and_72h_enforced(self):
        e = [
            dict(x, reviewed_at=(NOW - timedelta(hours=100)).isoformat())
            if x.get("sku") == self.skus[0] else x
            for x in self.evidence
        ]
        r = self.audit(evidence=e)
        self.assertIn("evidence_review_expired:product_stock_confirmation",r.per_sku[self.skus[0]])
        self.assertIn("evidence_review_expired:product_price_agreement",r.per_sku[self.skus[0]])

    def test_evidence_submitted_but_not_verified_not_sufficient(self):
        e = [dict(x,status="submitted") if x.get("sku")==self.skus[0] else x
             for x in self.evidence]
        r = self.audit(evidence=e)
        self.assertFalse(r.batch_eligible)

    def test_bad_currency_and_non_https_photo_rejected(self):
        p = dict(self.products[0], currency="USD", image_ref="images_800/demo.jpg")
        r = self.audit(products=[p]+self.products[1:])
        self.assertIn("currency_not_krw",r.per_sku[self.skus[0]])
        self.assertIn("real_image_https_missing",r.per_sku[self.skus[0]])

    def test_release_blocked_if_other_party_stripe_or_real_courier_missing(self):
        r = self.audit()
        with self.assertRaisesRegex(ValueError, "GO-LIVE BLOCKED"):
            assert_ready_for_activation(r,
                stripe_account_verified=False, stripe_test_webhook_passed=True,
                shipping_provider_contract_verified=True,
                signed_delivery_e2e_passed=True)
        with self.assertRaisesRegex(ValueError, "GO-LIVE BLOCKED"):
            assert_ready_for_activation(r,
                stripe_account_verified=True, stripe_test_webhook_passed=True,
                shipping_provider_contract_verified=False,
                signed_delivery_e2e_passed=True)
        assert_ready_for_activation(r, stripe_account_verified=True,
                                    stripe_test_webhook_passed=True,
                                    shipping_provider_contract_verified=True,
                                    signed_delivery_e2e_passed=True,
                                    merchant_of_record_authorized=True)

    def test_active_stripe_account_without_garak_merchant_authorization_is_blocked(self):
        r = self.audit()
        with self.assertRaisesRegex(ValueError, "GO-LIVE BLOCKED"):
            assert_ready_for_activation(
                r, stripe_account_verified=True, stripe_test_webhook_passed=True,
                shipping_provider_contract_verified=True,
                signed_delivery_e2e_passed=True,
                merchant_of_record_authorized=False)

if __name__ == "__main__":
    unittest.main()
