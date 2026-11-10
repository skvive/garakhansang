"""Offline unit tests for RODI POS state/integrity rules. Never charge real cards."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rodipos_server', ROOT/'server.py')
pos=importlib.util.module_from_spec(spec);spec.loader.exec_module(pos)

class RodiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=pos.DB
        pos.DB=Path(self.temp.name)/'test.sqlite3'
        pos.init_db()
    def tearDown(self):pos.DB=self.old;self.temp.cleanup()
    def order(self,items=None,key=None):
        return pos.create_checkout(items or [{'id':'latte','qty':2,'option':'ICED'}],key or ('test-'+('x'*28)))
    def test_server_recalculates_price(self):
        o=self.order([{'id':'latte','qty':2,'option':'ICED','price':1}]);self.assertEqual(o['amount'],11000)
    def test_idempotency_reuses_checkout(self):
        a=self.order();b=self.order();self.assertEqual(a['id'],b['id'])
        self.assertRaises(ValueError,pos.create_checkout,[{'id':'cookie','qty':1,'option':'기본'}],a['id'] if False else ('test-'+('x'*28)))
    def test_invalid_quantity_and_options(self):
        for i in [[{'id':'latte','qty':-1}],[{'id':'latte','qty':0}],[{'id':'cookie','qty':1,'option':'HOT'}],[{'id':'latte','qty':True}],[{'id':'NOT_REAL','qty':1}]]:
            with self.subTest(i=i):self.assertRaises(ValueError,pos.create_checkout,i,'test-valid-idempotency-key-001')
    def test_paid_sequence_and_double_callback(self):
        a=self.order();t=1234567890
        result=pos.finalize_payment(a['id'],a['payment_key'],'SUCCESS','DEMO_CARD','DEMO123',t)
        self.assertEqual(result['queue_number'],1);self.assertEqual(result['status'],'queued')
        result2=pos.finalize_payment(a['id'],a['payment_key'],'SUCCESS','DEMO_CARD','DEMO123',t)
        self.assertEqual(result2['queue_number'],1)
        b=self.order([{'id':'cookie','qty':1,'option':'기본'}],'test-second-xxxxxxxxxxxxxxxxxxx')
        result3=pos.finalize_payment(b['id'],b['payment_key'],'SUCCESS','DEMO_CARD','DEMO124',t)
        self.assertEqual(result3['queue_number'],2)
    def test_failed_does_not_create_queue(self):
        a=self.order();b=pos.finalize_payment(a['id'],a['payment_key'],'FAILED','','',0)
        self.assertIsNone(b['queue_number']);self.assertEqual(b['status'],'awaiting_payment');self.assertEqual(pos.list_orders(),[])
    def test_invalid_callback_cannot_mark_paid(self):
        a=self.order();self.assertRaises(ValueError,pos.finalize_payment,a['id'],'wrong','SUCCESS','DEMO_CARD','abc',123)
        self.assertEqual(pos.read_order(a['id'])['status'],'awaiting_payment')
    def test_staff_state_machine(self):
        a=self.order();pos.finalize_payment(a['id'],a['payment_key'],'SUCCESS','DEMO_CARD','abc',123)
        self.assertRaises(ValueError,pos.transition_order,a['id'],'ready')
        for name in ['preparing','ready','collected']:
            self.assertEqual(pos.transition_order(a['id'],name)['status'],name)
        self.assertRaises(ValueError,pos.transition_order,a['id'],'preparing')
    def test_cancelled_cart_never_appears_at_payment(self):
        a=self.order()
        b=pos.cancel_pending(a['id'],a['payment_key'])
        self.assertEqual(b['status'],'cancelled')
        self.assertRaises(ValueError,pos.finalize_payment,a['id'],a['payment_key'],'SUCCESS','DEMO_CARD','abc',123)
        self.assertEqual(pos.list_orders(),[])
    def test_receipt_requires_paid(self):
        a=self.order();self.assertRaises(ValueError,pos.log_print,a['id'],'printed')
        pos.finalize_payment(a['id'],a['payment_key'],'SUCCESS','DEMO_CARD','abc',123)
        b=pos.log_print(a['id'],'failed');self.assertEqual(b['print_attempts'],1)
        b=pos.log_print(a['id'],'printed');self.assertEqual(b['print_status'],'printed')

if __name__=='__main__':unittest.main()
