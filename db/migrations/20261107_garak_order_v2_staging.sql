-- GarakHansang Order V2 / staging only. NOT a production migration.
-- RLS is enabled but access policies require verified Neon Auth / Data API; NO grants to public.
-- Stripe payment_attempts CHECK(livemode=false); test-only until real PG legal/merchant approvals.
-- Apply only to isolated Neon development branch.

CREATE SCHEMA IF NOT EXISTS garak_order_v2;

CREATE TABLE IF NOT EXISTS garak_order_v2.merchants(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','suspended','rejected')),
 business_verified boolean NOT NULL DEFAULT false, commission_bps integer NOT NULL DEFAULT 800 CHECK(commission_bps BETWEEN 0 AND 4000),
 created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS garak_order_v2.merchant_memberships(
 merchant_id uuid NOT NULL REFERENCES garak_order_v2.merchants(id),
 auth_sub text NOT NULL, role text NOT NULL CHECK(role IN ('owner','staff')),
 active boolean NOT NULL DEFAULT true, PRIMARY KEY(merchant_id,auth_sub));

CREATE TABLE IF NOT EXISTS garak_order_v2.riders(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), auth_sub text NOT NULL UNIQUE,
 approved boolean NOT NULL DEFAULT false, on_duty boolean NOT NULL DEFAULT false,
 vehicle text NOT NULL DEFAULT 'bicycle' CHECK(vehicle IN ('bicycle','motorcycle','car','walk')),
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(approved OR NOT on_duty));

CREATE TABLE IF NOT EXISTS garak_order_v2.merchant_applications(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), merchant_id uuid UNIQUE REFERENCES garak_order_v2.merchants(id),
 submitted_by text NOT NULL, evidence_storage_key text, status text NOT NULL DEFAULT 'submitted'
 CHECK(status IN ('submitted','review','approved','rejected')),
 reviewed_by text, reviewed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS garak_order_v2.products(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), merchant_id uuid NOT NULL REFERENCES garak_order_v2.merchants(id),
 slug text NOT NULL CHECK(length(slug) BETWEEN 1 AND 80), name text NOT NULL, description text NOT NULL DEFAULT '',
 category text NOT NULL DEFAULT '', price_krw integer NOT NULL CHECK(price_krw > 0),
 stock integer NOT NULL DEFAULT 0 CHECK(stock >= 0),
 origin text NOT NULL DEFAULT '', allergen_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
 image_key text, publication text NOT NULL DEFAULT 'draft'
 CHECK(publication IN ('draft','review','approved','hidden')),
 approved_by text, approved_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(merchant_id,slug));

CREATE TABLE IF NOT EXISTS garak_order_v2.product_options(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), product_id uuid NOT NULL REFERENCES garak_order_v2.products(id),
 group_name text NOT NULL, option_name text NOT NULL,
 price_delta_krw integer NOT NULL DEFAULT 0, stock integer NOT NULL DEFAULT 0 CHECK(stock >= 0),
 is_required boolean NOT NULL DEFAULT false, active boolean NOT NULL DEFAULT true,
 UNIQUE(product_id,group_name,option_name));

CREATE TABLE IF NOT EXISTS garak_order_v2.delivery_zones(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), merchant_id uuid NOT NULL REFERENCES garak_order_v2.merchants(id),
 zone_code text NOT NULL, fee_krw integer NOT NULL CHECK(fee_krw >= 0),
 min_order_krw integer NOT NULL DEFAULT 0 CHECK(min_order_krw >= 0),
 max_distance_m integer CHECK(max_distance_m > 0),
 available boolean NOT NULL DEFAULT false, UNIQUE(merchant_id,zone_code));

CREATE TABLE IF NOT EXISTS garak_order_v2.orders(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), merchant_id uuid NOT NULL REFERENCES garak_order_v2.merchants(id),
 customer_auth_sub text NOT NULL, idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 12 AND 128),
 delivery_zone_id uuid NOT NULL REFERENCES garak_order_v2.delivery_zones(id),
 currency char(3) NOT NULL DEFAULT 'KRW' CHECK(currency='KRW'),
 subtotal_krw integer NOT NULL CHECK(subtotal_krw>0),
 delivery_fee_krw integer NOT NULL CHECK(delivery_fee_krw>=0),
 discount_krw integer NOT NULL DEFAULT 0 CHECK(discount_krw>=0),
 total_krw integer NOT NULL CHECK(total_krw>0 AND total_krw=subtotal_krw+delivery_fee_krw-discount_krw),
 state text NOT NULL DEFAULT 'payment_pending' CHECK(state IN
 ('payment_pending','paid','merchant_accepted','preparing','ready_for_pickup','dispatch_requested',
  'rider_assigned','picked_up','in_transit','delivered','refund_pending','refunded','canceled')),
 version integer NOT NULL DEFAULT 0 CHECK(version>=0),
 encrypted_delivery_address bytea,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(customer_auth_sub,idempotency_key));

