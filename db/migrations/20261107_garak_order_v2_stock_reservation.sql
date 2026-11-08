-- Order V2: atomic stock hold. Staging Neon branch only; callable by trusted server DB owner.
-- Application must verify Neon Auth token and encrypt delivery address before calling.
-- The SQL function is NOT a public RPC or user-authenticated endpoint.
ALTER TABLE garak_order_v2.orders ADD COLUMN IF NOT EXISTS request_hash text;

CREATE TABLE IF NOT EXISTS garak_order_v2.inventory_holds (
  order_id uuid NOT NULL REFERENCES garak_order_v2.orders(id),
  product_id uuid NOT NULL REFERENCES garak_order_v2.products(id),
  quantity integer NOT NULL CHECK(quantity BETWEEN 1 AND 99),
  state text NOT NULL DEFAULT 'held' CHECK(state IN ('held','consumed','released')),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(order_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_go_v2_holds_expiry
  ON garak_order_v2.inventory_holds(expires_at) WHERE state='held';
ALTER TABLE garak_order_v2.inventory_holds ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON garak_order_v2.inventory_holds FROM PUBLIC, authenticated, anonymous;

CREATE OR REPLACE FUNCTION garak_order_v2.reserve_trusted_order(
  p_auth_sub text,
  p_merchant_id uuid,
  p_zone_id uuid,
  p_items jsonb,
  p_idempotency text,
  p_encrypted_address bytea
)
RETURNS TABLE(confirmed_order_id uuid, total_due_krw integer, idempotent_reuse boolean)
LANGUAGE plpgsql SECURITY INVOKER
SET search_path=pg_catalog,garak_order_v2
AS $BODY$
DECLARE
  v_product RECORD;
  v_line RECORD;
  v_zone RECORD;
  v_existing RECORD;
  v_order uuid;
  v_requested_hash text;
  v_subtotal bigint := 0;
  v_due bigint := 0;
  v_lines integer;
  v_locked integer;
BEGIN
  IF p_auth_sub IS NULL OR length(p_auth_sub)<3 OR length(p_auth_sub)>128
     OR p_idempotency !~ '^[a-zA-Z0-9_-]{12,128}$'
     OR p_merchant_id IS NULL OR p_zone_id IS NULL THEN
     RAISE EXCEPTION 'invalid authenticated order identity';
  END IF;
  IF p_encrypted_address IS NULL OR octet_length(p_encrypted_address)<32
     OR octet_length(p_encrypted_address)>4096 THEN
     RAISE EXCEPTION 'delivery address must be application-encrypted';
  END IF;
  IF p_items IS NULL OR jsonb_typeof(p_items)<>'array' THEN
     RAISE EXCEPTION 'invalid cart';
  END IF;
  v_lines := jsonb_array_length(p_items);
  IF v_lines<1 OR v_lines>30 THEN RAISE EXCEPTION 'cart size invalid'; END IF;
  IF EXISTS(
      SELECT 1 FROM jsonb_to_recordset(p_items)
        AS item(product_id uuid,qty integer)
      WHERE item.product_id IS NULL OR item.qty IS NULL OR item.qty NOT BETWEEN 1 AND 99
  ) THEN RAISE EXCEPTION 'invalid cart quantity or SKU'; END IF;
  IF (
    SELECT count(DISTINCT product_id) FROM jsonb_to_recordset(p_items)
      AS item(product_id uuid,qty integer)
    ) <> v_lines THEN
     RAISE EXCEPTION 'duplicate product in cart';
  END IF;

  v_requested_hash := md5(p_items::text||':'||p_merchant_id::text||':'||p_zone_id::text);
  -- Same customer/idempotency key is serialized across concurrent requests.
  PERFORM pg_advisory_xact_lock(hashtext(p_auth_sub||':'||p_idempotency)::bigint);
  SELECT o.id,o.total_krw,o.request_hash INTO v_existing
  FROM garak_order_v2.orders o
  WHERE o.customer_auth_sub=p_auth_sub AND o.idempotency_key=p_idempotency;
  IF FOUND THEN
     IF v_existing.request_hash IS DISTINCT FROM v_requested_hash THEN
        RAISE EXCEPTION 'idempotency key reused for a different cart';
     END IF;
     RETURN QUERY SELECT v_existing.id, v_existing.total_krw, true;
     RETURN;
  END IF;

  SELECT z.fee_krw,z.min_order_krw INTO v_zone
  FROM garak_order_v2.delivery_zones z
  JOIN garak_order_v2.merchants m ON m.id=z.merchant_id
  WHERE z.id=p_zone_id AND z.merchant_id=p_merchant_id AND z.available=true
    AND m.status='approved' AND m.business_verified=true;
  IF NOT FOUND THEN RAISE EXCEPTION 'merchant or delivery zone not approved'; END IF;

  -- Deterministic product row lock order prevents oversell and reduces deadlocks.
  FOR v_line IN
      SELECT product_id,qty FROM jsonb_to_recordset(p_items)
        AS item(product_id uuid,qty integer)
      ORDER BY product_id
  LOOP
     SELECT p.* INTO v_product FROM garak_order_v2.products p
     WHERE p.id=v_line.product_id AND p.merchant_id=p_merchant_id
        AND p.publication='approved' FOR UPDATE;
     IF NOT FOUND OR v_product.stock<v_line.qty
        OR v_product.price_krw<1 OR length(trim(v_product.origin))<1
        OR v_product.image_key IS NULL THEN
        RAISE EXCEPTION 'unapproved or insufficiently stocked item';
     END IF;
     IF EXISTS(
        SELECT 1 FROM garak_order_v2.product_options opt
        WHERE opt.product_id=v_product.id AND opt.active AND opt.is_required
     ) THEN RAISE EXCEPTION 'required options must be configured before checkout'; END IF;
     v_subtotal:=v_subtotal+v_product.price_krw::bigint*v_line.qty;
     IF v_subtotal>100000000 THEN RAISE EXCEPTION 'cart maximum exceeded'; END IF;
  END LOOP;

  IF v_subtotal<v_zone.min_order_krw THEN RAISE EXCEPTION 'minimum order unmet'; END IF;
  v_due:=v_subtotal+v_zone.fee_krw;
  IF v_due>100000000 THEN RAISE EXCEPTION 'payable amount exceeds cap'; END IF;

  INSERT INTO garak_order_v2.orders
     (merchant_id,customer_auth_sub,idempotency_key,request_hash,delivery_zone_id,
      subtotal_krw,delivery_fee_krw,total_krw,encrypted_delivery_address)
  VALUES(p_merchant_id,p_auth_sub,p_idempotency,v_requested_hash,p_zone_id,
         v_subtotal::integer,v_zone.fee_krw,v_due::integer,p_encrypted_address)
  RETURNING id INTO v_order;

  FOR v_line IN
      SELECT product_id,qty FROM jsonb_to_recordset(p_items)
        AS item(product_id uuid,qty integer)
      ORDER BY product_id
  LOOP
     SELECT p.* INTO v_product FROM garak_order_v2.products p
       WHERE p.id=v_line.product_id AND p.merchant_id=p_merchant_id;
     UPDATE garak_order_v2.products p
         SET stock=stock-v_line.qty WHERE p.id=v_product.id
           AND p.stock>=v_line.qty;
     GET DIAGNOSTICS v_locked=ROW_COUNT;
     IF v_locked<>1 THEN RAISE EXCEPTION 'inventory modified concurrently'; END IF;
     INSERT INTO garak_order_v2.order_lines
       (order_id,product_id,name_snapshot,origin_snapshot,allergen_snapshot,
        qty,unit_price_krw,line_total_krw)
     VALUES(v_order,v_product.id,v_product.name,v_product.origin,
        v_product.allergen_codes,v_line.qty,v_product.price_krw,
        v_product.price_krw*v_line.qty);
     INSERT INTO garak_order_v2.inventory_holds
       (order_id,product_id,quantity,expires_at)
     VALUES(v_order,v_product.id,v_line.qty,now()+INTERVAL '30 minutes');
  END LOOP;

  RETURN QUERY SELECT v_order,v_due::integer,false;
END;
$BODY$;

REVOKE ALL ON FUNCTION garak_order_v2.reserve_trusted_order(
 text,uuid,uuid,jsonb,text,bytea) FROM PUBLIC,anonymous,authenticated;
