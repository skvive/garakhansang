"""Public, read-only and *verified-only* GarakHansang catalog for native apps.

Reads the SAME Neon partner release ledger as the website. It never exposes
unapproved products, candidate drafts, private merchant application data,
personal customer orders, or fabricated stock. No fallback to seeded SQLite.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import pg8000.dbapi
from contextlib import closing
from urllib.parse import urlparse
from .pgcompat import PostgresConnection
import re
from datetime import date, datetime
from urllib.parse import urlsplit

from .database import connect
from .pgcompat import use_postgres

PREFIX = "/api/mobile/v1"
MAX_RESULTS = 500

# Existing production view is the authoritative 8 merchant + 4 SKU evidence gate.
PUBLISHED_SQL = """
SELECT p.sku,p.merchant_slug,p.name,p.description,p.category_code,
       p.category_name,p.price_krw,p.stock,p.image_ref,p.updated_at
FROM garak_catalog_api.approved_products p
WHERE p.stock>0 AND p.price_krw>0 AND p.image_ref ~* '^https://'
ORDER BY p.merchant_slug,p.sku
LIMIT 501
"""

def _response(payload, status=200, *, etag=None):
    raw=json.dumps(payload,ensure_ascii=False,separators=(",",":"),default=str).encode("utf-8")
    headers={"Content-Type":"application/json; charset=utf-8",
             "Cache-Control":"no-store, max-age=0",
             "X-Content-Type-Options":"nosniff",
             "Vary":"Accept-Encoding"}
    if etag is not None:headers["ETag"]=etag
    return status,headers,raw

def _clean_text(value, limit=240):
    if not isinstance(value,str):return ""
    return "".join(ch if ch.isprintable() else " " for ch in value.strip())[:limit]

def _product(row):
    image=_clean_text(row.get("image_ref"),1200)
    u=urlsplit(image)
    if u.scheme!="https" or not u.hostname or u.username or u.password:
        return None
    price=row.get("price_krw")
    stock=row.get("stock")
    if type(price) is not int or not (0 < price < 100000001):
        return None
    if type(stock) is not int or stock<1:return None
    sku=_clean_text(row.get("sku"),100)
    merchant=_clean_text(row.get("merchant_slug"),100)
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",sku) or not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",merchant):
        return None
    return {"id":sku,"sku":sku,"merchant_id":merchant,
            "merchant_name":merchant, # No unverified business alias
            "name":_clean_text(row.get("name"),160),
            "description":_clean_text(row.get("description"),600),
            "category_id":_clean_text(row.get("category_code"),100),
            "category_name":_clean_text(row.get("category_name"),100),
            "price_krw":price,"currency":"KRW","stock":stock,
            "image_url":image, "merchant_verified":True,
            # The shared customer-order/PSP backend is NOT live.
            "can_checkout":False}

def _serialize(rows):
    if len(rows)>MAX_RESULTS:
        raise ValueError("public catalog exceeded bounded result count")
    items=[]
    for r in rows:
        item=_product(dict(r))
        if item is not None:items.append(item)
    seen=set()
    for p in items:
        key=(p["merchant_id"],p["sku"])
        if key in seen:raise ValueError("duplicate published SKU")
        seen.add(key)
    items.sort(key=lambda x:(x["merchant_id"],x["sku"]))
    merchants=[]
    for merchant in sorted({i["merchant_id"] for i in items}):
        merchants.append({"id":merchant,"name":merchant,
                          "product_count":sum(x["merchant_id"]==merchant for x in items)})
    # A publisher update becomes visible on the next GET, with a new stable ETag.
    return {"schema_version":1,"source":"verified_neon_release_ready",
            "items":items,"merchants":merchants,
            "count":len(items),"order_service_ready":False,
            "delivery_tracking_ready":False,
            "refresh_seconds":30}

def _catalog_readonly_connection():
    # Independent of any legacy admin DATABASE_URL. The DB account has
    # SELECT only on garak_catalog_api.approved_products, no user/order access.
    raw=os.environ.get("GARAK_CATALOG_DATABASE_URL","")
    u=urlparse(raw)
    if u.scheme not in ("postgres","postgresql") or not u.hostname or not u.password:
        raise ConnectionError("Isolated approved-catalog Neon URL is not configured")
    if u.username!="garak_catalog_public_ro":
        raise ConnectionError("Catalog must use verified least-privilege role")
    c=pg8000.dbapi.connect(
        host=u.hostname,port=u.port or 5432,user=u.username,
        password=u.password,database=(u.path or "/neondb").lstrip("/"),
        ssl_context=ssl.create_default_context(),timeout=12)
    return PostgresConnection(c)

def get_snapshot(connection_factory=None):
    if connection_factory is None:
        with _catalog_readonly_connection() as con:
            rows=con.execute(PUBLISHED_SQL).fetchall()
        return _serialize(rows)
    # Test injection for independent read-only integration unit tests.
    if not use_postgres():
        raise ConnectionError("Neon not configured")
    with connection_factory() as con:
        rows=con.execute(PUBLISHED_SQL).fetchall()
    return _serialize(rows)

def handle(method, path, headers, _body=b"", *, snapshot_loader=get_snapshot):
    """Owns only public catalog and explicit fail-closed order placeholders."""
    url=urlsplit(path)
    p=url.path.rstrip("/")
    h={str(k).lower():str(v) for k,v in (headers or {}).items()}
    if method!="GET":
        return _response({"error":"method_not_allowed"},405)
    if p in (PREFIX+"/orders", PREFIX+"/delivery"):
        # Real order state requires signed Neon Auth token + customer ownership
        # and an operational orders BFF. Never expose another service's orders.
        return _response({"error":"authenticated_order_api_not_ready",
                          "message":"실주문·배송 내역 연결 준비 중"},503)
    if p not in (PREFIX+"/catalog",PREFIX+"/merchants") and not re.fullmatch(
        re.escape(PREFIX)+r"/catalog/[A-Za-z0-9_-]{3,100}",p):
        return _response({"error":"not_found"},404)
    try:
        data=snapshot_loader()
    except (Exception,):  # Never leak PG host/schema/table names to clients
        return _response({"error":"catalog_unavailable","message":"상품 동기화 연결을 확인해 주세요"},503)
    if p==PREFIX+"/merchants":
        data={"schema_version":1,"merchants":data["merchants"],
              "count":len(data["merchants"]),"refresh_seconds":30}
    elif p.startswith(PREFIX+"/catalog/"):
        sku=p.rsplit("/",1)[-1]
        product=next((x for x in data["items"] if x["sku"]==sku),None)
        if product is None:return _response({"error":"product_not_available"},404)
        data={"schema_version":1,"product":product}
    raw=json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    etag='"'+hashlib.sha256(raw).hexdigest()+'"'
    if h.get("if-none-match")==etag:
        return 304,{"Cache-Control":"no-store, max-age=0","ETag":etag},b""
    return _response(data,etag=etag)
