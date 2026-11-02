-- GHO V4 isolated development branch ONLY. No real payment operation.
-- Run after 001_neon_order_schema.sql in a disposable/isolated Neon branch.
ALTER TABLE gho.markets ADD COLUMN IF NOT EXISTS base_fee_krw bigint NOT NULL DEFAULT 3900 CHECK(base_fee_krw>=0);
ALTER TABLE gho.markets ADD COLUMN IF NOT EXISTS extra_merchant_fee_krw bigint NOT NULL DEFAULT 600 CHECK(extra_merchant_fee_krw>=0);
ALTER TABLE gho.markets ADD COLUMN IF NOT EXISTS chilled_fee_krw bigint NOT NULL DEFAULT 1000 CHECK(chilled_fee_krw>=0);
ALTER TABLE gho.merchants ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT true;
ALTER TABLE gho.products ADD COLUMN IF NOT EXISTS catalog_ref text UNIQUE;
ALTER TABLE gho.products ADD COLUMN IF NOT EXISTS supports_slicing boolean NOT NULL DEFAULT false;
ALTER TABLE gho.products ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT true;
ALTER TABLE gho.checkouts ADD COLUMN IF NOT EXISTS response_snapshot jsonb;

CREATE TABLE IF NOT EXISTS gho.actor_grants (
  auth_subject text NOT NULL,
  role text NOT NULL CHECK(role IN ('admin','merchant','hub','rider')),
  market_id text REFERENCES gho.markets(id),
  merchant_id uuid REFERENCES gho.merchants(id),
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(auth_subject, role, market_id, merchant_id),
  CHECK ((role='admin' AND market_id IS NULL AND merchant_id IS NULL)
      OR (role IN ('hub','rider') AND market_id IS NOT NULL AND merchant_id IS NULL)
      OR (role='merchant' AND merchant_id IS NOT NULL))
);
-- NULLs in composite primary keys are not allowed, so use an actual surrogate key instead.
ALTER TABLE gho.actor_grants DROP CONSTRAINT IF EXISTS actor_grants_pkey;
ALTER TABLE gho.actor_grants ALTER COLUMN market_id DROP NOT NULL;
ALTER TABLE gho.actor_grants ALTER COLUMN merchant_id DROP NOT NULL;
ALTER TABLE gho.actor_grants ADD COLUMN IF NOT EXISTS id uuid DEFAULT gen_random_uuid() NOT NULL;
ALTER TABLE gho.actor_grants ADD CONSTRAINT actor_grants_pkey PRIMARY KEY(id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_gho_actor_grants_identity ON gho.actor_grants
 (auth_subject,role,coalesce(market_id,''),coalesce(merchant_id::text,''));
ALTER TABLE gho.actor_grants ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION gho.create_demo_checkout(
  p_subject text, p_idempotency_key text, p_lines jsonb
) RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
  v_digest text; v_previous record; v_item jsonb; v_product record; v_catalog_ref text;
  v_qty integer; v_proc text; v_checkout uuid; v_order uuid; v_market record;
  v_totals jsonb := '[]'::jsonb; v_shipping bigint; v_subtotal bigint;
BEGIN
  IF length(coalesce(p_subject,''))<4 OR length(p_subject)>255 THEN RAISE EXCEPTION 'invalid customer subject' USING ERRCODE='22023'; END IF;
  IF length(coalesce(p_idempotency_key,''))<8 OR length(p_idempotency_key)>128 THEN RAISE EXCEPTION 'invalid idempotency key' USING ERRCODE='22023'; END IF;
  IF jsonb_typeof(p_lines) IS DISTINCT FROM 'array' OR jsonb_array_length(p_lines) NOT BETWEEN 1 AND 80 THEN
    RAISE EXCEPTION 'invalid cart' USING ERRCODE='22023'; END IF;
  v_digest := encode(sha256(convert_to(p_lines::text,'UTF8')),'hex');
  PERFORM pg_advisory_xact_lock(hashtextextended(p_subject || ':' || p_idempotency_key,71));
  SELECT * INTO v_previous FROM gho.checkouts WHERE customer_subject=p_subject AND idempotency_key=p_idempotency_key FOR UPDATE;
  IF FOUND THEN
    IF v_previous.request_digest <> v_digest THEN RAISE EXCEPTION 'idempotency key reused with different payload' USING ERRCODE='23505'; END IF;
    RETURN v_previous.response_snapshot;
  END IF;
  CREATE TEMP TABLE IF NOT EXISTS gho_cart_v4 (
    product_id uuid NOT NULL, merchant_id uuid NOT NULL, market_id text NOT NULL,
    name_snapshot text NOT NULL, unit_price bigint NOT NULL, is_cold boolean NOT NULL,
    proc text NOT NULL, qty integer NOT NULL CHECK(qty BETWEEN 1 AND 99),
    PRIMARY KEY(product_id,proc)
  ) ON COMMIT DROP;
  TRUNCATE pg_temp.gho_cart_v4;
  FOR v_item IN SELECT value FROM jsonb_array_elements(p_lines) t(value) ORDER BY (value->>'id') LOOP
    IF jsonb_typeof(v_item) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'invalid cart row' USING ERRCODE='22023'; END IF;
    v_catalog_ref := v_item->>'id'; v_proc := coalesce(v_item->>'proc','');
    IF v_proc NOT IN ('','sliced') THEN RAISE EXCEPTION 'invalid processing option' USING ERRCODE='22023'; END IF;
    IF coalesce(v_item->>'qty','') !~ '^[1-9][0-9]?$' THEN RAISE EXCEPTION 'invalid quantity' USING ERRCODE='22023'; END IF;
    v_qty := (v_item->>'qty')::int;
    SELECT p.*, m.approval_status INTO v_product
      FROM gho.products p JOIN gho.merchants m ON m.id=p.merchant_id
      WHERE p.catalog_ref=v_catalog_ref AND p.status='active' FOR UPDATE OF p;
    IF NOT FOUND OR v_product.approval_status <> 'approved' THEN RAISE EXCEPTION 'unavailable item %',v_catalog_ref USING ERRCODE='22023'; END IF;
    IF v_proc='sliced' AND NOT v_product.supports_slicing THEN RAISE EXCEPTION 'unsupported slicing' USING ERRCODE='22023'; END IF;
    INSERT INTO pg_temp.gho_cart_v4(product_id,merchant_id,market_id,name_snapshot,unit_price,is_cold,proc,qty)
      VALUES (v_product.id,v_product.merchant_id,v_product.market_id,v_product.name,
        v_product.price_krw+CASE WHEN v_proc='sliced' THEN 3000 ELSE 0 END,
        v_product.temp_class<>'ambient',v_proc,v_qty)
      ON CONFLICT(product_id,proc) DO UPDATE SET qty=gho_cart_v4.qty+EXCLUDED.qty;
  END LOOP;
  IF EXISTS(SELECT 1 FROM pg_temp.gho_cart_v4 GROUP BY product_id,proc HAVING sum(qty)>99) THEN
    RAISE EXCEPTION 'line quantity exceeds 99' USING ERRCODE='22023'; END IF;
  IF EXISTS (SELECT 1 FROM gho.products p JOIN (SELECT product_id,sum(qty) q FROM pg_temp.gho_cart_v4 GROUP BY product_id) q
     ON q.product_id=p.id WHERE p.stock<q.q) THEN RAISE EXCEPTION 'insufficient stock' USING ERRCODE='23514'; END IF;
  INSERT INTO gho.checkouts(customer_subject,idempotency_key,request_digest)
    VALUES(p_subject,p_idempotency_key,v_digest) RETURNING id INTO v_checkout;
  FOR v_market IN SELECT market_id, sum(unit_price*qty) AS subtotal, count(DISTINCT merchant_id) AS store_count,
        bool_or(is_cold) AS cold_needed FROM pg_temp.gho_cart_v4 GROUP BY market_id ORDER BY market_id LOOP
    v_subtotal := v_market.subtotal;
    SELECT base_fee_krw + (v_market.store_count-1)*extra_merchant_fee_krw
        + CASE WHEN v_market.cold_needed THEN chilled_fee_krw ELSE 0 END INTO v_shipping
      FROM gho.markets WHERE id=v_market.market_id;
    INSERT INTO gho.orders(checkout_id,market_id,customer_subject,goods_krw,shipping_krw,discount_krw,total_krw,state)
      VALUES(v_checkout,v_market.market_id,p_subject,v_subtotal,v_shipping,0,v_subtotal+v_shipping,'created')
      RETURNING id INTO v_order;
    INSERT INTO gho.order_lines(order_id,market_id,merchant_id,product_id,name_snapshot,options_snapshot,unit_price_krw,qty)
      SELECT v_order,market_id,merchant_id,product_id,name_snapshot,jsonb_build_object('processing',proc),unit_price,qty
      FROM pg_temp.gho_cart_v4 WHERE market_id=v_market.market_id;
    INSERT INTO gho.merchant_fulfillments(order_id,merchant_id)
      SELECT v_order,merchant_id FROM pg_temp.gho_cart_v4 WHERE market_id=v_market.market_id GROUP BY merchant_id;
    v_totals := v_totals || jsonb_build_array(jsonb_build_object('id',v_order,'market_id',v_market.market_id,
      'goods_krw',v_subtotal,'shipping_krw',v_shipping,'discount_krw',0,'total_krw',v_subtotal+v_shipping,'state','created'));
  END LOOP;
  UPDATE gho.products SET stock=stock-q.q, inventory_version=inventory_version+1,updated_at=now()
    FROM (SELECT product_id,sum(qty) q FROM pg_temp.gho_cart_v4 GROUP BY product_id) q WHERE id=q.product_id;
  UPDATE gho.checkouts SET response_snapshot=jsonb_build_object('demo',true,'checkout_id',v_checkout,'orders',v_totals)
    WHERE id=v_checkout;
  INSERT INTO gho.audit_events(actor_subject,actor_role,entity_type,entity_id,action)
    VALUES(p_subject,'customer','checkout',v_checkout::text,'demo_order_created');
  RETURN jsonb_build_object('demo',true,'checkout_id',v_checkout,'orders',v_totals);
END $$;

CREATE OR REPLACE FUNCTION gho.cancel_demo_order(p_subject text,p_order uuid)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE v_order record;
BEGIN
 SELECT * INTO v_order FROM gho.orders WHERE id=p_order AND customer_subject=p_subject FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'order not found for customer' USING ERRCODE='42501'; END IF;
 IF v_order.state NOT IN ('created','authorized') THEN RAISE EXCEPTION 'cannot cancel current order state' USING ERRCODE='23514'; END IF;
 UPDATE gho.products p SET stock=stock+x.q,inventory_version=inventory_version+1,updated_at=now()
  FROM (SELECT product_id,sum(qty) q FROM gho.order_lines WHERE order_id=p_order GROUP BY product_id) x
  WHERE p.id=x.product_id;
 UPDATE gho.orders SET state='cancelled',updated_at=now() WHERE id=p_order;
 UPDATE gho.merchant_fulfillments SET state='cancelled',updated_at=now() WHERE order_id=p_order;
 INSERT INTO gho.audit_events(actor_subject,actor_role,entity_type,entity_id,action)
  VALUES(p_subject,'customer','order',p_order::text,'demo_order_cancelled');
 RETURN jsonb_build_object('demo',true,'order_id',p_order,'state','cancelled');
END $$;
