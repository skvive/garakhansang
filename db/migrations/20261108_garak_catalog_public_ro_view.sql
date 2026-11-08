-- READ-ONLY publication boundary for native/web clients.
-- The view exposes no customer orders, addresses, payment data, or applications.
CREATE SCHEMA IF NOT EXISTS garak_catalog_api;
REVOKE ALL ON SCHEMA garak_catalog_api FROM PUBLIC;
CREATE OR REPLACE VIEW garak_catalog_api.approved_products
WITH (security_barrier=true)
AS
SELECT p.sku, p.merchant_slug, p.name, p.description,
       p.category_code, c.name AS category_name, p.price_krw,
       p.stock, p.image_ref, p.updated_at
FROM public.garak_partner_release_ready r
JOIN public.garak_partner_products p
  ON p.sku=r.sku AND p.merchant_slug=r.merchant_slug
JOIN public.garak_partner_categories c
  ON c.code=p.category_code AND c.merchant_slug=p.merchant_slug
WHERE r.release_ready IS TRUE
  AND p.status='approved' AND c.status='approved'
  AND p.visible IS TRUE AND p.purchasable IS TRUE
  AND p.image_verified IS TRUE
  AND p.stock > 0 AND p.price_krw > 0
  AND upper(trim(p.currency))='KRW'
  AND p.image_ref ~* '^https://';
REVOKE ALL ON garak_catalog_api.approved_products FROM PUBLIC;
-- Neon read_only role must be restricted to garak_catalog_api only,
-- never public.orders, auth, customer addresses or payment records.
