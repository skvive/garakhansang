-- Stripe TEST Checkout session URL idempotency, staging only.
ALTER TABLE garak_order_v2.payment_attempts ADD COLUMN IF NOT EXISTS checkout_url text;
CREATE UNIQUE INDEX IF NOT EXISTS idx_go_v2_one_checkout_per_order ON garak_order_v2.payment_attempts(order_id);
