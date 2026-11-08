"""Read-only website/native shared catalog API invariants and HTTP contract."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from admin_core import mobile_public_catalog as m

def row(**kw):
    d={"sku":"GYS-099","merchant_slug":"verified-merchant","name":"정식 승인 실물상품",
       "description":"검증된 출고상품","category_code":"seafood","category_name":"수산물",
       "price_krw":45000,"stock":6,"image_ref":"https://cdn.example.org/verified.jpg",
       "updated_at":datetime(2026,11,8,tzinfo=timezone.utc)}
    d.update(kw)
    return d

class FakeDb:
    def __init__(self, rows):
        self.rows=rows
        self.queries=[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql):
        self.queries.append(sql)
        return self
    def fetchall(self):return self.rows

class MobileCatalogAPITests(unittest.TestCase):
    def test_verified_release_view_and_all_safety_predicates_mandatory(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parents[1] / "db/migrations" /
           "20261108_garak_catalog_public_ro_view.sql").read_text(encoding="utf-8")
        for required in ("garak_partner_release_ready","r.release_ready IS TRUE",
                         "p.status='approved'","c.status='approved'",
                         "p.visible IS TRUE","p.purchasable IS TRUE",
                         "p.image_verified IS TRUE","p.stock > 0",
                         "p.price_krw > 0","p.image_ref ~* '^https://'",
                         "REVOKE ALL ON garak_catalog_api.approved_products"):
            self.assertIn(required,s)
        self.assertIn("FROM garak_catalog_api.approved_products",m.PUBLISHED_SQL)
        self.assertIn("LIMIT 501",m.PUBLISHED_SQL)

    def test_release_empty_returns_no_fabricated_products_and_never_enables_checkout(self):
        data=m._serialize([])
        self.assertEqual(data["items"],[])
        self.assertEqual(data["merchants"],[])
        self.assertEqual(data["count"],0)
        self.assertFalse(data["order_service_ready"])
        self.assertFalse(data["delivery_tracking_ready"])

    def test_two_verified_merchants_and_skus_share_same_contract(self):
        p=m._serialize([row(),row(sku="SEA-002",merchant_slug="other-approved",
                                     image_ref="https://cdn.example.org/real.png",stock=2)])
        self.assertEqual(p["count"],2)
        self.assertEqual(len(p["merchants"]),2)
        self.assertTrue(all(i["currency"]=="KRW" for i in p["items"]))
        self.assertTrue(all(not i["can_checkout"] for i in p["items"]))

    def test_invalid_price_photo_stock_and_merchant_are_rejected(self):
        xs=[row(stock=0),row(image_ref="images_800/dummy.jpg"),
            row(image_ref="https://name:pass@example.org/img.jpg"),
            row(price_krw=0),row(price_krw="45000"),
            row(merchant_slug="../path"),row(sku="illegal!!")]
        self.assertEqual(m._serialize(xs)["count"],0)

    def test_duplicate_release_sku_fails_closed(self):
        with self.assertRaises(ValueError):
            m._serialize([row(),row()])
    def test_catalog_result_exceeding_limit_fails_closed(self):
        many=[row(sku=f"SKU-{i:04d}") for i in range(501)]
        with self.assertRaises(ValueError):
            m._serialize(many)

    def test_get_snapshot_requires_neon_not_sqlite_fixture(self):
        with patch.object(m,"use_postgres",return_value=False):
            with self.assertRaises(ConnectionError):
                m.get_snapshot(lambda: FakeDb([row()]))

    def test_snapshot_reads_verified_database_rows(self):
        db=FakeDb([row()])
        with patch.object(m,"use_postgres",return_value=True):
            result=m.get_snapshot(lambda:db)
        self.assertEqual(result["count"],1)
        self.assertIn("garak_catalog_api.approved_products",db.queries[0])

    def test_etag_refresh_changes_when_price_or_new_merchant_changes(self):
        first=m._serialize([row()])
        code,h,b=m.handle("GET","/api/mobile/v1/catalog",{},snapshot_loader=lambda:first)
        self.assertEqual(code,200)
        self.assertEqual(json.loads(b)["items"][0]["price_krw"],45000)
        self.assertEqual(h["Cache-Control"],"no-store, max-age=0")
        etag=h["ETag"]
        code2,h2,b2=m.handle("GET","/api/mobile/v1/catalog",
                              {"If-None-Match":etag},snapshot_loader=lambda:first)
        self.assertEqual(code2,304);self.assertEqual(b2,b"")
        changed=m._serialize([row(price_krw=51000),
            row(sku="NEW-001",merchant_slug="new-approved-merchant")])
        code3,h3,b3=m.handle("GET","/api/mobile/v1/catalog",
            {"If-None-Match":etag},snapshot_loader=lambda:changed)
        self.assertEqual(code3,200);self.assertNotEqual(h3["ETag"],etag)
        self.assertEqual(json.loads(b3)["count"],2)

    def test_merchant_list_has_only_eligible_merchant_not_pending_application(self):
        p=m._serialize([row()])
        status,_,body=m.handle("GET","/api/mobile/v1/merchants",{},snapshot_loader=lambda:p)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)["merchants"][0]["id"],"verified-merchant")

    def test_detail_refresh_price_and_unlisted_sku_404(self):
        p=m._serialize([row(price_krw=72000)])
        status,_,body=m.handle("GET","/api/mobile/v1/catalog/GYS-099",{},snapshot_loader=lambda:p)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)["product"]["price_krw"],72000)
        status,_,body=m.handle("GET","/api/mobile/v1/catalog/GYS-001",{},snapshot_loader=lambda:p)
        self.assertEqual(status,404)
        self.assertEqual(json.loads(body)["error"],"product_not_available")

    def test_orders_and_delivery_never_expose_unowned_data(self):
        for path in ("/api/mobile/v1/orders","/api/mobile/v1/delivery"):
            status,_,b=m.handle("GET",path,{},
                         snapshot_loader=lambda:m._serialize([row()]))
            self.assertEqual(status,503)
            self.assertEqual(json.loads(b)["error"],"authenticated_order_api_not_ready")

    def test_invalid_http_method_and_backend_outage(self):
        status,_,b=m.handle("POST","/api/mobile/v1/catalog",{},
                         snapshot_loader=lambda:m._serialize([row()]))
        self.assertEqual(status,405)
        status,h,b=m.handle("GET","/api/mobile/v1/catalog",{},
                         snapshot_loader=lambda:1/0)
        self.assertEqual(status,503)
        self.assertNotIn("division",b.decode())

if __name__=="__main__":
    unittest.main()
