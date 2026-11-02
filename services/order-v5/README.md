# 가락한상 오더 V5 (격리 개발 전용)
Neon Auth EdDSA/JWKS verification, independent V5 FastAPI, least-privilege catalog RLS.
Keep red A mascot customer UI in ../storefront/order; V5 OAuth sample separate.

Run: pip install -r requirements-v5.txt
Set GHO_V4_MODE=isolated-dev, GHO_NEON_DSN and GHO_CATALOG_READ_DSN to verified DEV endpoint DSNs only, GHO_NEON_AUTH_BASE_URL/GHO_OIDC_ISSUER/GHO_OIDC_AUDIENCE/GHO_OIDC_JWKS_URL to actual Neon Auth claims.
uvicorn backend.api_v5:app --host 127.0.0.1 --port 8770
python -m unittest discover -s tests -p 'test*.py'
No real payments, no production deployment; see docs/V5_SECURITY_EVIDENCE.md.
