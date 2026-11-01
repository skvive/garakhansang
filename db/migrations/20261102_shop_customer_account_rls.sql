-- REVIEW ONLY / NOT APPLIED. Requires Neon Data API and explicit approval.
-- Project: dawn-paper-21288363, branch br-jolly-surf-b5wb7ior.
-- Protect real user information using authenticated Neon JWT + RLS.
-- Test on a Neon temporary branch before migrating production.
BEGIN;
CREATE TABLE IF NOT EXISTS public.shop_customer_profiles (
  user_id uuid PRIMARY KEY REFERENCES neon_auth."user"(id) ON DELETE CASCADE,
  phone text CHECK(phone IS NULL OR length(phone) <= 30),
  postal_code text CHECK(postal_code IS NULL OR length(postal_code) <= 15),
  address_line1 text CHECK(address_line1 IS NULL OR length(address_line1) <= 250),
  address_line2 text CHECK(address_line2 IS NULL OR length(address_line2) <= 250),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.shop_customer_cart (
  user_id uuid NOT NULL REFERENCES neon_auth."user"(id) ON DELETE CASCADE,
  product_slug text NOT NULL CHECK(length(product_slug) BETWEEN 1 AND 120),
  qty integer NOT NULL CHECK(qty BETWEEN 1 AND 99),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id,product_slug)
);
CREATE TABLE IF NOT EXISTS public.shop_customer_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES neon_auth."user"(id) ON DELETE RESTRICT,
  order_reference text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','paid','preparing','shipped','delivered','canceled','refunded')),
  total_won integer NOT NULL CHECK(total_won >= 0),
  carrier text, tracking_number text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS shop_customer_orders_owner_created
  ON public.shop_customer_orders(user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS public.shop_customer_coupon_grants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES neon_auth."user"(id) ON DELETE CASCADE,
  coupon_code text NOT NULL,
  status text NOT NULL DEFAULT 'issued' CHECK(status IN ('issued','used','expired','canceled')),
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS shop_customer_coupons_user_idx
  ON public.shop_customer_coupon_grants(user_id,created_at DESC);
ALTER TABLE public.shop_customer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_cart ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_cart FORCE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_orders FORCE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_coupon_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shop_customer_coupon_grants FORCE ROW LEVEL SECURITY;
-- auth.user_id() is provided by the Neon Data API / JWT RLS integration.
CREATE POLICY shop_profile_owner_read ON public.shop_customer_profiles
  FOR SELECT TO authenticated USING (user_id::text = auth.user_id());
CREATE POLICY shop_profile_owner_insert ON public.shop_customer_profiles
  FOR INSERT TO authenticated WITH CHECK (user_id::text = auth.user_id());
CREATE POLICY shop_profile_owner_update ON public.shop_customer_profiles
  FOR UPDATE TO authenticated USING (user_id::text = auth.user_id())
  WITH CHECK (user_id::text = auth.user_id());
CREATE POLICY shop_cart_owner_read ON public.shop_customer_cart
  FOR SELECT TO authenticated USING (user_id::text = auth.user_id());
CREATE POLICY shop_cart_owner_insert ON public.shop_customer_cart
  FOR INSERT TO authenticated WITH CHECK (user_id::text = auth.user_id());
CREATE POLICY shop_cart_owner_update ON public.shop_customer_cart
  FOR UPDATE TO authenticated USING (user_id::text = auth.user_id())
  WITH CHECK (user_id::text = auth.user_id());
CREATE POLICY shop_cart_owner_delete ON public.shop_customer_cart
  FOR DELETE TO authenticated USING (user_id::text = auth.user_id());
CREATE POLICY shop_orders_owner_read ON public.shop_customer_orders
  FOR SELECT TO authenticated USING (user_id::text = auth.user_id());
CREATE POLICY shop_coupons_owner_read ON public.shop_customer_coupon_grants
  FOR SELECT TO authenticated USING (user_id::text = auth.user_id());
GRANT SELECT,INSERT,UPDATE ON public.shop_customer_profiles TO authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.shop_customer_cart TO authenticated;
GRANT SELECT ON public.shop_customer_orders,public.shop_customer_coupon_grants TO authenticated;
-- Crucially, customers CANNOT INSERT fake paid orders, tracking, or issued coupons.
COMMIT;
