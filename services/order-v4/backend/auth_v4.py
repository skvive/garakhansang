"""Fail-closed OIDC ID token verification. Claims alone NEVER confer staff roles."""
import os
from functools import lru_cache
from dataclasses import dataclass
from urllib.parse import urlparse
import jwt
from jwt import PyJWKClient

class AuthenticationError(Exception):
    pass

@dataclass(frozen=True)
class AuthSubject:
    sub: str

@lru_cache(maxsize=4)
def _jwks_client(url: str):
    return PyJWKClient(url, cache_keys=True, cache_jwk_set=True, lifespan=300, timeout=5)

def verify_oidc(token: str) -> AuthSubject:
    issuer=os.getenv('GHO_OIDC_ISSUER','').rstrip('/')
    audience=os.getenv('GHO_OIDC_AUDIENCE','')
    jwks_url=os.getenv('GHO_OIDC_JWKS_URL','')
    if not all((issuer,audience,jwks_url)):
        raise AuthenticationError('OIDC provider not configured')
    if any(urlparse(u).scheme!='https' or not urlparse(u).hostname for u in (issuer,jwks_url)):
        raise AuthenticationError('OIDC requires HTTPS URLs')
    if not isinstance(token,str) or len(token)>12000:
        raise AuthenticationError('Invalid token length')
    try:
        key=_jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims=jwt.decode(token,key.key,algorithms=['RS256'],issuer=issuer,audience=audience,
                          options={'require':['exp','iat','iss','aud','sub']},leeway=30)
        sub=claims['sub']
        if not isinstance(sub,str) or not 4<=len(sub)<=255:
            raise AuthenticationError('Invalid token subject')
        return AuthSubject(sub)
    except (jwt.PyJWTError,ValueError,KeyError,TypeError) as exc:
        raise AuthenticationError('JWT signature/claims verification failed') from exc
