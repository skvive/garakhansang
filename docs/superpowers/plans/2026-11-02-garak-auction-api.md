# Garak Auction API Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish verified Garak Market auction results on the Garak Hansang price page with daily fail-closed refreshes and no confusion with KAMIS reference prices or merchant sale prices.

**Architecture:** Add a separate Garak auction collector and dataset instead of changing the existing KAMIS collector. The collector consumes the Garak Corporation LINK API only after approval, validates market/source/date/unit/price/quantity fields, preserves the last known good file on every failure, and exposes a distinct UI panel. Credentials remain GitHub Actions secrets and the workflow stays disabled-by-skip until all required values are configured.

**Tech Stack:** Python 3.12 standard library, XML, GitHub Actions, static HTML/CSS/JavaScript, `unittest`.

**Spec:** `GARAKMALL_WORK_START_PROMPT_20261102.md` and `docs/DAILY_SEAFOOD_PRICE_SOURCE.md`

## Global Constraints

- Base new work on current `main`; do not overwrite the existing KAMIS collector or account/login changes.
- Never label KAMIS Seoul wholesale reference prices as Garak Market auction prices.
- Never publish sample, stale, empty, unauthenticated, or unitless data.
- Keep API ID, password/authentication number, and service data ID in GitHub Actions secrets only.
- Preserve item, variety, unit, grade, auction price, quantity, corporation, origin, trade date, and provider attribution.
- Do not convert mixed package units to kilograms unless the official response explicitly supplies a verified conversion.
- Do not merge or deploy until at least one approved live response is cross-checked against the provider output.

## Review Focus

- Authentication or approval error must exit non-zero without replacing the last known good JSON.
- Empty/holiday responses must not be treated as a successful zero-price day.
- Pagination must stop exactly at the reported total count and must reject repeated pages.
- Agricultural-only corporation codes must not be presented as proof of seafood coverage.
- UI must reject future dates, data older than 14 days, missing units, non-positive prices, and non-Garak source markers.

---

### Task 1: Garak auction XML contract

**Files:**
- Create: `tests/test_sync_garak_auction.py`
- Create: `tools/sync_garak_auction.py`

**Interfaces:**
- Consumes: Garak XML fields `list_total_count`, `PUMMOK`, `PUMJONG`, `PUM_NAME_IMSI`, `UUN`, `DDD`, `PPRICE`, `SSANGI`, `CORP_NM`, `ADJ_DT`, `QTY`, and `INJUNG_GUBUN`.
- Produces: `parse_page(content: bytes, expected_date: date) -> tuple[int, list[dict]]` and a versioned verified dataset.

- [ ] **Step 1: Write failing tests** for valid rows, authentication error, malformed XML, missing unit, invalid price, mismatched date, and missing quantity.
- [ ] **Step 2: Run the focused test** and confirm it fails because the new module is absent.
- [ ] **Step 3: Implement the minimal parser and validators.**
- [ ] **Step 4: Run the focused test and the existing KAMIS test.**
- [ ] **Step 5: Commit parser and tests.**

### Task 2: Approved live fetch and fail-closed publication

**Files:**
- Modify: `tests/test_sync_garak_auction.py`
- Modify: `tools/sync_garak_auction.py`

**Interfaces:**
- Consumes: `GARAK_API_ID`, `GARAK_API_PASSWORD`, `GARAK_API_DATA_ID`, and explicitly verified `GARAK_CORP_CODES`.
- Produces: `storefront/data/garak-seafood-auction-latest.json` via an atomic replacement only after all pages validate.

- [ ] **Step 1: Add failing tests** for query construction without secret logging, multi-page aggregation, repeated-page rejection, empty response, and atomic last-known-good behavior.
- [ ] **Step 2: Verify the tests fail for the intended missing behavior.**
- [ ] **Step 3: Implement HTTPS fetch, pagination, explicit corporation filters, and atomic publication.**
- [ ] **Step 4: Verify focused and repository test suites.**
- [ ] **Step 5: After approval, run one live request and record only redacted structure, row count, trade date, unit examples, corporation, and item examples.**
- [ ] **Step 6: Commit only after the live schema matches the parser or adjust with another red-green cycle.**

### Task 3: Daily workflow and secret gate

**Files:**
- Create: `.github/workflows/daily-garak-auction.yml`
- Modify: `tests/test_sync_garak_auction.py`

**Interfaces:**
- Consumes: the four GitHub Actions secrets/variables approved in Task 2.
- Produces: a daily/manual workflow that skips safely when unconfigured and commits only a verified changed dataset.

- [ ] **Step 1: Add a failing workflow contract test** for required secret gates, least-privilege contents write, concurrency, timeout, and no secret-bearing URL output.
- [ ] **Step 2: Verify the contract test fails before the workflow exists.**
- [ ] **Step 3: Add the workflow with manual dispatch and a schedule set after the provider publication time is verified.**
- [ ] **Step 4: Run tests and perform one manual workflow dispatch after secrets are configured.**
- [ ] **Step 5: Record the workflow run ID, actual start time, result, and produced commit SHA.**

### Task 4: Distinct Garak auction UI

**Files:**
- Modify: `storefront/assets/js/official-prices.js`
- Modify: `storefront/assets/css/official-prices.css`
- Modify: `storefront/prices.html`
- Create or modify: UI contract tests following the repository's existing static QA pattern.

**Interfaces:**
- Consumes: the verified Garak dataset and the existing KAMIS dataset.
- Produces: clearly separate `가락시장 경락가격` and `KAMIS 서울 도매 참고가격` sections with dates, units, corporations, source links, and safe no-data states.

- [ ] **Step 1: Add failing UI tests** for source flags, stale/future dates, missing unit, XSS escaping, and labeling boundaries.
- [ ] **Step 2: Verify the tests fail for the new Garak panel.**
- [ ] **Step 3: Implement the smallest UI change that passes.**
- [ ] **Step 4: Verify at 390px, 768px, and 1280px and run the full suite.**
- [ ] **Step 5: Commit the UI change.**

### Task 5: PR, deployment, and evidence

**Files:**
- Modify: `docs/DAILY_SEAFOOD_PRICE_SOURCE.md`
- Create: `docs/GARAK_AUCTION_API_VERIFICATION_20261102.md`

**Interfaces:**
- Consumes: approved application status, redacted live-response evidence, workflow run, commit SHA, and production verification.
- Produces: auditable deployment evidence with no secret values.

- [ ] **Step 1: Document approval state, approval/reference number, verified fields, unit examples, market/corporation, and unresolved coverage limits.**
- [ ] **Step 2: Run the full automated suite and browser QA.**
- [ ] **Step 3: Open a PR from the dedicated branch; do not merge while approval/live data remains unverified.**
- [ ] **Step 4: After review, merge and verify the production page against the same live trade date and units.**
- [ ] **Step 5: Record deployment SHA/URL and remaining blockers.**
