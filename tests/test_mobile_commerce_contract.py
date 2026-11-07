"""Mobile API beta contract checks; no real orders, payments, or PII."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from admin_core.database import init_db,connect
from admin_core.server import Server

class MobileContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"mobile.sqlite3"
        cls.con=init_db(cls.db,seed=True,bootstrap=False)
        cls.con.close()
        cls.server=Server(("127.0.0.1",0),cls.db)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.port=cls.server.server_address[1]
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()
    def setUp(self):
        with connect(self.db) as c:
            c.execute("UPDATE merchants SET status='pending',verified=0")
            c.execute("UPDATE products SET status='published',stock=20")
    def approved(self):
        with connect(self.db) as c:
            c.execute("""UPDATE merchants SET status='active',verified=1
                WHERE id=(SELECT merchant_id FROM products WHERE slug='bangeo-hoe')""")
    def req(self,method,path,body=None):
        cn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=10)
        raw=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
        cn.request(method,path,raw,headers={"Content-Type":"application/json"})
        response=cn.getresponse()
        out=response.status,json.loads(response.read().decode())
        cn.close()
        return out
    def test_unverified_product_is_unavailable(self):
        code,p=self.req("GET","/api/v1/mobile/products/bangeo-hoe")
        self.assertEqual(code,404)
    def test_verified_detail_returns_no_checkout(self):
        self.approved()
        code,p=self.req("GET","/api/v1/mobile/products/bangeo-hoe")
        self.assertEqual(code,200)
        self.assertFalse(p["data"]["checkout_enabled"])
        self.assertEqual(p["data"]["price_krw"],55000)
    def test_quote_uses_server_prices_not_client_prices(self):
        self.approved()
        code,p=self.req("POST","/api/v1/mobile/cart/quote",{"items":[{"slug":"bangeo-hoe","qty":2,"price":1}]})
        self.assertEqual(code,200)
        self.assertEqual(p["data"]["subtotal_krw"],110000)
        self.assertIsNone(p["data"]["payable_total_krw"])
        self.assertFalse(p["data"]["checkout_enabled"])
    def test_quote_rejects_invalid_quantities(self):
        self.approved()
        for qty in (True,0,100,-1,"2",1.1):
            code,_=self.req("POST","/api/v1/mobile/cart/quote",{"items":[{"slug":"bangeo-hoe","qty":qty}]})
            self.assertEqual(code,400,str(qty))
    def test_quote_rejects_stock_and_options(self):
        self.approved()
        for item in ({"slug":"bangeo-hoe","qty":21},
                     {"slug":"bangeo-hoe","qty":1,"options":["extra"]}):
            self.assertEqual(self.req("POST","/api/v1/mobile/cart/quote",{"items":[item]})[0],400)
    def test_quote_rejects_unverified_products(self):
        self.assertEqual(self.req("POST","/api/v1/mobile/cart/quote",{"items":[{"slug":"bangeo-hoe","qty":1}]})[0],400)
    def test_quote_rejects_duplicate_product(self):
        self.approved()
        item={"slug":"bangeo-hoe","qty":1}
        self.assertEqual(self.req("POST","/api/v1/mobile/cart/quote",{"items":[item,item]})[0],400)
    def test_no_public_mobile_order_payment_path(self):
        self.approved()
        for path in ("/api/v1/mobile/orders","/api/v1/mobile/payments/confirm"):
            code,_=self.req("POST",path,{"items":[{"slug":"bangeo-hoe","qty":1}]})
            self.assertEqual(code,404)

    def test_market_and_merchants_only_verified(self):
        self.assertEqual(self.req("GET","/api/v1/mobile/markets")[1]["data"]["items"],[])
        self.approved()
        markets=self.req("GET","/api/v1/mobile/markets")[1]["data"]["items"]
        self.assertEqual(markets,[{"id":"garak","name":"가락한상 제휴 매장"}])
        self.assertEqual(len(self.req("GET","/api/v1/mobile/merchants?market_id=garak")[1]["data"]["items"]),1)
    def test_remote_shop_catalog_filters_approved(self):
        self.assertEqual(self.req("GET","/api/v1/mobile/products")[1]["data"]["items"],[])
        self.approved()
        code,r=self.req("GET","/api/v1/mobile/products?market_id=garak")
        self.assertEqual(code,200)
        products=r["data"]["items"]
        self.assertTrue(any(p["slug"]=="bangeo-hoe" for p in products))
        self.assertTrue(all(p["checkout_enabled"] is False for p in products))
    def test_market_mismatch_fails(self):
        self.approved()
        self.assertEqual(self.req("GET","/api/v1/mobile/merchants?market_id=other")[0],404)
        self.assertEqual(self.req("GET","/api/v1/mobile/products?market_id=other")[0],404)

    def test_stock_and_data_unchanged_by_quote(self):
        self.approved()
        with connect(self.db) as c:
            before=c.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0]
            orders_before=c.execute("SELECT count(*) FROM orders").fetchone()[0]
        self.req("POST","/api/v1/mobile/cart/quote",{"items":[{"slug":"bangeo-hoe","qty":2}]})
        with connect(self.db) as c:
            self.assertEqual(c.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0],before)
            self.assertEqual(c.execute("SELECT count(*) FROM orders").fetchone()[0],orders_before)
if __name__=="__main__":
    unittest.main()
