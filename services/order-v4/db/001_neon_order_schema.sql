-- Garak Hansang Order / PostgreSQL 16+ and Neon
-- DESIGN-ONLY MIGRATION. NOT APPLIED TO ANY LIVE PROJECT.
-- Authentication and grants must be configured BEFORE deploying any HTTP API.
-- This schema intentionally uses a namespaced schema to avoid changing existing public tables.
CREATE SCHEMA IF NOT EXISTS gho;
CREATE TABLE IF NOT EXISTS gho.markets (
  id text PRIMARY KEY, name text NOT NULL, region_code text NOT NULL,
  service_status text NOT NULL DEFAULT 'pilot' CHECK(service_status IN ('pilot','active','paused')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS gho.merchants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  market_id text NOT NULL REFERENCES gho.markets(id),
  business_name text NOT NULL, approval_status text NOT NULL DEFAULT 'pending'
  CHECK(approval_status IN ('pending','approved','rejected','suspended')),
  business_verification_ref text, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(id,market_id)
);
CREATE TABLE IF NOT EXISTS gho.merchant_members (
  merchant_id uuid NOT NULL REFERENCES gho.merchants(id),
  auth_subject text NOT NULL, member_role text NOT NULL CHECK(member_role IN ('owner','staff')),
  PRIMARY KEY(merchant_id,auth_subject)
);
CREATE TABLE IF NOT EXISTS gho.products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), merchant_id uuid NOT NULL REFERENCES gho.merchants(id),
  market_id text NOT NULL REFERENCES gho.markets(id),
  name text NOT NULL, price_krw bigint NOT NULL CHECK(price_krw>=0),
  stock integer NOT NULL DEFAULT 0 CHECK(stock>=0),
  temp_class text NOT NULL DEFAULT 'ambient' CHECK(temp_class IN ('ambient','chilled','frozen')),
  inventory_version bigint NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','paused')),
  updated_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (merchant_id,market_id) REFERENCES gho.merchants(id,market_id),
  UNIQUE(id,market_id,merchant_id)
);
CREATE TABLE IF NOT EXISTS gho.checkouts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), customer_subject text NOT NULL,
  idempotency_key text NOT NULL,
  request_digest char(64) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(customer_subject,idempotency_key)
);
CREATE TABLE IF NOT EXISTS gho.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  checkout_id uuid NOT NULL REFERENCES gho.checkouts(id),
  market_id text NOT NULL REFERENCES gho.markets(id),
  customer_subject text NOT NULL,
  goods_krw bigint NOT NULL CHECK(goods_krw>=0),
  shipping_krw bigint NOT NULL CHECK(shipping_krw>=0),
  discount_krw bigint NOT NULL CHECK(discount_krw>=0),
  total_krw bigint NOT NULL CHECK(total_krw=goods_krw+shipping_krw-discount_krw AND total_krw>=0),
  state text NOT NULL DEFAULT 'created' CHECK(state IN
   ('created','authorized','paid','picking','hub_ready','assigned','picked_up','delivered','cancel_pending','cancelled','refunded')),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(id,market_id)
);
CREATE TABLE IF NOT EXISTS gho.order_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL, market_id text NOT NULL, merchant_id uuid NOT NULL,
  product_id uuid NOT NULL, name_snapshot text NOT NULL, options_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  unit_price_krw bigint NOT NULL CHECK(unit_price_krw>=0), qty integer NOT NULL CHECK(qty BETWEEN 1 AND 99),
  FOREIGN KEY (order_id,market_id) REFERENCES gho.orders(id,market_id),
  FOREIGN KEY (product_id,market_id,merchant_id) REFERENCES gho.products(id,market_id,merchant_id)
);
CREATE TABLE IF NOT EXISTS gho.merchant_fulfillments (
  order_id uuid NOT NULL REFERENCES gho.orders(id), merchant_id uuid NOT NULL REFERENCES gho.merchants(id),
  state text NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','ready','handed_off','cancelled')),
  updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(order_id,merchant_id)
);
CREATE TABLE IF NOT EXISTS gho.dispatch_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), order_id uuid NOT NULL UNIQUE REFERENCES gho.orders(id),
  market_id text NOT NULL REFERENCES gho.markets(id),
  rider_subject text, temp_class text NOT NULL DEFAULT 'ambient'
     CHECK(temp_class IN ('ambient','chilled','frozen','mixed_segregated')),
  state text NOT NULL DEFAULT 'waiting' CHECK(state IN ('waiting','assigned','picked_up','delivered','failed')),
  assigned_at timestamptz, completed_at timestamptz
);
CREATE TABLE IF NOT EXISTS gho.payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), checkout_id uuid NOT NULL REFERENCES gho.checkouts(id),
  provider text NOT NULL, external_payment_ref text UNIQUE,
  amount_krw bigint NOT NULL CHECK(amount_krw>=0),
  state text NOT NULL CHECK(state IN ('initialized','authorized','paid','void','refunded','failed')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS gho.payment_webhooks (
  provider text NOT NULL, event_id text NOT NULL,
  payload_sha256 char(64) NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
  verified boolean NOT NULL DEFAULT false,
  PRIMARY KEY(provider,event_id)
);
CREATE TABLE IF NOT EXISTS gho.coupons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE, market_id text REFERENCES gho.markets(id),
  discount_kind text NOT NULL CHECK(discount_kind IN ('fixed','percentage','delivery')),
  discount_amount bigint NOT NULL CHECK(discount_amount>=0),
  min_goods_krw bigint NOT NULL DEFAULT 0 CHECK(min_goods_krw>=0),
  budget_krw bigint NOT NULL DEFAULT 0 CHECK(budget_krw>=0),
  redeemed_krw bigint NOT NULL DEFAULT 0 CHECK(redeemed_krw>=0),
  valid_from timestamptz NOT NULL, valid_until timestamptz NOT NULL,
  CHECK(valid_until>valid_from)
);
CREATE TABLE IF NOT EXISTS gho.coupon_redemptions (
  coupon_id uuid NOT NULL REFERENCES gho.coupons(id),
  checkout_id uuid NOT NULL REFERENCES gho.checkouts(id),
  customer_subject text NOT NULL, order_id uuid NOT NULL REFERENCES gho.orders(id),
  amount_krw bigint NOT NULL CHECK(amount_krw>=0),
  PRIMARY KEY(coupon_id,checkout_id)
);
CREATE TABLE IF NOT EXISTS gho.audit_events (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  actor_subject text, actor_role text NOT NULL, entity_type text NOT NULL,
  entity_id text NOT NULL, action text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_gho_orders_market_created ON gho.orders(market_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gho_orders_customer ON gho.orders(customer_subject,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gho_products_merchant_status ON gho.products(merchant_id,status);
CREATE INDEX IF NOT EXISTS idx_gho_fulfillments_merchant ON gho.merchant_fulfillments(merchant_id,state);
CREATE INDEX IF NOT EXISTS idx_gho_audit_entity ON gho.audit_events(entity_type,entity_id,occurred_at DESC);
-- These tables are server-only, not directly exposed to browsers.
-- RLS is on by default with NO end-user policies, so ordinary non-owner roles cannot access rows.
ALTER TABLE gho.merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.merchant_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.checkouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.order_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.merchant_fulfillments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.dispatch_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.payment_webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.coupon_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE gho.audit_events ENABLE ROW LEVEL SECURITY;
-- RLS does NOT stop owners/superusers/BYPASSRLS roles. Grant only least privileges
-- to a dedicated server runtime DB role after confirming Neon branch role privileges.
-- No GRANT statements or credentials supplied in this migration.
