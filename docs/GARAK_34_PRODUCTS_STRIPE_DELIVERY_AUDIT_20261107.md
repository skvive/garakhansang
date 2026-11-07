# 가락한상 오더 34개 상품 승인 · Stripe · 실제 배송 연동 검증 결과
기준: 2026-11-07 KST | **READ-ONLY 운영 DB 및 연결계정 검증** | 운영 상품/PG/배송 상태 변경 없음

## 운영 DB 점검 (Neon garakhansang)
운영 프로젝트 `mute-darkness-67529424` / 기본 브랜치 `br-ancient-cake-b34e2q55`.
- `public.garak_partner_products`: **37건 전부 merchant_slug=gwangyang-fisheries**, SKU **GYS-011 ~ GYS-047**. `status='pending'` 37/37; `approved=0`; `visible AND purchasable=0`.
- 모든 상품에 `price_krw>0` 참고 가격 존재하나 **재고 `stock>0` 0/37**. 실물 사진 `image_verified=true` **0/37**. 이미지 경로는 `images_800/*.jpg` 샘플/시연용이며 실제 증빙이 승인된 HTTPS 링크가 아님. 예: GYS-046은 QA 노트에서 쥐치 실물 사진으로 교체를 요구.
- `public.garak_partner_categories`: **9건 모두 pending**.
- `public.garak_partner_evidence`: **전체 0행**; 상인 공통 증빙 8종, 상품별 증빙 4종 미제출/미검증.
- `public.garak_partner_release_ready`: 37건 중 **TRUE=0**. 현재 정확히 어떤 SKU 34개가 승인 대상인지 확인할 수 있는 별도 선택 내역·제외 3개 명세를 발견하지 못함. 따라서 **임의로 GYS-011 ~ GYS-044 등을 '승인한 34개'로 간주하지 않음**.

### 기존 운영 승인 규칙
**상인별 8종 검증 완료 필요:** `business_registration`, `signed_merchant_contract`, `photo_usage_rights`, `cold_chain_plan`, `shipping_fee_policy`, `returns_refund_policy`, `pg_settlement_reconciliation`, `pg_refund_rehearsal`.

**상품별 4종 검증 완료 필요:** `product_real_photo`, `product_origin_weight`, `product_price_agreement`, `product_stock_confirmation`. 가격 합의는 72시간 이내, 재고는 24시간 이내 재확인. 추가로 카테고리 승인·가격 >0·재고 >0·실물 사진 이미지 검증 및 HTTPS 이미지 경로·상품 승인/판매 노출 상태 필요. 규칙은 기존 운영 view 정의에서 직접 확인.

**판정:** `34 approved`는 현재 **0/34**. 안전한 판매/주문 가능 항목 0/37. 증빙 생성·SKU 목록 추정·상품 status 일괄 UPDATE 실행하지 않음.

## Stripe 결제 설정 검증
- 현재 연결된 Stripe 컨텍스트는 **`Linkrpay` / `acct_1T4EQyR4SlZGfHAe` / `livemode:true` 1개**. 가락한상 전용 Stripe 컨텍스트 없음. 타 브랜드 계정으로 고객에게 실청구하지 않음.
- Vercel `garakhansang` 환경변수 전체 10개 이름(개발/미리보기/운영) 중 Stripe 키, webhook secret, `GARAK_*PAYMENT*` 설정이 없음. 운영 `DATABASE_URL`·`NEON_AUTH_BASE_URL` 이름은 있으나 이 사실만으로 실제 주문·결제 연동이 이루어졌다고 볼 수 없음.
- `admin_core/order_p2_sandbox.py` / `admin_core/order_v2_pg_checkout.py`: **`sk_test_` 테스트 Checkout**, KRW 정수, 서버 금액/상인/고객 대조, 서명 테스트 웹훅과 중복방지 코드는 검증. 실제 Stripe 테스트 계정에서 카드 결제, 3DS, 환불 및 지급/정산은 **미검증**.
- 별도 Stripe 계정/권한 연결: https://access.stripe.com/mcp/oauth2/authorize/sessions/oases_VX1aCLVlHbuWvK (계정 관리 연결을 위한 사용자 인증 화면; 만료 시 재발급 필요). 연결 후 명의/사업자 적격성·TEST 계정·결제 메서드·KRW/한국 발행 카드·웹훅 검증, 사업자 계정과 판매자 자금 귀속/분쟁 책임 확인.
- Stripe 공식 국가별 적격성 확인: https://stripe.com/global ; 한국 고객 대상 현지 카드/지갑 지원과 한국 소재 사업자가 독자적으로 Stripe 계정을 발급할 수 있는지는 **별개**. 공식 근거: https://support.stripe.com/questions/requirements-to-open-a-stripe-account-in-another-country , https://stripe.com/payment-method/korea .

