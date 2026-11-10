# RODI POS v0.1.0 — QA EVIDENCE (2026-11-10)

## Sources & permissions
- GitHub `skvive/garakhansang` main inspected read-only (admin and push capabilities observed); original site and payment sources untouched.
- Drive Sydney Rocks BunnyBear brand book/release notes and ChatGPT_Library source tree verified; V9 local beta order/auth patterns reused conceptually, not copied without testing.
- Drive `렉시드개발자료/공통개발스킬` examined; no direct certified Toss FRONT POS implementation available.
- LinkNode billing assets identified but not used as physical-card driver.

## Automated tests — PASS 9/9
- Server recomputes price ignoring client amounts.
- Checkout idempotency key reuses same order.
- Invalid quantity and options rejected.
- Queue number issued exactly once after simulated success.
- Failed payment does not issue queue number.
- Wrong callback payment key blocked.
- Kitchen display state transitions enforced.
- Cancelling unpaid cart keeps it out of payment queue.
- Receipt print logging requires paid order.

`python -m unittest discover -s tests -v`: 9 tests OK.
`node --check web/kiosk.js`, `web/staff.js`, `terminal/toss-front-bridge.js`: PASS.
`python -m py_compile server.py`: PASS.

## HTTP integration — PASS (127.0.0.1:8768)
- `GET /api/menu` 200, 8 demo items.
- `POST /api/checkout` 201, server-controlled order created.
- Unauthenticated `GET /api/staff/orders` 401.
- Physical Toss terminal endpoints return 403 in demo mode, even when called explicitly.
- `POST /api/demo/approve` 200, queue issued.
- Staff-authenticated tablet fetch sees paid order, status transition -> preparing 200.

## NOT verified / release blockers
- No real Toss FRONT or merchant credentials, partner review, approval, refund, terminal SDK auth or receipt printer physically exercised.
- No production Neon DB provisioned and no distributed transactions; SQLite local-demo only.
- No browser rendering/pixel-level QA; automated Chromium navigation blocked by runtime policy. Manual touchscreen checks still required.
- No verified beverage recipe prices, local tax, allergy labeling, commercial menu data, privacy policy or Australian payment eligibility.
- Browser print is OS print dialog; automatic silent physical printing needs kiosk OS/printer service or certified Toss FRONT plugin.
- DEMO ONLY. Never accept real payments from current app. Live mode intentionally blocked, do not bypass gating without end-to-end approval and reconciliation.
