-- Proposed production PostgreSQL architecture; NOT applied to any live Neon instance.
-- This version isolates add-on domains in garak_ops and does NOT overwrite
-- existing Next.js storefront tables. Existing products/orders/users are
-- canonical and joined by explicitly verified external IDs during migration.
BEGIN;
CREATE SCHEMA IF NOT EXISTS garak_ops;
CREATE TABLE IF NOT EXISTS garak_ops.admin_members(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),auth_user_id text NOT NULL UNIQUE,
  role text NOT NULL CHECK(role IN ('superadmin','ops','content','finance','support')),
  enabled boolean NOT NULL DEFAULT true,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.merchants(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),legal_name text NOT NULL,
  business_registration_hash text UNIQUE,verification_status text NOT NULL DEFAULT 'pending'
    CHECK(verification_status IN ('pending','verified','rejected')),
  payout_account_token text,commission_bps integer NOT NULL DEFAULT 800 CHECK(commission_bps BETWEEN 0 AND 4000),
  created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.catalog_links(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),storefront_product_id text NOT NULL UNIQUE,
  merchant_id uuid REFERENCES garak_ops.merchants(id),status text NOT NULL DEFAULT 'draft',
  verified_origin boolean NOT NULL DEFAULT false,verified_photos boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.stock_ledger(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,product_external_id text NOT NULL,
  change_qty integer NOT NULL,source_type text NOT NULL,source_reference text NOT NULL,
  idempotency_key text NOT NULL UNIQUE,actor_user_id text,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.stock_reservations(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),order_external_id text NOT NULL,
  product_external_id text NOT NULL,qty integer NOT NULL CHECK(qty>0),
  status text NOT NULL CHECK(status IN ('reserved','committed','released')),
  UNIQUE(order_external_id,product_external_id));
CREATE TABLE IF NOT EXISTS garak_ops.order_events(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,order_external_id text NOT NULL,
  event_type text NOT NULL,event_data jsonb NOT NULL DEFAULT '{}'::jsonb,
  actor_user_id text,idempotency_key text NOT NULL UNIQUE,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.payment_events(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,order_external_id text NOT NULL,
  provider text NOT NULL,external_payment_id text,provider_event_id text NOT NULL UNIQUE,
  verified_amount bigint CHECK(verified_amount>=0),verified_at timestamptz,
  payload_sha256 text NOT NULL,processed_at timestamptz);
CREATE TABLE IF NOT EXISTS garak_ops.shipments(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),order_external_id text NOT NULL UNIQUE,
  merchant_id uuid REFERENCES garak_ops.merchants(id),carrier text,tracking_number text,
  cold_chain_required boolean NOT NULL DEFAULT true,status text NOT NULL DEFAULT 'pending',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.recipes(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),legacy_source_id text UNIQUE,
  title text NOT NULL,category text NOT NULL,ingredients jsonb NOT NULL DEFAULT '[]'::jsonb,
  steps jsonb NOT NULL DEFAULT '[]'::jsonb,media_asset_id text,linked_product_ids text[] NOT NULL DEFAULT '{}',
  review_state text NOT NULL DEFAULT 'draft' CHECK(review_state IN ('draft','approved','rejected')),
  reviewer_id text,approved_at timestamptz,updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.creator_connections(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),owner_auth_user_id text NOT NULL,
  provider text NOT NULL CHECK(provider IN ('blogger','youtube')),
  provider_account_id text NOT NULL,encrypted_refresh_token bytea,
  granted_scopes text[] NOT NULL DEFAULT '{}',revoked_at timestamptz,
  UNIQUE(owner_auth_user_id,provider,provider_account_id));
CREATE TABLE IF NOT EXISTS garak_ops.community_posts(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),author_auth_user_id text,
  merchant_id uuid REFERENCES garak_ops.merchants(id),category text NOT NULL,title text NOT NULL,
  content text NOT NULL,disclosure_kind text NOT NULL DEFAULT 'organic',
  status text NOT NULL DEFAULT 'pending',identity_checked_at timestamptz,
  reviewer_id text,reviewed_at timestamptz,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.ad_campaigns(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),merchant_id uuid REFERENCES garak_ops.merchants(id),
  name text NOT NULL,placement text NOT NULL,start_at timestamptz,end_at timestamptz,
  budget_krw bigint NOT NULL DEFAULT 0 CHECK(budget_krw>=0),status text NOT NULL DEFAULT 'draft',
  disclosure_required boolean NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS garak_ops.ad_events(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,campaign_id uuid REFERENCES garak_ops.ad_campaigns(id),
  event_type text NOT NULL,event_time timestamptz NOT NULL DEFAULT now(),
  attribution_id text,order_external_id text,amount_krw bigint);
CREATE TABLE IF NOT EXISTS garak_ops.settlements(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),order_external_id text NOT NULL,
  merchant_id uuid NOT NULL REFERENCES garak_ops.merchants(id),gross_krw bigint NOT NULL,
  platform_fee_krw bigint NOT NULL,payout_krw bigint NOT NULL,
  state text NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','approved','paid','reversed')),
  payout_transaction_id text,settled_at timestamptz,
  UNIQUE(order_external_id,merchant_id));
CREATE TABLE IF NOT EXISTS garak_ops.support_tickets(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),customer_external_id text,
  order_external_id text,subject text NOT NULL,status text NOT NULL DEFAULT 'open',
  assigned_user_id text,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.integrations(
  provider text PRIMARY KEY,configured boolean NOT NULL DEFAULT false,
  verified_at timestamptz,last_sync_at timestamptz,last_error_code text);
CREATE TABLE IF NOT EXISTS garak_ops.webhook_inbox(
  provider text NOT NULL,event_id text NOT NULL,payload_digest text NOT NULL,
  verified boolean NOT NULL DEFAULT false,received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,error_text text,PRIMARY KEY(provider,event_id));
CREATE TABLE IF NOT EXISTS garak_ops.audit_log(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,actor_auth_user_id text,
  action text NOT NULL,entity text NOT NULL,entity_id text,previous_state jsonb,new_state jsonb,
  request_id text,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS garak_ops.event_metrics(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,event_name text NOT NULL,
  page_path text NOT NULL,event_time timestamptz NOT NULL DEFAULT now(),
  source text NOT NULL DEFAULT 'web',anonymous_session_hash text);
CREATE INDEX IF NOT EXISTS ops_stock_prod ON garak_ops.stock_ledger(product_external_id,created_at DESC);
CREATE INDEX IF NOT EXISTS ops_order_events ON garak_ops.order_events(order_external_id,created_at DESC);
CREATE INDEX IF NOT EXISTS ops_ads_time ON garak_ops.ad_events(event_time);
CREATE INDEX IF NOT EXISTS ops_posts_review ON garak_ops.community_posts(status,created_at DESC);
CREATE INDEX IF NOT EXISTS ops_audit_time ON garak_ops.audit_log(created_at DESC);
-- Authorization must be implemented with tenant-scoped RLS or authenticated
-- service roles + audited backend checks before using these tables in production.
-- Do not apply without reviewing original Drizzle schema and legal/account data.
COMMIT;
