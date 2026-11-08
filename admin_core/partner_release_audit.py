"""Read-only Garak partner release approval gate.

This module NEVER writes approval, inventory, billing or shipping records.
Its 34-SKU request is blocked until explicit SKU selection and all merchant /
product evidence from the existing garak_partner_release_ready view is verified.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Mapping, Iterable, Any
import json

MERCHANT_EVIDENCE = frozenset({
    "business_registration", "signed_merchant_contract",
    "photo_usage_rights", "cold_chain_plan", "shipping_fee_policy",
    "returns_refund_policy", "pg_settlement_reconciliation",
    "pg_refund_rehearsal",
})
SKU_EVIDENCE = frozenset({
    "product_real_photo", "product_origin_weight",
    "product_price_agreement", "product_stock_confirmation",
})


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def _verified(evidence: Iterable[Mapping[str, Any]], merchant: str,
              sku: str | None) -> dict[str, datetime | None]:
    result = {}
    for row in evidence:
        if (row.get("merchant_slug") != merchant
                or row.get("sku") != sku
                or row.get("status") != "verified"):
            continue
        typ = str(row.get("evidence_type", ""))
        reviewed = _datetime(row.get("reviewed_at"))
        if typ not in result or (reviewed is not None and
                (result[typ] is None or reviewed > result[typ])):
            result[typ] = reviewed
    return result


def inspect_product(product: Mapping[str, Any],
                    categories: Mapping[str, str],
                    evidence: Iterable[Mapping[str, Any]], *,
                    at: datetime) -> list[str]:
    """Pre-approval checks; status/visibility are changed only AFTER all pass."""
    if at.tzinfo is None:
        raise ValueError("Timezone-aware audit timestamp required")
    sku = str(product.get("sku", ""))
    merchant = str(product.get("merchant_slug", ""))
    notes = []
    if product.get("status") not in ("pending", "approved"):
        notes.append("product_status_invalid")
    if categories.get(str(product.get("category_code", ""))) != "approved":
        notes.append("category_not_approved")
    if type(product.get("price_krw")) is not int or product["price_krw"] <= 0:
        notes.append("price_unverified")
    if type(product.get("stock")) is not int or product["stock"] < 1:
        notes.append("stock_zero")
    if str(product.get("currency", "")).strip().upper() != "KRW":
        notes.append("currency_not_krw")
    if product.get("image_verified") is not True:
        notes.append("real_image_unverified")
    if not str(product.get("image_ref", "")).startswith("https://"):
        notes.append("real_image_https_missing")

    evidence = list(evidence)
    global_approved = _verified(evidence, merchant, None)
    local_approved = _verified(evidence, merchant, sku)
    for typ in sorted(MERCHANT_EVIDENCE - global_approved.keys()):
        notes.append("merchant_evidence_missing:" + typ)
    for typ in sorted(SKU_EVIDENCE - local_approved.keys()):
        notes.append("sku_evidence_missing:" + typ)

    # Like the live garak_partner_release_ready view, today's stock
    # confirmation and price agreement must be newly reviewed.
    for typ, age in (("product_stock_confirmation", timedelta(hours=24)),
                     ("product_price_agreement", timedelta(hours=72))):
        reviewed = local_approved.get(typ)
        if reviewed is None or not (at - age <= reviewed <= at):
            notes.append("evidence_review_expired:" + typ)
    return notes


@dataclass
class AuditResult:
    requested_count: int
    catalog_count: int
    selected_count: int
    missing_skus: list[str]
    excluded_skus: list[str]
    per_sku: dict[str, list[str]]
    batch_eligible: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_batch(products: Iterable[Mapping[str, Any]],
                category_statuses: Mapping[str, str],
                evidence: Iterable[Mapping[str, Any]],
                selected_skus: Iterable[str], *,
                requested_count: int = 34,
                at: datetime | None = None) -> AuditResult:
    """An exact set of 34 identified SKUs is required; no arbitrary first-34."""
    if requested_count < 1:
        raise ValueError("requested_count must be positive")
    selected = list(selected_skus)
    if len(selected) != len(set(selected)):
        raise ValueError("duplicate SKU in approval request")
    products = list(products)
    if len({p.get("sku") for p in products}) != len(products):
        raise ValueError("duplicate SKU in catalog")
    by_sku = {p["sku"]: p for p in products}
    missing = sorted(set(selected) - by_sku.keys())
    excluded = sorted(by_sku.keys() - set(selected))
    at = at or datetime.now(timezone.utc)
    evidence = list(evidence)
    results = {
        sku: inspect_product(by_sku[sku], category_statuses, evidence, at=at)
        for sku in sorted(set(selected) & by_sku.keys())
    }
    eligible = (len(selected) == requested_count and not missing
                and len(results) == requested_count
                and all(not errors for errors in results.values()))
    return AuditResult(requested_count, len(by_sku), len(selected),
                       missing, excluded, results, eligible)


def assert_ready_for_activation(audit: AuditResult, *,
                                stripe_account_verified: bool,
                                stripe_test_webhook_passed: bool,
                                shipping_provider_contract_verified: bool,
                                signed_delivery_e2e_passed: bool,
                                merchant_of_record_authorized: bool = False) -> None:
    """Fail closed: an ACTIVE Stripe account is not GarakHansang billing authority."""
    gates = [
        audit.batch_eligible,
        stripe_account_verified,
        merchant_of_record_authorized,
        stripe_test_webhook_passed,
        shipping_provider_contract_verified,
        signed_delivery_e2e_passed,
    ]
    if not all(gates):
        raise ValueError("GO-LIVE BLOCKED: product evidence/Stripe/delivery gates incomplete")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("read_only_snapshot", help="JSON with products, categories, evidence and selected_skus")
    args = ap.parse_args()
    with open(args.read_only_snapshot, encoding="utf-8") as f:
        j = json.load(f)
    report = audit_batch(j["products"], j["categories"], j["evidence"],
                         j.get("selected_skus", []))
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.batch_eligible else 2)
