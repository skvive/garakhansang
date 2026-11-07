import unittest
from admin_core.delivery_flow import DeliveryOrder,OrderFlowError,transition

class DeliveryFlowTests(unittest.TestCase):
 def setUp(self):
  self.o=DeliveryOrder(order_id="sandbox-order-1",merchant_id="merchant-a")
 def move(self,o,event,role,actor,verified=False):
  return transition(o,event,role,actor,o.version,verified)
 def test_verified_payment_notifies_merchant(self):
  o=self.move(self.o,"payment_verified","payment_service","stripe-webhook",True)
  self.assertEqual(o.order.state,"paid")
  self.assertEqual(o.notifications,("merchant:new_paid_order",))
 def test_no_fake_payment_without_provider_proof(self):
  with self.assertRaises(OrderFlowError):
   self.move(self.o,"payment_verified","payment_service","demo")
  with self.assertRaises(OrderFlowError):
   self.move(self.o,"payment_verified","customer","customer-a",True)
 def test_merchant_cannot_access_another_shop(self):
  o=self.move(self.o,"payment_verified","payment_service","stripe-webhook",True).order
  with self.assertRaises(OrderFlowError):
   self.move(o,"merchant_accept","merchant","merchant-b")
 def test_normal_delivery(self):
  o=self.move(self.o,"payment_verified","payment_service","stripe-webhook",True).order
  for event,role,actor in [
    ("merchant_accept","merchant","merchant-a"),
    ("merchant_prepare","merchant","merchant-a"),
    ("merchant_ready","merchant","merchant-a"),
    ("merchant_request_dispatch","merchant","merchant-a"),
    ("rider_accept","rider","rider-9"),
    ("rider_pickup","rider","rider-9"),
    ("rider_start_delivery","rider","rider-9"),
    ("rider_deliver","rider","rider-9"),
  ]:
   o=self.move(o,event,role,actor).order
  self.assertEqual(o.state,"delivered")
  self.assertEqual(o.rider_id,"rider-9")
  self.assertEqual(o.version,9)
 def test_rider_cannot_take_over(self):
  o=self.move(self.o,"payment_verified","payment_service","stripe",True).order
  for event in ("merchant_accept","merchant_prepare","merchant_ready","merchant_request_dispatch"):
   o=self.move(o,event,"merchant","merchant-a").order
  o=self.move(o,"rider_accept","rider","rider-9").order
  with self.assertRaises(OrderFlowError):
   self.move(o,"rider_pickup","rider","rider-8")
 def test_refund_must_be_provider_confirmed(self):
  o=self.move(self.o,"payment_verified","payment_service","stripe",True).order
  o=self.move(o,"merchant_reject","merchant","merchant-a").order
  self.assertEqual(o.state,"refund_pending")
  with self.assertRaises(OrderFlowError):
   self.move(o,"refund_verified","payment_service","stripe")
  o=self.move(o,"refund_verified","payment_service","stripe",True).order
  self.assertEqual(o.state,"refunded")
 def test_stale_version_fails(self):
  with self.assertRaises(OrderFlowError):
   transition(self.o,"payment_verified","payment_service","stripe",-1,True)
 def test_cannot_dispatch_before_payment(self):
  with self.assertRaises(OrderFlowError):
   self.move(self.o,"merchant_request_dispatch","merchant","merchant-a")
 def test_duplicate_rider_accept_is_invalid(self):
  o=self.move(self.o,"payment_verified","payment_service","stripe",True).order
  for event in ("merchant_accept","merchant_prepare","merchant_ready","merchant_request_dispatch"):
   o=self.move(o,event,"merchant","merchant-a").order
  o=self.move(o,"rider_accept","rider","rider-9").order
  with self.assertRaises(OrderFlowError):
   self.move(o,"rider_accept","rider","rider-9")
if __name__=="__main__":
 unittest.main()