CREATE TABLE IF NOT EXISTS garak_order_v2.order_lines(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), order_id uuid NOT NULL REFERENCES garak_order_v2.orders(id),
 product_id uuid NOT NULL REFERENCES garak_order_v2.products(id),
 name_snapshot text NOT NULL, origin_snapshot text NOT NULL, allergen_snapshot jsonb NOT NULL DEFAULT '[]'::jsonb,
 option_snapshot jsonb NOT NULL DEFAULT '[]'::jsonb,
 qty integer NOT NULL CHECK(qty BETWEEN 1 AND 99),
 unit_price_krw integer NOT NULL CHECK(unit_price_krw>0),
 line_total_krw integer NOT NULL CHECK(line_total_krw=qty*unit_price_krw));

CREATE TABLE IF NOT EXISTS garak_order_v2.payment_attempts(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 order_id uuid NOT NULL REFERENCES garak_order_v2.orders(id),
 provider text NOT NULL DEFAULT 'stripe' CHECK(provider IN ('stripe','toss')),
 provider_checkout_id text UNIQUE, amount_krw integer NOT NULL CHECK(amount_krw>0),
 currency char(3) NOT NULL DEFAULT 'KRW' CHECK(currency='KRW'),
 livemode boolean NOT NULL DEFAULT false CHECK(livemode=false),
 state text NOT NULL DEFAULT 'pending'
 CHECK(state IN ('pending','paid','failed','refund_pending','refunded')),
 created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS garak_order_v2.payment_events(
 event_id text PRIMARY KEY, order_id uuid NOT NULL REFERENCES garak_order_v2.orders(id),
 provider text NOT NULL, event_kind text NOT NULL, signature_checked boolean NOT NULL CHECK(signature_checked=true),
 amount_krw integer, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS garak_order_v2.deliveries(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),order_id uuid NOT NULL UNIQUE REFERENCES garak_order_v2.orders(id),
 rider_id uuid REFERENCES garak_order_v2.riders(id),
 state text NOT NULL DEFAULT 'dispatch_requested'
 CHECK(state IN ('dispatch_requested','rider_assigned','picked_up','in_transit','delivered','failed','cancelled')),
 version integer NOT NULL DEFAULT 0 CHECK(version>=0),
 deadline_at timestamptz, accepted_at timestamptz, delivered_at timestamptz);

CREATE TABLE IF NOT EXISTS garak_order_v2.notification_outbox(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), order_id uuid NOT NULL REFERENCES garak_order_v2.orders(id),
 event text NOT NULL, recipient_role text NOT NULL CHECK(recipient_role IN ('customer','merchant','rider','ops')),
 recipient_subject text NOT NULL, order_version integer NOT NULL,
 payload jsonb NOT NULL DEFAULT '{}'::jsonb,
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0),
 next_attempt_at timestamptz NOT NULL DEFAULT now(),
 dispatched_at timestamptz, last_error text,
 UNIQUE(order_id,event,recipient_role,recipient_subject,order_version));

CREATE TABLE IF NOT EXISTS garak_order_v2.refund_requests(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), order_id uuid NOT NULL REFERENCES garak_order_v2.orders(id),
 requested_by text NOT NULL, reason text NOT NULL DEFAULT '',
 amount_krw integer NOT NULL CHECK(amount_krw>0),
 state text NOT NULL DEFAULT 'review' CHECK(state IN ('review','approved','provider_pending','verified','rejected')),
 provider_refund_id text UNIQUE, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS garak_order_v2.settlements(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),order_id uuid NOT NULL UNIQUE REFERENCES garak_order_v2.orders(id),
 merchant_id uuid NOT NULL REFERENCES garak_order_v2.merchants(id),
 gross_krw integer NOT NULL CHECK(gross_krw>0),
 commission_krw integer NOT NULL CHECK(commission_krw>=0),
 merchant_due_krw integer NOT NULL CHECK(merchant_due_krw=gross_krw-commission_krw),
 state text NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','review','approved','paid')),
 created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS garak_order_v2.audit_events(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_subject text, role text NOT NULL,
 action text NOT NULL, object_type text NOT NULL, object_id text NOT NULL,
 metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now());

CREATE INDEX IF NOT EXISTS idx_go_v2_orders_merchant ON garak_order_v2.orders(merchant_id,created_at DESC);

CREATE INDEX IF NOT EXISTS idx_go_v2_orders_customer ON garak_order_v2.orders(customer_auth_sub,created_at DESC);

CREATE INDEX IF NOT EXISTS idx_go_v2_delivery_state ON garak_order_v2.deliveries(state,deadline_at);

CREATE INDEX IF NOT EXISTS idx_go_v2_outbox_due ON garak_order_v2.notification_outbox(next_attempt_at) WHERE dispatched_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_go_v2_products_approved ON garak_order_v2.products(merchant_id,publication);

REVOKE ALL ON SCHEMA garak_order_v2 FROM PUBLIC;

REVOKE ALL ON ALL TABLES IN SCHEMA garak_order_v2 FROM PUBLIC;

ALTER TABLE garak_order_v2.orders ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.order_lines ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.products ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.merchant_memberships ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.riders ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.deliveries ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.settlements ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.notification_outbox ENABLE ROW LEVEL SECURITY;
