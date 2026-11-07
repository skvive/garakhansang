-- Order V2: safely release an unpaid reservation only if no unpaid Stripe checkout
-- can still complete. PG session must be explicitly expired/failed by a trusted BFF.
-- Staging-only, no direct GRANT to public / user roles.
CREATE OR REPLACE FUNCTION garak_order_v2.release_unpaid_reservation(p_order_id uuid)
RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,garak_order_v2
AS $BODY$
DECLARE
  v_order RECORD;
  v_hold RECORD;
BEGIN
  SELECT id,state,version,customer_auth_sub INTO v_order
    FROM garak_order_v2.orders WHERE id=p_order_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'order not found'; END IF;
  IF v_order.state='canceled' THEN RETURN false; END IF;
  IF v_order.state<>'payment_pending' THEN
    RAISE EXCEPTION 'cannot release paid or fulfilled inventory';
  END IF;
  IF EXISTS(
    SELECT 1 FROM garak_order_v2.payment_attempts pa
    WHERE pa.order_id=p_order_id AND pa.state NOT IN ('failed')
  ) THEN
    RAISE EXCEPTION 'Stripe payment is not confirmed failed or expired; hold cannot be released';
  END IF;
  FOR v_hold IN
    UPDATE garak_order_v2.inventory_holds h
      SET state='released'
      WHERE h.order_id=p_order_id AND h.state='held'
      RETURNING product_id, quantity
  LOOP
    UPDATE garak_order_v2.products p
      SET stock = p.stock + v_hold.quantity WHERE p.id = v_hold.product_id;
  END LOOP;
  UPDATE garak_order_v2.orders
    SET state='canceled',version=version+1,updated_at=now()
    WHERE id=p_order_id;
  INSERT INTO garak_order_v2.notification_outbox
    (order_id,event,recipient_role,recipient_subject,order_version)
    VALUES(p_order_id,'unpaid_order_cancelled','customer',
           v_order.customer_auth_sub,v_order.version+1)
    ON CONFLICT DO NOTHING;
  RETURN true;
END;
$BODY$;
REVOKE ALL ON FUNCTION garak_order_v2.release_unpaid_reservation(uuid)
 FROM PUBLIC,anonymous,authenticated;
