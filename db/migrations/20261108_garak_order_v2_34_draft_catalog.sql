-- 2026-11-08: ID-locked candidate migration, Neon DEVELOPMENT branch only.
-- Imports 34 verified-identification candidates as DRAFTS with stock=0.
-- Never modifies public.garak_partner_products or publishes products.
-- No fabricated real images, allergens, origin, inventory or merchant identity.
DO $guard$
DECLARE
    n integer;
BEGIN
    SELECT COUNT(*) INTO n FROM public.garak_partner_products p
    WHERE p.merchant_slug='gwangyang-fisheries'
      AND p.sku BETWEEN 'GYS-011' AND 'GYS-047'
      AND p.sku NOT IN ('GYS-037','GYS-038','GYS-039')
      AND p.status='pending'
      AND p.price_krw>0
      AND p.stock=0 AND p.image_verified=false;
    IF n <> 34 THEN
        RAISE EXCEPTION 'Source catalog differs from expected 34 pending candidate rows: %', n;
    END IF;
END
$guard$;

INSERT INTO garak_order_v2.merchants
    (id,name,status,business_verified,commission_bps)
VALUES
    (md5('garak_order_v2:merchant:gwangyang-fisheries')::uuid,
     'gwangyang-fisheries', 'pending', false, 800)
ON CONFLICT(id) DO NOTHING;

INSERT INTO garak_order_v2.products
    (id,merchant_id,slug,name,description,category,price_krw,
     stock,origin,allergen_codes,image_key,publication)
SELECT md5('garak_order_v2:sku:'||p.sku)::uuid,
       md5('garak_order_v2:merchant:gwangyang-fisheries')::uuid,
       p.sku,p.name,COALESCE(p.description,''),p.category_code,
       p.price_krw,0,'','[]'::jsonb,NULL,'draft'
FROM public.garak_partner_products p
WHERE p.merchant_slug='gwangyang-fisheries'
  AND p.sku BETWEEN 'GYS-011' AND 'GYS-047'
  AND p.sku NOT IN ('GYS-037','GYS-038','GYS-039')
  AND p.status='pending'
  AND p.price_krw>0 AND p.stock=0 AND p.image_verified=false
ORDER BY p.sku
ON CONFLICT(merchant_id,slug) DO NOTHING;

-- Readback: 34 draft products, stock 0, no images and merchant pending.
SELECT (SELECT COUNT(*) FROM garak_order_v2.products p
            WHERE p.merchant_id=md5('garak_order_v2:merchant:gwangyang-fisheries')::uuid)
       AS draft_count,
       (SELECT COUNT(*) FROM garak_order_v2.products p
            WHERE p.merchant_id=md5('garak_order_v2:merchant:gwangyang-fisheries')::uuid
              AND p.publication<>'draft') AS not_draft,
       (SELECT COUNT(*) FROM garak_order_v2.products p
            WHERE p.merchant_id=md5('garak_order_v2:merchant:gwangyang-fisheries')::uuid
              AND (p.stock<>0 OR p.image_key IS NOT NULL))
       AS accidentally_sellable_or_image_claimed;
