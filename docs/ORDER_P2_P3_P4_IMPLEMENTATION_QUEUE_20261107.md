# 가락한상 오더 — P2 결제 샌드박스 + 4역할 배달 플랫폼 구현 대기열 (2026-11-07)

> **NOT LIVE.** 이 브랜치는 P1L 상품/장바구니/견적 코드를 기반으로 하고 운영 `main`, 기존 P1K APK, 데이터베이스, 실사용자, 실결제, 실제 배차를 변경하지 않습니다.

## 검증된 재사용 원본

- `skvive/garakhansang` P1L: `admin_core/mobile_commerce.py`는 승인 상점/상품·서버 기반 장바구니 견적, `admin_core/delivery_flow.py`는 역할·상태별 변경과 알림을 정의. 고객 Android는 상품 상세·장바구니·주문서 미리보기까지.
- `skvive/garakhansang/storefront/admin/`: 관리자 베타 UI와 현재 `storefront/merchant/dashboard.html` 참고; 상인별 RBAC는 아직 실제 인증되지 않음.
- `shinkangteam/lexid/src/lib/stripe.server.ts`: Stripe Checkout KRW zero-decimal(원 단위 unit_amount), 서버 가격 검증 및 테스트/라이브 모드 구분. 기존 `src/routes/api.stripe.webhook.ts`의 서명 검사 구조 참조; 실제 `markOrderPaid`가 추가 금액·주문 검증이 필요하므로 그대로 이식 금지.
- `skvive/garak`의 Stripe draft PR #8 결제 확정 보안 강화 원칙 참조.
- Drive `ChatGPT_Library`, `렉시드개발자료/공통개발스킬`, `가락한상오더_안드로이드_통합개발명세서_v1_3_20261104.md` 우선.
- 연결 Stripe는 현재 **Linkrpay 라이브 컨텍스트만 확인**. 실제 Stripe test key·test webhook signing secret이 연동됐다고 주장하지 않는다.

## 이 브랜치에서 작성한 실제 소스

`admin_core/order_p2_sandbox.py`:
- 전용 SQLite 일회성 샌드박스 스키마 (`p2_sandbox_orders`, `p2_sandbox_events`, `p2_sandbox_outbox`), 기존 주문·정산·고객 DB 분리
- 고객 principal 필요 + 서버 산출 `quote_cart` 결과만 주문 초안으로 허용; 고객별 멱등키/스냅샷/원화 합계 검증. **재고 예약 및 서비스 가능 권역 검증은 미연결.**
- `sk_test_`만 허용하는 Stripe-hosted Checkout 세션 어댑터. `krw` 원 단위, 서버 최종금액, 주문·매장 메타데이터 전달. `create_session`을 주입한 모의 응답으로 오프라인 검증. **실 Stripe API 호출 없음.**
- Stripe-Signature HMAC SHA256 원문 검증, 5분 타임스탬프 범위, event ID 중복 기록, test `livemode=false`, 세션 ID/고객/매장/통화/원화 금액/결제 상태 검증을 모두 만족해야 `payment_pending -> paid`. 결제 완료 URL 복귀만으로 결제확정 금지.
- P1L `delivery_flow.transition` 재사용, 주문 `version` 비교 및 조건부 업데이트, 승인 라이더 ID 주입 검증, 타 상인/고객/미배정 라이더 주문 접근 차단
- 역할별 알림 **DB outbox** 및 역할별 dashboard 조회 구현; 아직 실제 웹 컨트롤러, 로그인, FCM, 앱 푸시, 배달지도에 연결하지 않았음

`tests/test_order_p2_sandbox.py`: 서명 위조, 이벤트 재전송·중복, 미결제/금액·통화·상인·세션 불일치, 라이브 키/세션 거부, 역할 접근 제한, 배송 상태 전이, 중복 라이더 수락, 오래된 버전 거절 테스트.

## 주요 페이지·역할·승인 게이트

