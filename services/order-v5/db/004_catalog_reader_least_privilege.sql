-- Only isolated DEV branch br-winter-flower-b5tvau07; not for production.
-- SQL-created role gho_catalog_runtime_v5 has NOINHERIT NOBYPASSRLS NOCREATEROLE.
REVOKE ALL ON SCHEMA gho FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION gho.create_demo_checkout(text,text,jsonb) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION gho.cancel_demo_order(text,uuid) FROM PUBLIC;
GRANT USAGE ON SCHEMA gho TO gho_catalog_runtime_v5;
GRANT SELECT ON gho.markets TO gho_catalog_runtime_v5;
GRANT SELECT(id,business_name,approval_status,is_demo) ON gho.merchants TO gho_catalog_runtime_v5;
GRANT SELECT(id,merchant_id,market_id,catalog_ref,name,price_krw,stock,temp_class,supports_slicing,is_demo,status) ON gho.products TO gho_catalog_runtime_v5;
DROP POLICY IF EXISTS gho_catalog_guard_merchants_v5 ON gho.merchants;
CREATE POLICY gho_catalog_guard_merchants_v5 ON gho.merchants FOR SELECT TO gho_catalog_runtime_v5 USING (is_demo AND approval_status='approved');
DROP POLICY IF EXISTS gho_catalog_guard_products_v5 ON gho.products;
CREATE POLICY gho_catalog_guard_products_v5 ON gho.products FOR SELECT TO gho_catalog_runtime_v5 USING (is_demo AND status='active');
