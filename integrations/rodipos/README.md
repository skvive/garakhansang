# RODI POS v0.2.0 — Sydney Rocks × BunnyBear

**Status: local simulation, not a live card/payment/printing system.**

Reuses the verified architecture of `skvive/garakhansang` (static storefront / Python order-api / SQLite and Neon-ready architecture) without overwriting its source. Sydney Rocks × BunnyBear is the active customer-facing visual brand.

## Run (Python 3.11+, no external Python dependencies)

```bash
python server.py
# kiosk: http://127.0.0.1:8765/
# staff tablet preview: http://127.0.0.1:8765/staff.html
# staff token printed to terminal at startup; is local-demo-only.
python -m unittest discover -s tests -v
```

## Implemented and tested locally

- Touch-first portrait kiosk, menu categories, HOT/ICED beverage choices, quantity selection, shopping cart and price review.
- Server-authoritative pricing, unique idempotent order submissions, draft orders and payment keys.
- **Local-only mock card approval** (not real payment), atomic daily pickup number allocation, audit events.
- Authorized kitchen tablet screen, auto refresh, manufacturing state transitions and reprint queue.
- Browser demo receipt (print dialog) plus receipt print job queue for Toss Front `sdk.printer.printReceipt()` with pickup number in `additionalText`; physical device not tested.
- Skeleton Toss Front `sdk.payment.requestPayment()` bridge; requires official SDK bootstrap and merchant/device agreement.

## Hardware integration status / safety

- Toss POS Open API **does not authorize a new card transaction**. Use Toss Front Payment API through approved Front plugin and a secure device/server bridge; the custom large screen kiosk is a separate web UI.
- `RODI_ALLOW_BRIDGE_CONFIRM` defaults **off**. Never enable for commercial operation without authenticated reconciliation of authorized transaction, amount, merchant and refund capability. This prototype has no device-bound verification and must not be exposed to the Internet.
- No payment credentials in kiosk javascript. Demo card simulation endpoint is loopback only. Staff bearer token is sessionStorage only; production needs real identity, MFA and per-store RBAC, secured TLS.
- Receipts and queue numbers can be printed on **one slip** via Toss Front printer (SDK additionalText); a separate physical pickup slip requires another supported printer/driver and validation. Print jobs survive restart, use bounded retries, support reprint from staff console.
- Menu prices are **illustrative KRW demo data**, not approved BunnyBear offers. For Sydney Australia, local AUD payments and Australian-acquiring terminal availability must be contracted and verified independently. Don't assume Toss Korea SDK works on an Australian storefront.
- No mobile native APK included. Browser kiosk/touchscreen prototype is ready for native wrapper integration after hardware selection.

## API overview

|Endpoint|Auth|Purpose|
|---|---|---|
|`GET /api/catalog`|public|Demo menu|
|`POST /api/orders`|public + unique Idempotency-Key|Pending checkout, server-calculated total|
|`GET /api/orders/:id`|public order-id as capability|Non-sensitive status|
|`POST /api/demo/orders/:id/pay`|loopback demo only|Simulated approval|
|`GET /api/staff/orders`|staff bearer|Kitchen orders|
|`POST /api/staff/orders/:id/status`|staff bearer|PAID → MAKING → READY → COLLECTED|
|`POST /api/staff/orders/:id/reprint`|staff bearer|Queue another receipt|
|`GET /api/bridge/pending`|bridge bearer|New payment requests|
|`POST /api/bridge/payment-result`|bridge bearer + disabled in normal mode|SDK result recording|
|`GET /api/bridge/print-jobs`|bridge bearer|Queued/failed printer jobs|
|`POST /api/bridge/print-result`|bridge bearer|Printer job ACK/failure|

## Origin materials verified

- GitHub `skvive/garakhansang` — `storefront/cart.html`, `admin_core/server.py`, `admin_core/database.py`, project `README_START_HERE.md`.
- Google Drive `ChatGPT_Library/01_PROJECTS/SYDNEY_ROCKS/`, `SydneyRocks_BunnyBear_RELEASE_NOTES_v1.3.0_20261109.md`, `SydneyRocks_BunnyBear_UI_ERP_QA_ACTION_PLAN_v1.4.1_20261109.md`.
- Drive `렉시드개발자료/공통개발스킬` index and existing Garak Hansang folder verified.
- Toss official `https://docs.tossplace.com/faq.html`, `https://docs.tossplace.com/reference/plugin-sdk/front/payment.html`, `https://docs.tossplace.com/reference/plugin-sdk/front/printer.html`.

## Pre-production release gates

1. Confirm **Korea or Australia location**, settlement currency, and merchant identity. Validate Toss Front availability if Korea; Australia needs an authorized Australian terminal/payment provider.
2. Acquire Toss Front hardware, merchant test account and developer registration. Build proper plugin bootstrap + Template API, install on test terminal, complete certification and live pilot.
3. Implement secure short-lived device authorization, payment-key/amount reconciliation against acquirer records, cancellation/refund, crash recovery and duplicate device claim prevention.
4. Install/test network-connected receipt printer and USB/serial drivers if separate pickup slip is required. Test offline/reconnect, paper-out, duplicate print and printer ACK.
5. Replace mock menu with approved prices, allergen and tax information. Implement real Neon/RLS backend, staff login and signed order events.
6. Test tablet on LAN with HTTPS, payment terminal and actual printer; run end-to-end card test/void with merchant approval. Only then enable live mode.

## v0.2.0 (2026-11-10)

Merged enhancements into pre-existing `RODI_POS_BunnyBear_v0.1.0_20261110` without deleting that baseline: option selection, browser receipt, server-side print job retry queue, 12-way concurrent atomic queue test. Original code remains in the Drive v0.1.0 folder.
