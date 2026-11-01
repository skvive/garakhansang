# Garak Hansang Order — Phase 2 local engineering handoff
Date: 2026-11-02

## Current repo status
- Main production branch remains untouched by this phase.
- Existing `storefront/order/` is the previously committed V1 customer PWA, approved red-A mascot and app icon.
- Phase 2 full tested source is delivered in the accompanying ChatGPT conversation as `GARAK_HANSANG_ORDER_V2_FULL_SOURCE_QA.zip`.
- **Phase 2 runtime files in the ZIP are NOT yet committed to this branch or deployed.** Never claim this branch's current customer app already uses the new backend.

## Phase 2 files to merge on a dedicated working branch
- `backend/domain.py`, `backend/server.py`, `backend/catalog.json`: local-only mock transactions.
- `storefront/order/ops.html`, `ops.css`, `ops.js`: merchant/hub/rider dashboard.
- `storefront/order/app.js`: optional local backend checkout, retain offline demo fallback.
- `db/001_neon_order_schema_DRAFT.sql`: SQL draft only; **not applied** to Neon.
- `tests/test_domain.py`, `tests/http_api_qa.py`, `tests/browser_qa.py`: tests.
- `docs/PHASE2_DEVELOPMENT_SPEC.md`, `docs/QA_V2.md`: specification and QA.

## Verified in local development
- 14 SQLite domain unit checks passed.
- 8 real loopback HTTP API checks passed.
- 13 Chromium DOM/mobile/desktop checks passed via inline HTML plus Python domain bridge (browser network blocked; do not call this live HTTP E2E).
- ZIP extraction + test rerun passed.

## Production gates
No real payments, actual merchant verifications, delivery proof, or public deployment. Local role header is deliberately not secure and Python demo binds to 127.0.0.1 only. Two separate Neon organizations have projects named `garakhansang`; decide the intended non-production target before any migration. Preserve the original site assets, main branch and V1 current functionality.
