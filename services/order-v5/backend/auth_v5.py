"""Neon Managed Auth Ed25519 JWT verifier: only authenticated sub, never role claims."""
import os
from urllib.parse import urlsplit
from dataclasses import dataclass
from functools import lru_cache
import jwt
from jwt import PyJWKClient
class AuthenticationError(Exception): pass
@dataclass(frozen=True)
class AuthSubject:
    sub: str
@lru_cache(maxsize=2)
def _jwks_client(url):
    return PyJWKClient(url,cache_keys=True,cache_jwk_set=True,lifespan=300,timeout=5)
def verify_oidc(token):
    base=os.getenv('GHO_NEON_AUTH_BASE_URL','').rstrip('/')
    issuer=os.getenv('GHO_OIDC_ISSUER','').rstrip('/')
    aud=os.getenv('GHO_OIDC_AUDIENCE','')
    jwks=os.getenv('GHO_OIDC_JWKS_URL','')
    if not all((base,issuer,aud,jwks)):
        raise AuthenticationError('Neon Auth config missing')
    parsed=urlsplit(base)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AuthenticationError('Invalid Auth base URL')
    if urlsplit(issuer).netloc!=parsed.netloc or urlsplit(issuer).scheme!='https' or jwks!=base+'/.well-known/jwks.json':
        raise AuthenticationError('Untrusted issuer or JWKS')
    if not isinstance(token,str) or not 20<=len(token)<=12000:
        raise AuthenticationError('Invalid token length')
    try:
        header=jwt.get_unverified_header(token)
        if header.get('alg')!='EdDSA' or not header.get('kid'):
            raise AuthenticationError('Only signed Neon Auth EdDSA tokens allowed')
        key=_jwks_client(jwks).get_signing_key_from_jwt(token)
        c=jwt.decode(token,key.key,algorithms=['EdDSA'],issuer=issuer,audience=aud,
             options={'require':['exp','iat','iss','aud','sub']},leeway=30)
        if not isinstance(c['sub'],str) or not 4<=len(c['sub'])<=255:
            raise AuthenticationError('Invalid identity')
        if not isinstance(c['iat'],int) or not isinstance(c['exp'],int) or c['exp']<=c['iat'] or c['exp']-c['iat']>1200:
            raise AuthenticationError('Invalid token lifetime')
        return AuthSubject(c['sub'])
    except AuthenticationError: raise
    except (jwt.PyJWTError,ValueError,KeyError,TypeError) as e:
        raise AuthenticationError('Invalid JWT signature/claims') from e
