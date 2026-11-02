import unittest,os,time,sys
from pathlib import Path
from unittest.mock import patch,MagicMock
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import auth_v5,repository_v5
AUTH='https://ep-gentle-wind-b5ir41pn.neonauth.c-7.us-east-2.aws.neon.tech/neondb/auth'
CONFIG={'GHO_NEON_AUTH_BASE_URL':AUTH,'GHO_OIDC_ISSUER':AUTH,'GHO_OIDC_AUDIENCE':AUTH,'GHO_OIDC_JWKS_URL':AUTH+'/.well-known/jwks.json'}
class V5(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate()
    def token(self,**kw):
        now=int(time.time());claims={'iss':AUTH,'aud':AUTH,'sub':'customer-abc123','iat':now,'exp':now+900,'role':'admin'};claims.update(kw)
        return jwt.encode(claims,self.key,algorithm='EdDSA',headers={'kid':'test'})
    def verify(self,token,config=None):
        fake=MagicMock();fake.get_signing_key_from_jwt.return_value=type('Key',(),{'key':self.key.public_key()})()
        with patch.dict(os.environ,config or CONFIG),patch.object(auth_v5,'_jwks_client',return_value=fake):
            return auth_v5.verify_oidc(token)
    def test_ed25519(self): self.assertEqual(self.verify(self.token()).sub,'customer-abc123')
    def test_expiry(self):
        with self.assertRaises(auth_v5.AuthenticationError):self.verify(self.token(exp=int(time.time())-100))
    def test_audience(self):
        with self.assertRaises(auth_v5.AuthenticationError):self.verify(self.token(aud='evil'))
    def test_issuer(self):
        with self.assertRaises(auth_v5.AuthenticationError):self.verify(self.token(iss='https://evil.example'))
    def test_jwks_pin(self):
        with self.assertRaises(auth_v5.AuthenticationError):self.verify(self.token(),{**CONFIG,'GHO_OIDC_JWKS_URL':'https://evil.example/jwks'})
    def test_missing_kid(self):
        now=int(time.time());t=jwt.encode({'iss':AUTH,'aud':AUTH,'sub':'customer-abc123','iat':now,'exp':now+600},self.key,algorithm='EdDSA')
        with self.assertRaises(auth_v5.AuthenticationError):self.verify(t)
    def test_lifetime(self):
        with self.assertRaises(auth_v5.AuthenticationError):self.verify(self.token(exp=int(time.time())+3600))
    def test_wrong_db_role(self):
        with patch.dict(os.environ,{'GHO_V4_MODE':'isolated-dev','GHO_CATALOG_READ_DSN':'postgresql://neondb_owner:fake@ep-gentle-wind-b5ir41pn.c-7.us-east-2.aws.neon.tech/neondb?sslmode=verify-full'}):
            with self.assertRaises(repository_v5.StorageUnavailable):
                with repository_v5.open_catalog_db():pass
if __name__=='__main__':unittest.main()
