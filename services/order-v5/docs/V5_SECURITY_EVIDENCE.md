# Garak Hansang Order V5: Auth + RLS evidence (2026-11-02)
- Neon DEV project dawn-paper-21288363, branch br-winter-flower-b5tvau07 ONLY.
- Neon Managed Better Auth / Google provider configured; live login NOT tested.
- V4 JWT verifier only allowed RS256; V5 now supports EdDSA from Neon Managed Better Auth.
- SQL-created role gho_catalog_runtime_v5 has rolbypassrls=false, rolcreaterole=false, rolinherit=false. Test: demo products 17 readable, orders/audit/grants/private merchant verification SELECT permission denied. Neon API-created gho_catalog_reader_dev inherited neon_superuser BYPASSRLS and was NOT used; secret rotated, cleanup needs explicit permission.
- Local V3/V4/V5 source: 47 unittest tests passed; repository V5 subtree includes V4 and V5 targeted tests.
- No live payments, refunds, operational deployment, rider GPS, Android APK.
- Python driver could not install in local container, so direct FastAPI->Neon integration unverified. Neon DB queries verified through connector.
- Authentication web client requires npm build and real OAuth callback. Do NOT claim production readiness.
