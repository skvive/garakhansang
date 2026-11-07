# 가락한상 오더 — 4역할 주문/배달 로컬 테스트 앱 실행법

최종 소스: `skvive/garakhansang` / `chatgpt/garakhansang-order-p2-stripe-sandbox-roles-20261107`.

> **주의:** 이 앱은 프로덕션 애플리케이션이 아니라 127.0.0.1에서만 실행되는 합성 데이터 E2E 검증용입니다. 고객 결제, 실제 배송/배차, 실제 상인·라이더 등록/정산, FCM 푸시 및 운영 Neon 연결은 제공하지 않습니다.

## 1. 로컬 실행 (Python 3.11 이상)

릴리스 전체 소스(또는 CI artifact `GarakHansang-Order-P3-LocalLab-Source`)를 풀어서, `admin_core/`와 `storefront/`가 같은 상위 폴더에 있도록 배치합니다.

```bash
python -m admin_core.order_lab_server --port 8118
```

실행 터미널에 **그때 생성된** 고객/상인/라이더/관리자 비밀번호 4개가 표시됩니다. 비밀번호를 화면에 고정하거나 소스·로그·브라우저 저장소에 삽입하지 마세요. `http://127.0.0.1:8118/`를 엽니다.

- 고객 `customer`: 카탈로그, 상품 상세, 장바구니, 테스트 주문 생성/상태 조회.
- 관리자 `ops`: 상인·라이더 승인, 미결제 주문의 **합성 서명 이벤트**로 모의 결제 확인, 환불 테스트, 예상정산.
- 상인 `merchant`: 자기 상품 재고, 결제된 주문 수락/조리/픽업준비/배차요청.
- 라이더 `rider`: 근무상태, 승인 배차 후보, 배차 수락/픽업/배송완료.
- 고객/상인/라이더/운영자 각자의 알림함은 폴링으로 기록 확인. 브라우저가 열려 있고 사용자가 알림을 허용한 경우 브라우저 자체 알림을 표시할 수 있으나 FCM/푸시 백그라운드 발송은 아닙니다.

각 역할은 별도 브라우저 프로필이나 시크릿 창에서 로그인하면 한 주문을 동시에 확인할 수 있습니다.

### 시나리오

1. customer로 `테스트 주문 생성`; 서버는 승인된 샘플 품목 가격으로 재견적, 고정 **합성** 배달료 2,000원을 반영.
2. ops로 해당 주문의 `모의 Stripe 결제 검증` 버튼 → 로컬 합성 결제 완료 이벤트 HMAC 검증 → 상태 `paid`.
3. merchant로 접수·조리·픽업준비·배차요청.
4. rider로 배차 수락·픽업·배송중·배송 완료.
5. ops에서 정산 예상액, customer에서 주문상태, 각 역할별 알림을 조회.

## 2. Stripe TEST 환경 연결(선택, 별도 승인 필요)

**연결된 Stripe 계정은 라이브 컨텍스트만 확인되었으므로 이 브랜치에서는 Stripe 실거래 요청을 실행하지 않았습니다.** 실행 테스트는 모의 Session과 유효한 테스트 서명으로 수행합니다. 실제 Stripe 샌드박스 테스트를 하려면 안전한 테스트 계정에서 분리된 `sk_test_` 비밀키와 테스트 `whsec_` 웹훅 서명키를 별도로 발급해야 합니다.

```text
GARAK_LAB_ENABLE_STRIPE_TEST=1
GARAK_LAB_STRIPE_TEST_KEY=sk_test_...
GARAK_LAB_STRIPE_TEST_WEBHOOK_SECRET=whsec_...
GARAK_LAB_PUBLIC_HTTPS_ORIGIN=https://<별도-스테이징-도메인>
```

테스트 모드만 허용하고 `sk_live_`·실결제 Session·라이브 이벤트는 거부합니다. 테스트 웹훅은 `POST http://127.0.0.1:8118/lab/api/stripe/webhook`로 **로컬 Stripe CLI**를 통해 전달하고 원문 `Stripe-Signature`를 사용해 검증합니다. 직접 만든 JSON을 클라이언트에서 결제 성공이라고 보내도 성공 처리하지 않습니다. Test Session 생성과 실제 테스트 카드 결제는 별도 키, Stripe 계정 권한, HTTPS 콜백 세팅 후에만 실행할 수 있습니다.

## 3. 자동검증

```bash
python -m unittest discover -s tests -p 'test_order_p2_sandbox.py' -v
python -m unittest discover -s tests -p 'test_order_lab_integration.py' -v
```

실행 기록: [GitHub Actions P2/P3](https://github.com/skvive/garakhansang/actions/workflows/order-p2-stripe-sandbox-ci.yml).
현재 GitHub CI에서는 Python 계층·실제 로컬 HTTP 요청·JavaScript 구문 및 역할별 권한을 확인합니다.

## 4. 프로덕션 전환 차단 항목

Neon은 별도 개발 브랜치 `dev-garak-order-v2-20261107`에 스키마 `garak_order_v2`만 추가했습니다. 테이블은 비어 있고 RLS 사용 테이블에는 인증된 공개 접근 정책이 **아직 없어 직접 클라이언트 접근 차단 상태**입니다. 8개 테이블 RLS `ENABLE`과 공개 권한 철회는 실제 운영 JWT/RLS를 구현한 것과 다릅니다.

프로덕션 전환 전 필수: 검증 가능한 고객 Neon Auth 로그인·주소 동의, 실상품 승인/원산지·알레르기/옵션/권역/배송비, 운영 주문 원장과 트랜잭션, Stripe TEST E2E/취소/환불, 상인 계약·라이더 안전 심사, 실지도·FCM·대기시간 재배차·정산 대사, 운영 인프라 및 취약점 테스트, Android 설치 서명/실기기 검수. **main 병합, 실결제 활성화, Google Play 출시는 자동 수행하지 않습니다.**

주의: 코드의 `simulate-paid`·`simulate-refund`는 ops만 접근 가능한 루프백 QA 엔드포인트입니다. 이 서버를 외부 네트워크나 Vercel에 노출하면 안 됩니다.
