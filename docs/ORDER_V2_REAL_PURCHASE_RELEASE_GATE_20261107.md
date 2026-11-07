# 가락한상 오더 — 실제 상품 1건 판매/배송을 위한 P4 출시 게이트 (2026-11-07)

## 확인된 실상태 (정본 vs 테스트)
- **운영 Neon** `garakhansang` main `br-ancient-cake-b34e2q55`:
  - `garak_partner_products` 37개 모두 **pending**.
  - `garak_partner_release_ready` 37건 중 `release_ready=true` **0건**. 따라서 실판매 가능한 확정 SKU는 검증되지 않았음.
  - `public.orders`의 기존 기록은 주문 소스/업종 분리가 확인되지 않아 가락한상 오더의 실매출로 간주하거나 가공하지 않음.
- **Vercel** `garakhansang`에는 `DATABASE_URL`, `NEON_AUTH_BASE_URL` 등 있으나 `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` **없음** (변수 이름의 존재 여부만 확인, 값은 열람·노출 안 함).
- **Stripe 연결** Linkrpay `livemode=true`만 확인. 다른 브랜드 결제계정으로 가락한상 고객에게 청구하지 않음.
- **Lexistyle 결제 엔진** `shinkangteam/lexistyle/src/lib/payments/stripe.ts`, `stripe-validation.ts`, `src/app/api/payments/stripe/webhook/route.ts`: USD 기반 단위 금액 및 원본 주문 스키마이므로 그대로 복사하면 KRW에서 금액 오류 발생. P4 소스는 이를 참고해 KRW 0-decimal, 정확한 금액·상인/고객/세션 대조로 재구현.
- **내비게이션** `skvive/garakland/game/navigation.mjs` 코드 재사용. 검증된 상점 GPS 없으면 가락시장 입구까지만 Google 길찾기. 고객 수령 주소에 대한 도어 투 도어 경로는 아직 미구현.
- **Android** P1L native UI는 47개 시연 메뉴, 실제 판매·로그인·PG 차단. P2 navigation branch에서는 오픈 URL 길찾기만 안전하게 추가. 실결제 APK를 출시했다고 표시하지 않음.

## 이 브랜치에서 검증한 소스 및 DB
- 브랜치 `chatgpt/garakhansang-order-p2-stripe-sandbox-roles-20261107`, PR #42: `admin_core/order_p2_sandbox.py`, `order_v2_pg_checkout.py`, 4역할 로컬 PWA/HTTP, 각 검증 테스트, 가락랜드 내비게이션.
- 별도 Neon staging `dev-garak-order-v2-20261107`, id `br-lingering-queen-b3ew4bjw`: 별도 `garak_order_v2` schema, Neon Auth Data API **authenticated SELECT 정책**, 익명/직접 쓰기 권한 없음.
- SQL 마이그레이션 `db/migrations/20261107_garak_order_v2_*.sql`:
  - 실상품 검증, 주소 앱 암호화 필요, 서버 확정 KRW 수수료, 재고 FOR UPDATE 차감·중복키 주문 멱등·30분 재고 보류
  - Stripe TEST Checkout session 1개/주문, 라이브 결제 거부, 서명 웹훅 서버 검증 후 상태 및 outbox 갱신
  - 결제가 실패했거나 세션이 없는 주문에만 재고 원상복구; 결제 확인 전 세션 유효 중 보류 취소 금지
  - Neon SQL 트랜잭션 직접 호출 검증: 테스트 2개 상품 × 12,000 KRW + 배송료 3,000 KRW = 27,000 KRW. 재호출해도 중복되지 않음, 재고 보류/반환 1회만. 테스트 완료 후 **ROLLBACK**, 원본 운영 DB 변경 없음.
- `admin_core/order_v2_pg_checkout.py`의 PostgreSQL 커넥션은 psycopg3 `dict_row`와 `%s` 인자를 사용하도록 작성. **운영 HTTP BFF 연결은 아직 미완료.**

## 1건 상용 판매/배송을 위한 필수 순서
1. 판매 상점 1곳 **사업자/입점 계약, 원산지/포장/알레르기/규격/판매 사진/가격/재고/품절/냉장 배송** 승인. `garak_partner_release_ready`를 확인하고, 실판매 가능 SKU만 신규 order v2 상품으로 매핑. 임의 승인/시연 사진/테스트 가격 공개 금지.
2. 배달 가능 **우편번호/거리·시간대, 배송비/최저 주문, 배송 주체·실라이더/제휴사/긴급 연락** 확정. 좌표·출발/도착 개인정보와 위치 동의.
3. 운영 BFF: Neon Auth Google/휴대폰 토큰 서명검증, 계정 권한(상인/고객/라이더/관리자), 서비스 가능 권역 및 SKU 재검증, 주소 암호화, `reserve_trusted_order`과 Stripe TEST 세션을 원자/멱등 처리, outbox 수신자 라우팅, 이중 배차 방지.
4. 해당 브랜드의 **Stripe TEST** 계정/키/웹훅 별도 연결 → 실제 Stripe 테스트 카드 승인/취소/거절/3DS/환불/일부 환불/중복웹훅 및 타임아웃 E2E. KRW 지원·결제 사업자 계약 및 한국 배송 상점 적격성 확인.
5. 고객·상인·라이더 **실기기** 흐름(주문 → 카드테스트 → 상인접수 → 라이더배정/픽업 → 수령인 배송완료 → 영수증/정산)과 FCM 알림·위치정확도·거부/지연/취소 회귀를 확인한 뒤 별도 운영 승인.
6. 모두 통과 시 실결제 키/실상품/실배차 및 Google Play AAB 배포를 **최소 1개 실상품에 대해 단계적으로 활성화**. 별도 운영 승인 및 분리된 정산/환불 대사 필수.

## 상태 판정
- 자동화 코드 및 synthetic E2E: 준비/일부 CI 검증.
- Neon staging 재고·주문 트랜잭션: 직접 SQL QA 통과.
- 실제 승인 상품: **0/37**, 상용 전환 불가.
- 운영 Stripe 계정 연결: 미확인/키 미설정. 실제 Stripe 카드 승인 E2E **미실행**.
- 라이더 GPS 실시간 지도, 실서비스 배송·푸시, Android Native 주문 API: 미완료.
- **GO-LIVE NO**. 이 문서는 미완료를 완료로 표기하거나 운영 데이터/상품/결제 설정을 임의로 변경하지 않는다.
