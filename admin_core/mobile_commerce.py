"""Read-only, fail-closed mobile product and quote adapter for GARAK sandbox.
This is NOT a payment, inventory reservation, or sellable order service.
No DB schema changes; products and prices are read from the existing trusted catalog.
"""
from __future__ import annotations
import re

SLUG=re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")

def _available(con,slug):
    if not isinstance(slug,str) or not SLUG.fullmatch(slug):
        raise ValueError("invalid product slug")
    row=con.execute("""
        SELECT p.slug,p.name,p.category,p.price,p.stock,p.image,p.origin,
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
    return {
        "id":p["slug"],"name":p["name"],"merchant_id":p["merchant_id"],
        "merchant_name":p["merchant"],"category":p["category"],
        "price_krw":p["price"],"stock":p["stock"],
        "image":p["image"],"origin":p["origin"],
        "option_groups":[],"price_source":"server_catalog",
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
        if entry.get("options",[])!=[]:
            raise ValueError("options are not yet approved by the server")
        product=_available(con,slug)
        if product is None:raise ValueError("unapproved or unavailable product")
        if qty>product["stock"]:raise ValueError("insufficient available stock")
        if owner is None:owner=product["merchant_id"]
        if owner!=product["merchant_id"]:
            raise ValueError("multi-merchant checkout is not configured")
        unit=product["price"]
        if isinstance(unit,bool) or not isinstance(unit,int) or unit<=0:
            raise ValueError("product price has not been approved")
        line=unit*qty
        total+=line
        if total>100_000_000:raise ValueError("quote exceeds sandbox cap")
        out.append({"slug":slug,"qty":qty,"name":product["name"],
                    "unit_price_krw":unit,"line_total_krw":line})
    return {
        "mode":"LOCAL_BETA","items":out,"merchant_id":owner,
        "subtotal_krw":total,"delivery_fee_krw":None,
        "discount_krw":None,"payable_total_krw":None,
        "checkout_enabled":False,
        "reason":"Delivery zone, final fees, stock reservation and PG are not verified",
        "source":"server_catalog","currency":"KRW",
    }
