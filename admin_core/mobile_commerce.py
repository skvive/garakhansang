"""Read-only, fail-closed mobile product and quote adapter for GARAK sandbox.
This is NOT a payment, inventory reservation, or sellable order service.
Options are stored as approved versioned records; quote prices are always server-computed.
"""
from __future__ import annotations
import re
from .product_options import approved_options,price_options

SLUG=re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")

def _available(con,slug):
    if not isinstance(slug,str) or not SLUG.fullmatch(slug):
        raise ValueError("invalid product slug")
    row=con.execute("""
        SELECT p.id AS product_id,p.slug,p.name,p.category,p.price,p.stock,p.image,p.origin,
               p.merchant_id,m.name merchant
        FROM products p JOIN merchants m ON m.id=p.merchant_id
        WHERE p.slug=? AND p.status='published'
              AND m.status='active' AND m.verified=1
        LIMIT 1
    """,(slug,)).fetchone()
    return dict(row) if row else None

def public_product(con,slug):
    p=_available(con,slug)
    if p is None:raise LookupError("not approved or unavailable")
    option_version, option_groups = approved_options(con,p["product_id"])
    return {
        "id":p["slug"],"name":p["name"],"merchant_id":p["merchant_id"],
        "merchant_name":p["merchant"],"category":p["category"],
        "price_krw":p["price"],"stock":p["stock"],
        "image":p["image"],"origin":p["origin"],
        "option_groups":option_groups,"options_version":option_version,
        "price_source":"server_catalog",
        "image_is_concept":True,"checkout_enabled":False,
    }

def quote_cart(con,request):
    if not isinstance(request,dict):raise ValueError("request must be an object")
    items=request.get("items")
    if not isinstance(items,list) or not 1<=len(items)<=30:
        raise ValueError("cart requires 1 to 30 lines")
    if request.get("delivery_type","delivery") not in ("delivery","pickup"):
        raise ValueError("unsupported fulfillment mode")
    seen=set();out=[];total=0;owner=None
    for entry in items:
        if not isinstance(entry,dict):raise ValueError("invalid cart item")
        slug=entry.get("slug");qty=entry.get("qty")
        if isinstance(qty,bool) or not isinstance(qty,int) or not 1<=qty<=99:
            raise ValueError("quantity must be integer 1..99")
        if not isinstance(slug,str) or slug in seen:
            raise ValueError("duplicate or invalid slug")
        seen.add(slug)
        product=_available(con,slug)
        if product is None:raise ValueError("unapproved or unavailable product")
        if qty>product["stock"]:raise ValueError("insufficient available stock")
        if owner is None:owner=product["merchant_id"]
        if owner!=product["merchant_id"]:
            raise ValueError("multi-merchant checkout is not configured")
        unit=product["price"]
        if isinstance(unit,bool) or not isinstance(unit,int) or unit<=0:
            raise ValueError("product price has not been approved")
        option_delta, selected, option_version = price_options(
            con,product["product_id"],entry.get("options",[]),qty)
        final_unit=unit+option_delta
        line=final_unit*qty
        total+=line
        if total>100_000_000:raise ValueError("quote exceeds sandbox cap")
        out.append({"slug":slug,"qty":qty,"name":product["name"],
                    "base_unit_price_krw":unit,
                    "option_unit_price_krw":option_delta,
                    "unit_price_krw":final_unit,
                    "line_total_krw":line,
                    "options_version":option_version,
                    "selected_options":selected})
    return {
        "mode":"LOCAL_BETA","items":out,"merchant_id":owner,
        "subtotal_krw":total,"delivery_fee_krw":None,
        "discount_krw":None,"payable_total_krw":None,
        "checkout_enabled":False,
        "reason":"Delivery zone, final fees, stock reservation and PG are not verified",
        "source":"server_catalog","currency":"KRW",
    }

def verified_merchants(con):
    rows=con.execute("""
        SELECT m.id,m.name,
          (SELECT COUNT(*) FROM products p WHERE p.merchant_id=m.id
           AND p.status='published') AS product_count
        FROM merchants m WHERE m.status='active' AND m.verified=1
        ORDER BY m.id LIMIT 100
    """).fetchall()
    return [{"id":str(x["id"]),"name":x["name"],"product_count":x["product_count"],
             "checkout_enabled":False} for x in rows]

def list_verified_products(con,merchant_name=None):
    if merchant_name is not None and (not isinstance(merchant_name,str)
           or not 1<=len(merchant_name)<=90
           or any(ord(c)<32 for c in merchant_name)):
        raise ValueError("invalid merchant filter")
    sql="""
      SELECT p.slug,p.name,p.category,p.price,p.stock,p.image,p.origin,
             p.merchant_id,m.name merchant
      FROM products p JOIN merchants m ON m.id=p.merchant_id
      WHERE p.status='published' AND m.status='active' AND m.verified=1
    """
    params=[]
    if merchant_name is not None:
        sql+=" AND m.name=?"
        params.append(merchant_name)
    sql+=" ORDER BY p.id LIMIT 100"
    rows=con.execute(sql,params).fetchall()
    return [{"id":x["slug"],"slug":x["slug"],"name":x["name"],
             "category":x["category"],"merchant":x["merchant"],
             "price_krw":x["price"],"stock":x["stock"],"origin":x["origin"],
             "image":x["image"],"checkout_enabled":False,
             "image_is_concept":True} for x in rows]
