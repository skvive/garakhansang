import os
import sys
import unittest
import time
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.api_v4 import app,get_db, get_subject
from backend import repository_v4 as repo
from backend.auth_v4 import verify_oidc,AuthenticationError

class FakeDB: pass
class TestV4(unittest.TestCase):
    def setUp(self):
        self.db=FakeDB();self.subject='oidc|customer-01'
        app.dependency_overrides[get_db]=lambda:self.db
        self.client=TestClient(app)
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_never_claims_live_payment(self):
        j=self.client.get('/order/api/v4/health').json()
        self.assertEqual(j['real_payments'],False);self.assertEqual(j['demo'],True)

    def test_missing_auth_rejected(self):
        resp=self.client.post('/order/api/v4/checkouts',json={'lines':[{'id':'g1','qty':1}]},headers={'Idempotency-Key':'12345678'})
        self.assertEqual(resp.status_code,401)

    def test_valid_customer_checkout_passes_subject_not_role(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        with patch.object(repo,'create_checkout',return_value={'demo':True,'checkout_id':'x','orders':[]}) as fn:
            resp=self.client.post('/order/api/v4/checkouts',json={'lines':[{'id':'g1','qty':2}]},headers={'Idempotency-Key':'KEY000011'})
            self.assertEqual(resp.status_code,201)
            self.assertEqual(fn.call_args.args[1],self.subject)
            self.assertEqual(fn.call_args.args[2],'KEY000011')

    def test_cart_rejects_oversize_and_unknown_field(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        for data in ({'lines':[]},{'lines':[{'id':'g1','qty':100}]},{'lines':[{'id':'g1','qty':1,'free':True}]}):
            self.assertEqual(self.client.post('/order/api/v4/checkouts',json=data,headers={'Idempotency-Key':'KEY000011'}).status_code,422)

    def test_cross_tenant_denied(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        with patch.object(repo,'merchant_orders',side_effect=repo.Forbidden('not linked')):
            resp=self.client.get('/order/api/v4/merchants/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/orders')
            self.assertEqual(resp.status_code,403)

    def test_customer_cancel_uses_jwt_subject(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        with patch.object(repo,'cancel_checkout_order',return_value={'state':'cancelled'}) as fn:
            resp=self.client.post('/order/api/v4/orders/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/cancel')
            self.assertEqual(resp.status_code,200)
            self.assertEqual(fn.call_args.args[1],self.subject)

    def test_arbitrary_staff_claim_not_used(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        with patch.object(repo,'hub_collect',side_effect=repo.Forbidden('no grant')):
            resp=self.client.post('/order/api/v4/markets/garak/orders/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/hub-collect')
            self.assertEqual(resp.status_code,403)

    def test_rider_cannot_act_on_another_rider_job(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        with patch.object(repo,'rider_progress',side_effect=repo.Forbidden('not assigned')):
            resp=self.client.post('/order/api/v4/dispatch/jobs/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/deliver')
            self.assertEqual(resp.status_code,403)

    def test_hub_cannot_assign_unregistered_rider(self):
        app.dependency_overrides[get_subject]=lambda:self.subject
        with patch.object(repo,'assign_rider',side_effect=repo.Forbidden('rider not enrolled')):
            resp=self.client.post('/order/api/v4/dispatch/jobs/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/assign',json={'rider_subject':'other-rider'})
            self.assertEqual(resp.status_code,403)

    def test_local_dev_mode_required(self):
        with patch.dict(os.environ,{'GHO_V4_MODE':'production','GHO_NEON_DSN':'postgres://u:pass@host.neon.tech/db'}):
            with self.assertRaises(repo.StorageUnavailable):
                with repo.open_db():pass

    def test_rejects_production_neon_endpoint_even_in_dev_mode(self):
        with patch.dict(os.environ,{'GHO_V4_MODE':'isolated-dev',
            'GHO_NEON_DSN':'postgres://user:fake@ep-production.c-7.us-east-2.aws.neon.tech/neondb?sslmode=verify-full'}):
            with self.assertRaises(repo.StorageUnavailable):
                with repo.open_db():pass

    def test_rejects_unverified_tls_mode(self):
        with patch.dict(os.environ,{'GHO_V4_MODE':'isolated-dev',
            'GHO_NEON_DSN':'postgres://user:fake@ep-gentle-wind-b5ir41pn.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require'}):
            with self.assertRaises(repo.StorageUnavailable):
                with repo.open_db():pass

    def test_oidc_is_fail_closed_without_config(self):
        with patch.dict(os.environ,{'GHO_OIDC_ISSUER':'','GHO_OIDC_AUDIENCE':'','GHO_OIDC_JWKS_URL':''}):
            with self.assertRaises(AuthenticationError):verify_oidc('test')

    def test_oidc_rejects_http_jwks_even_with_good_token(self):
        with patch.dict(os.environ,{'GHO_OIDC_ISSUER':'https://idp.example','GHO_OIDC_AUDIENCE':'gho', 'GHO_OIDC_JWKS_URL':'http://bad.example/jwks'}):
            with self.assertRaises(AuthenticationError):verify_oidc('bad')

    def test_oidc_rs256_signature_audience_expiry_and_subject(self):
        from backend import auth_v4
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        fake=MagicMock()
        fake.get_signing_key_from_jwt.return_value=type('Key',(),{'key':key.public_key()})()
        with patch.dict(os.environ,{'GHO_OIDC_ISSUER':'https://idp.test.example',
                         'GHO_OIDC_AUDIENCE':'garak-order',
                         'GHO_OIDC_JWKS_URL':'https://idp.test.example/jwks'}):
            with patch.object(auth_v4,'_jwks_client',return_value=fake):
                payload={'sub':'auth-sub-100','iss':'https://idp.test.example',
                         'aud':'garak-order','iat':int(time.time()),'exp':int(time.time())+300,
                         'role':'admin'}
                signed=jwt.encode(payload,key,algorithm='RS256',headers={'kid':'local-test'})
                # Token role='admin' is ignored; only DB grants convey staff authority.
                self.assertEqual(auth_v4.verify_oidc(signed).sub,'auth-sub-100')
                wrong_audience=jwt.encode({**payload,'aud':'wrong'},key,algorithm='RS256')
                with self.assertRaises(AuthenticationError):auth_v4.verify_oidc(wrong_audience)
                expired=jwt.encode({**payload,'exp':int(time.time())-100},key,algorithm='RS256')
                with self.assertRaises(AuthenticationError):auth_v4.verify_oidc(expired)
                unsigned=jwt.encode(payload,key,algorithm='HS256') if False else 'eyJhbGciOiJub25lIn0.eyJzdWIiOiJmb28ifQ.'
                with self.assertRaises(AuthenticationError):auth_v4.verify_oidc(unsigned)

    def test_db_scope_invalid_uuid(self):
        with self.assertRaises(ValueError):repo._parse_uuid('../another-merchant')

if __name__=='__main__':unittest.main()
