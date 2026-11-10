# RODI POS v0.1.0 — Sydney Rocks × BunnyBear

**Status: functional LOCAL DEMO / no live card transactions.** Built from patterns verified in `skvive/garakhansang` V9 local order/admin data flow and uses the brand direction in Sydney Rocks × BunnyBear v1.3 / v1.4 documents. Original sources remain unchanged. Menu names and prices are UI fixtures, not approved commercial offers.

## Run

- Windows: double-click `RUN_WINDOWS.bat` (requires Python 3.11+).
- macOS / Linux: `./RUN_MAC_LINUX.sh`.
- Customer touchscreen: http://127.0.0.1:8765/
- Staff kitchen tablet emulator: http://127.0.0.1:8765/staff
- Staff demo access key: `local-demo-staff` (change via `RODI_STAFF_KEY` env before accessible network binding).
- Receipt: printed from order-success view using native browser printing; printer driver/USB pairing is a separate deployment step.
- Run offline automated tests: `python -m unittest discover -s tests -v` (9 automated integrity tests).

**For demo only**: `RODI_MODE=demo` is required (default). The live mode is deliberately blocked by the entrypoint. Every physical `/api/terminal/*` endpoint additionally rejects demo requests (403) to prevent accidental card-terminal activation. To allow other LAN devices to view the staff tablet, run with `--host 0.0.0.0`, but avoid untrusted networks and use a strong staff key; this prototype has no HTTPS, managed roles, or audited card-provider reconciliation. Browser print is NOT the Toss Front printer API.

## Implemented

1. Large touch targets, mobile/tablet responsive menu and basket with optional temperature for drinks.
2. Server-controlled pricing, idempotency key, SQLite WAL order persistence, order-created event.
3. **Demo card payment**, queue number assigned atomically after simulated success; repeated callbacks do not produce another number.
4. Invoice/order ticket in browser print layout with numbered queue; stand-alone POS printer NOT tested.
5. Staff tablet panel: polling every 2s, status `queued -> preparing -> ready -> collected`, protected with staff access key.
6. Separate official Toss FRONT plugin adapter skeleton in `terminal/`, including `payment.requestPayment` and `printer.printReceipt` mapping, not installed, not tested on hardware.

## Real Toss FRONT implementation — gated

The recommended topology is **RODI kiosk web UI -> RODI order server -> Toss FRONT SDK plugin -> Toss FRONT VAN card reader + printer**, with a separate authenticated kitchen tablet. Tossplace Open API only queries already-existing orders/payments and **cannot approve card payments**. See:

- https://docs.tossplace.com/guide/front-integration/plugin/develop/partner-integration-guide.html
- https://docs.tossplace.com/reference/plugin-sdk/front/payment.html
- https://docs.tossplace.com/reference/plugin-sdk/front/printer.html
- https://github.com/tossplace/toss-front-plugin-template

For production, clone the official Toss Front plugin template (don't install `terminal/toss-front-bridge.js` alone), initialize its actual `sdk`, register ACL/server domain, pair to test merchants and devices, verify terminal capability, pass Toss review, add signed result and reconciliation and refund logic, robust job leasing, printer retry queue, HTTPS, per-device credentials and server audit. Read the provider docs for compliance with country/merchant/currency constraints. This prototype uses **KRW** as an assumed Korean pilot currency; **Australian in-person payments via Toss FRONT are not verified**. No secrets/API keys are included.

**Critical:** Testing cards on physical Toss FRONT may cause real approval even in development; follow provider guidance and cancel approved test transactions. Demo mode is the safe default.

## QA acceptance matrix

| Scenario | Demo | Physical device / production |
|---|---|---|
| Tap menu/add/remove/multiquantity | Implemented | Touchscreen human QA required |
| Server amount cannot be overwritten by client | Unit tested | Live pricing approval required |
| Duplicate checkout uses same idempotency key | Unit tested | Network stress test needed |
| Failed payment yields no queue number | Unit tested | Provider response test needed |
| Duplicate success never creates second ticket | Unit tested | Duplicate webhook/device test needed |
| Cash register pays and prints | Simulated payment + browser print | Toss VAN + hardware receipt unverified |
| Tablet sees paid orders | Polling | Multi-device LAN/wifi QA needed |
| Staff transitions enforce order state | Unit tested | Staff device access management needed |
| Refunds/discounts/taxes/settlement | Not implemented | Required before operations |

## Structure

```text
server.py            Python stdlib HTTP + SQLite prototype
web/index.html       Customer kiosk UI
web/staff.html       Staff/KDS UI
web/receipt.html     Browser print slip
web/*.js,app.css     Client logic and responsive design
terminal/            Toss FRONT SDK adapter placeholder (not certified)
tests/test_pos.py    Offline transaction integrity tests
```

RODI POS is a new branded POS/KDS module; it does not overwrite any `skvive/garakhansang`, `skvive/garak`, `skvive/garakland`, Sydney Rocks site, or their Neon production database.