| 영역 | 고객 Customer | 입점상인 Merchant | 라이더 Rider | 운영 Admin/Ops |
|---|---|---|---|---|
| 초기화 | 지역/주소·로그인·권역 | 사업자등록·정산계좌·승인 | 본인/차량/활동 권역·심사 | 상인·라이더 승인/정지·감사 |
| 상품/장바구니 | 상품 상세·사진/규격·원산지/알레르기·옵션·수량/쿠폰·최종견적 | 자기 매장 메뉴·재고·영업시간·품절·프로모션 | 배달 가능 구역/근무상태 | 품질/사진/규정/가격 승인 |
| 주문 | 결제/포장/배달·취소·영수증·내역·리뷰 | 수락·거절·조리 ETA·픽업준비 | 배차 수락·픽업/배달완료·증빙 | 거래·배차 모니터, CS/환불 |
| 정산/통계 | 고객의 영수증만 | 자기 주문 수수료/정산 | 자기 배달비·명세/정산 | PG 대사·정산 승인·수수료·분쟁 |

## 이벤트 알림 설계

| 서버 검증 이벤트 | 알림 수신자 | 채널(출시 시) |
|---|---|---|
| `payment_verified` | 해당 상인 | 앱 알림함 + FCM, 재시도/미열람 경보 |
| `merchant_accept`/`prepare`/`ready` | 해당 고객 | 고객 앱 + FCM |
| `merchant_request_dispatch` | 승인된 해당 권역 라이더 후보 | 라이더 앱 대기 카드 + FCM(PII 없이) |
| `rider_accept` | 해당 상인 + 고객 | 상인/고객 상태 알림 |
| `pickup`/`in_transit`/`delivered` | 해당 고객 | 주문 상태 화면 + FCM |
| `refund_pending`/`dispatch_timeout`/`delivery_failure` | 관리자/CS + 해당 고객 | 운영 이슈 큐 + 최소 정보 알림 |

현재 P1L domain은 이벤트당 알림 토큰 한 개만 발행하므로, 여러 수신자에 대한 라우팅 확장/전송/재시도는 P3 완료 조건으로 남긴다. 앱은 실서비스 알림이 전송됐다고 표시하면 안 된다.

## 단계별 개발·수용 기준

- [x] P1L 기준 확인: 고객 상세·수량·장바구니/서버 견적/도메인 주문 상태, 에뮬레이터 API35/API36 PASS (PR #41은 미병합).
- [x] P2-A: 실제 돈이 움직이지 않는 테스트 전용 원장·KRW Stripe 세션 파라미터·서명 웹훅·금액검증·역할별 주문/알림 아웃박스 순수 모듈 및 회귀 테스트.
- [ ] P1M: 실 SKU/배송권역/배달료/옵션/원산지/상인 계약/Neon Auth+RLS, DB 스키마 변경 전 현재 데이터 및 백업 확인.
- [ ] P2-B: Stripe 샌드박스 별도 키/웹훅/테스트모드 계정, 분리된 staging Neon 브랜치, HTTP endpoint과 앱 외부 브라우저 콜백 연결, 실제 Stripe 테스트 카드 이벤트·취소·환불 E2E; 실결제 기본 OFF.
- [ ] P3-A: `/merchant` 역할별 대시보드(입점·메뉴/품절·영업시간/주문접수·배달요청·정산), 내 매장 데이터만 RLS.
- [ ] P3-B: `/rider` PWA/Android 설치형(심사·근무/배차·픽업·배송·증빙·길찾기/ETA), 승인·배정 외 주소/전화번호 노출 금지, 동시 배차 검증.
- [ ] P3-C: 이벤트 outbox 영속화, FCM/웹 실시간 알림, 로그인 세션/토큰 회전, 수신자별 최소 정보, ack/retry/dead-letter/미응답 타임아웃.
- [ ] P4: 관리자 통합 운영/매장 및 라이더 승인/주문·결제·환불·배차·정산·CS/개인정보 열람 감사/BI.
- [ ] P5: 결제/권한/푸시/지도의 실제 단말 E2E, 모든 페이지 360~600dp/태블릿/접근성·클릭·화면회전·오프라인/복구 QA, 서명 AAB/Google Play/법률·입점·배달 SLA.

## 안전·출시 금지 조건

운영 결제 활성화는 **정확한 실상품·재고·배송권역/요금·동의/취소·환불·PG 서비스 제공 대상 국가/통화/실계약·전자상거래 고지·상인/라이더 승인·Neon Auth와 RLS 검증** 후 별도 릴리스. 현재 구현은 **테스트 전용 모듈**이고 API 엔드포인트나 Android APK에 자동 연결되지 않는다. Google Play 출시·실 Stripe TEST 결제·실기기 검증을 완료했다고 주장하지 않는다.
