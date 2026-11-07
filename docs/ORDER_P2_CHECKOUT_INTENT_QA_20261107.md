# 가락한상 오더 P2 — 중복 주문 방지·견적 스냅샷 원장 검수

기준: 2026-11-07 · **LOCAL BETA / GO-LIVE NO** · 사용자 원본 상품 및 기존 배포본 보존.

## 소스 정본·재사용

- Drive `ChatGPT_Library` 및 `렉시드개발자료/공통개발스킬/가락한상`의 기존 브랜드·공통 스킬과 `가락한상 오더 통합 개발명세서 v1.3` 확인.
- GitHub `skvive/garakhansang`의 `admin_core/database.py`, `mobile_commerce.py`, `product_options.py`, 기존 `orders` 시뮬레이션과 `delivery_flow.py` 상태 머신 재사용.
- Neon 기존 `garakhansang` 프로젝트는 `public.garak_partner_products`, `garak_partner_release_ready`, `neon_auth` 정본 재사용. 2026-11-07 조회 결과 `GYS-011..047` 37개는 Android #11..47과 번호·명칭·가격이 전부 일치하지만 **37개 전부 승인대기/미노출/판매불가/재고0**. 기존 운영 데이터는 수정하지 않음.
- GARAK `skvive/garak` P1M PR #9: Neon 승인 상품 GET 및 원화 견적 POST 읽기 전용, 상용 결제 경로 없음.

## 이번 P2의 기능

| 항목 | 구현 | 제한 |
|---|---|---|
| 원장 테이블 `checkout_intents` | 기존 SQLite 로컬 베타 스키마에 **추가만 함** | 기존 `orders` 및 재고 미변경 |
| 등록 `POST /api/admin/order-intents` | 로그인·CSRF·`Idempotency-Key` 검증, 현재 승인 가격/옵션 계산, 원화 견적과 판매자 ID 스냅샷 | `GARAK_ORDER_SANDBOX=1` 및 SQLite에서만 허용 |
| 중복 클릭·네트워크 재시도 | 작성자+멱등키 UNIQUE, 동일 본문 기존 결과(200), 다른 본문 충돌(409) | 테스트 케이스 병렬 요청 포함 |
| 읽기 `GET /api/admin/order-intents[/{ref}]` | 작성자 격리·최고관리자 전체 감사 조회 | 고객/상인 실주문 정보가 아님 |
| 종료 `POST /api/admin/order-intents/{ref}/abandon` | 작성자만, 조건부 버전 갱신, 중복 종료 방지 | PG 환불/실주문 취소와 무관 |
| 운영센터 페이지 `/admin/order-intents.html` | 반응형 표·상품/수량·개발 견적 생성·검수 종료 | 운영용 판매 알림, 주문 수락 UI 없음 |
| CI | 주문 원장 테스트 17개 2회 + 기존 Android 15/16 에뮬레이터 회귀 | PR/배포 상태는 CI 종료 후 보고 |

### 검증 규칙

```text
Admin Auth + CSRF + LOCAL_BETA guard
       ↓
client { items, delivery_type } + Idempotency-Key
       ↓
request sha256 → (actor_id, key) 선조회
       ├─ 기존 동일 요청 → 기존 reference/quote 반환
       ├─ 기존 다른 요청 → HTTP 409
       └─ 최초 요청 → 서버 제품 검증 및 quote_cart()
                             ↓
                checkout_intents(지불 불가 상태)
                status = awaiting_delivery_policy
                payable_total_krw = null
                checkout_enabled = false
                             ↓
            Commit 완료 후 HTTP 201 + 감사 로그
```

실주소·고객 실명·휴대전화·카드정보·PG 시크릿을 이 원장에 저장하지 않습니다. 실제 주문/결제/상인 알림을 발생시키는 라우트도 열지 않습니다. 시뮬레이션 원장과 기존 `orders` 운영 데이터는 혼합하지 않습니다.

## 운영 전 단계별 결제 게이트

1. 기존 Neon Auth 조직과 가락한상 상점 소유권/상인 라이더 역할·RLS 검증. 주문은 익명 관리자 세션이 아닌 실제 구매자 권한으로 생성되어야 합니다.
2. 고객 배송지 동의·배송권역·배달료·최소주문·쿠폰 정책을 연결한 뒤 **결제 가능한 최종 원화 금액을 계산**합니다.
3. 운영상품의 옵션/가격/재고 승인 및 가격변동·품절 경합·재고 예약 만료, 주문 생성 멱등성까지 DB 조건부 트랜잭션으로 보호합니다.
4. Stripe/Toss **PG 테스트 키**와 저장된 금액/통화/상인/주문 참조를 대조하고 검증된 웹훅 이벤트로 결제 상태를 전환합니다. redirect 성공화면만으로 결제 상태를 확정하지 않습니다.
5. 이벤트 outbox에서 결제완료 후에만 상인 대상 새 주문 알림. 상인 수락/조리/픽업 준비/배달요청, 배달기사 배정·위치·수령을 역할별 상태/버전으로 제한합니다.
6. 취소·부분 환불·중복 웹훅·배차 미응답·휴무·품절·배송 실패·정산 대사와 Android 물리적 실기기 테스트 통과 후 운영 승인.

**안전 상태:** APK의 시연 장바구니는 로컬 카탈로그, 운영 Neon SKU 37개는 준비중 판매불가이며 새 원장은 별도 관리자 검수용입니다. 실제 고객 돈·배송지·상품 출고는 처리하지 않습니다.

## 리포 구조

- `admin_core/order_intents.py`: 멱등 원장 도메인.
- `admin_core/database.py`: `checkout_intents` 추가.
- `admin_core/server.py`: 베타 전용 관리자 HTTP API, CSRF·origin·role·sandbox guard.
- `storefront/admin/order-intents.html`: 주문 검수 전용 화면.
- `tests/test_order_intents_p2.py`: API E2E/경합/권한·취소·원본 불변 검증.
- `.github/workflows/order-android-p1h.yml`: Android 15/16 실에뮬레이터 및 P2 계약/JS 문법 검증.

**주의:** 현재 P2는 샌드박스 원장이며 Stripe/Toss 결제, FCM, 지도/라이더, 운영 배포·실기기(물리폰)는 별도 개발 및 검증이 필요합니다.
