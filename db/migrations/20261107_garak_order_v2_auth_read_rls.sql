-- Staging read-only Data API access (Neon Auth). All writes require server BFF verified session.
-- Never copy anonymous grants, disable row security, or trust client role claims.
-- This script must be applied only once to the staging development branch.

ALTER TABLE garak_order_v2.merchants ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.delivery_zones ENABLE ROW LEVEL SECURITY;

ALTER TABLE garak_order_v2.product_options ENABLE ROW LEVEL SECURITY;

CREATE POLICY go_merchants_read ON garak_order_v2.merchants FOR SELECT TO authenticated USING (
    status = 'approved' AND business_verified = true
    OR EXISTS (SELECT 1 FROM garak_order_v2.merchant_memberships mm WHERE mm.merchant_id=id AND mm.auth_sub=auth.user_id() AND mm.active)
);

CREATE POLICY go_memberships_read ON garak_order_v2.merchant_memberships FOR SELECT TO authenticated USING (auth_sub=auth.user_id() AND active);

CREATE POLICY go_products_read ON garak_order_v2.products FOR SELECT TO authenticated USING (
    (publication='approved' AND EXISTS(SELECT 1 FROM garak_order_v2.merchants m WHERE m.id=merchant_id AND m.status='approved' AND m.business_verified))
    OR EXISTS(SELECT 1 FROM garak_order_v2.merchant_memberships mm WHERE mm.merchant_id=products.merchant_id AND mm.auth_sub=auth.user_id() AND mm.active)
);

CREATE POLICY go_options_read ON garak_order_v2.product_options FOR SELECT TO authenticated USING (
    EXISTS(SELECT 1 FROM garak_order_v2.products p WHERE p.id=product_id)
);

CREATE POLICY go_zones_read ON garak_order_v2.delivery_zones FOR SELECT TO authenticated USING (
    (available AND EXISTS(SELECT 1 FROM garak_order_v2.merchants m WHERE m.id=delivery_zones.merchant_id AND m.status='approved' AND m.business_verified))
    OR EXISTS(SELECT 1 FROM garak_order_v2.merchant_memberships mm WHERE mm.merchant_id=delivery_zones.merchant_id AND mm.auth_sub=auth.user_id() AND mm.active)
);

CREATE POLICY go_orders_read ON garak_order_v2.orders FOR SELECT TO authenticated USING (
    customer_auth_sub=auth.user_id() OR EXISTS(
      SELECT 1 FROM garak_order_v2.merchant_memberships mm
      WHERE mm.merchant_id=orders.merchant_id AND mm.auth_sub=auth.user_id() AND mm.active)
);

CREATE POLICY go_order_lines_read ON garak_order_v2.order_lines FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM garak_order_v2.orders o WHERE o.id=order_id)
);

CREATE POLICY go_riders_read ON garak_order_v2.riders FOR SELECT TO authenticated USING (auth_sub=auth.user_id());

CREATE POLICY go_deliveries_read ON garak_order_v2.deliveries FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM garak_order_v2.riders r WHERE r.id=rider_id AND r.auth_sub=auth.user_id())
    OR EXISTS (SELECT 1 FROM garak_order_v2.orders o WHERE o.id=order_id)
);

CREATE POLICY go_settlements_read ON garak_order_v2.settlements FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM garak_order_v2.merchant_memberships mm
      WHERE mm.merchant_id=settlements.merchant_id AND mm.auth_sub=auth.user_id() AND mm.active)
);

CREATE POLICY go_outbox_read ON garak_order_v2.notification_outbox FOR SELECT TO authenticated USING (
    (recipient_role IN ('customer','rider') AND recipient_subject=auth.user_id())
    OR (recipient_role='merchant' AND EXISTS (
       SELECT 1 FROM garak_order_v2.merchant_memberships mm
       WHERE mm.merchant_id::text=notification_outbox.recipient_subject
         AND mm.auth_sub=auth.user_id() AND mm.active))
);

GRANT USAGE ON SCHEMA garak_order_v2 TO authenticated;

GRANT SELECT ON garak_order_v2.merchants,garak_order_v2.merchant_memberships,
 garak_order_v2.products,garak_order_v2.product_options,garak_order_v2.delivery_zones,
 garak_order_v2.orders,garak_order_v2.order_lines,garak_order_v2.riders,
 garak_order_v2.deliveries,garak_order_v2.settlements,garak_order_v2.notification_outbox TO authenticated;

REVOKE ALL ON SCHEMA garak_order_v2 FROM anonymous;

REVOKE ALL ON ALL TABLES IN SCHEMA garak_order_v2 FROM anonymous;