## 실제 배송 연동 검증
- `admin_core/delivery_flow.py`: 상태머신/역할 검사, 상인→라이더→배송완료 알림 대상은 있으나 파일 상단에 **`No PG/FCM/Maps side effects here`**. 이 자체로 외부 배송업체 배차 API 호출·정산·추적·위치전송을 수행하지 않음.
- `admin_core/order_lab_server.py`: 고정 2,000원 **합성 테스트 배송료**. 실제 배달사/실시간 배달 요금/냉장 포장·온도 확인/고객 배송지/라이더 근무·동의/배송 완료 증빙 연동 없음.
- 기존 `api/index.py`는 `admin_core.server.Handler` / `runtime/garak_beta.sqlite3`를 사용. 개발 중인 주문 V2 Neon 어댑터/라이더 PWA는 **프로덕션 서버의 결제·배송 API와 연결되지 않음**.
- Vercel 프로젝트 10개 환경변수에서 배달업체 자격증명/콜백 비밀키가 확인되지 않았고, 관련 Google Drive 실배송 계약·API 자격증명도 확인되지 않음. 외부 배달사에 실제 배차 요청하거나 개인정보 전송하지 않음.
- 국내 배송대행 제휴 실무 후보: 바로고는 공식 발표에서 배달앱/POS API 제휴를 안내(https://www.barogo.com/detail-news/201), 하지만 가락한상 계약/승인/배차 API 키·테스트 허용/냉장 수산물 취급 SLA **미확인**. 후보 서비스는 실제 연동 완료로 간주 금지.

## 이번 개발 브랜치 추가
- `admin_core/partner_release_audit.py`: **34개 SKU 명시 필수**, 선택된 SKU 중 누락/중복/카테고리/재고/사진/12종 증빙/기간 만료 확인. Stripe 명의/서명 TEST와 배송업체 계약·실배차 E2E가 모두 성공해야 서비스 활성화 준비 상태로 인정. **쓰기 기능 없음**.
- `tests/test_partner_release_audit.py`: 검증 완료된 합성 SKU 34개를 사용해 구조·예외를 **10개 단위 테스트**로 검증. 합성 샘플을 실제 판매 승인으로 간주하지 않음.
- 기존 27개 Python API/도메인 테스트 및 지도 JS 회귀와 함께 GitHub Actions **SUCCESS**: https://github.com/skvive/garakhansang/actions/runs/42363528997 . 이 녹색은 검증 로직을 확인한 것이고 실제 Stripe 카드 결제/실배송이 수행됐다는 증명이 아님.

## GO/NO-GO 및 다음 입력
- **상용 판매 승인 34개: NO (0개)** — 대상 34개 SKU ID / 제외할 3개를 명시하고 상인 8종 및 상품별 4종 증빙, 승인 사진, 가격/실재고를 등록.
- **Stripe: NO** — 가락한상 판매자가 실제 사용 가능한 Stripe 계정(사업자 소재 국가/명의/정산계좌 포함)을 연결, *TEST* Checkout/웹훅/결제·환불 대사를 수행. 검증 전 live charge/refund 불가.
- **실배송: NO** — 실제 배달업체(또는 계약된 자사 라이더) 선택·계약, 냉장 배송 정책/권역/요금/픽업 SLA·배차 API/콜백 credentials 및 라이더 인증·배송완료증빙. 계약된 테스트 환경에서 주문→배차→픽업→배송완료 증거 수신을 검증.
- **앱 운영 배포: NO** — Neon Auth BFF·상품 노출/API 연동, Android/iOS 실기기 + 환불/정산/알림/실배송 연동 QA 이후 별도 출시 심사.

증빙 및 자격증명이 없는 상태에서 절대 상품 상태만 강제로 승인·공개하거나 타사 Stripe 실계정으로 충전하지 않습니다. 운영 DB와 GitHub main은 변경하지 않았습니다.
