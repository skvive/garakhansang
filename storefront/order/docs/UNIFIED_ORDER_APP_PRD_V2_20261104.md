# 가락한상오더 통합 배달앱 개발명세서 PRD v2.0

- 기준일: 2026-11-04 (KST)
- 제품: **가락한상오더 / GARAK HANSANG ORDER**
- 태그라인: **가락시장의 신선함, 집 앞까지!**
- 상태: **개발 / 운영 주문·결제 비활성화**
- 기준: Android 네이티브 고객앱 우선, 고객 PWA 병행, 상인·집하·라이더·관리자 운영 표면 단계적 연결
- 원본 보존: `main`, `chatgpt/garakhansang-order-20261102`, `chatgpt/garakhansang-order-android-20261102`, `chatgpt/garakhansang-order-v5-20261102` 불변. 본 v2 통합 브랜치에서만 작업.
- 참고 문서: Drive 2026-11-04 `가락한상오더_안드로이드_통합개발명세서_v1_3_20261104.md`; Drive `가락한상_쇼핑몰_전환_기획서.md`; 기존 `services/order-v4`, `services/order-v5`, `storefront/order` 코드.
- 저작권/브랜딩: 쿠팡이츠·배민의 **작동 원리와 UX 휴리스틱** 참고. 상표, 캡처, 아이콘, 카피·레이아웃 1:1 복제 금지. 공식 가락한상 에셋 우선 사용.

## 0. 기존 자산 실사 및 재사용

| 원본 | 실제 확인 | 재사용 규칙 |
|---|---|---|
| `storefront/order` (V5 브랜치) | 5개 시장, 17개 시연 상품, 검색, 카테고리, 장바구니, 시연 쿠폰, 시장별 가상 합배송, 로컬 모의 주문, 레드 A 마스코트 UI | 고객 PWA·웹 QA 기준선; 샘플 실판매 금지 |
| `services/order-v4` | FastAPI, PostgreSQL 격리 DEV 주문·취소, 집하/배차, 멱등키, 주문 이벤트, 재고 트랜잭션 | 검증된 DEV 도메인 로직 보존; PG 연동으로 오인 금지 |
| `services/order-v5` | Neon Auth JWT EdDSA/JWKS 검증, 카탈로그 최소권한 RLS, 역할 조회, V5 테스트 | 독립된 개발 API/DB 계약; 운영 이관 전에 실 OAuth E2E 필요 |
| `android-order` (별도 Android 브랜치) | Java/SDK36/minSDK26, 홈·상품·검색·장바구니·주문준비 안내, 로컬 9개 시연 상품 | 소스/리소스 보존 후 앱 점진 리팩터링; V5 브랜치에 없는 파일은 충돌 검증 후 통합 |
| Drive Android v1.3 패키지 | 명세상 47종/12카테고리, 검색·상세·카트·5탭, JPG 매핑 | 실제 소스/이미지 ZIP·빌드 일치 여부 별도 확인 전 구현 완료로 표기하지 않음 |
| `skvive/garakland` | 가락시장 매장 검색·층별 도면·모바일 지도 개발자산 | 점포 위치 매핑에 재사용; 도면 라이선스·정확성·접근성 검증 전 고객 동선 안내 금지 |
| Drive `렉시드개발자료/공통개발스킬/가락한상` | 공식 브랜드 에셋/스킬 ZIP 및 컨택트 시트 | 가락한상 로고·레드 스쿠터 마스코트 우선, 외부 복제 에셋 금지 |
| Drive `가락한상_쇼핑몰_전환_기획서.md` | 기존 Next.js/Neon/Drizzle/토스 결제 전환 설계 및 시세·원산지·합배송·정산 정책 | 코어 스키마/운영 정책 후보. 현재 V5 FastAPI/SQL과 **중복 테이블 방지 매핑** 선행 |

**현재 실측 주의:** V5 README는 `Neon DEV dawn-paper-21288363 / br-winter-flower-b5tvau07` 개발 격리를 명시함. 직접 API→DB, OAuth 콜백, APK 실기기 및 PG 실거래 미검증. V5는 운영이 아니다. 과거 CI 통과 사실을 현재 전체 기능 통과로 외삽하지 않는다.

## 1. 서비스 원칙 / MVP 정의

**핵심 차별화:** 한 시장 내 여러 상인의 장바구니를 **시장별 그룹**으로 나누어 공동집하·합배송. 다른 시장은 원칙적으로 별도 배송; 노량진 수산/가락 청과 등 수산·축산·농산 상품의 **중량, 원산지, 손질 옵션, 온도유지, 실중량 차액 정산**을 주문 단계마다 설명한다.

1. 고객은 주소를 입력해 **실제 운영 권역/슬롯이 서버에서 승인된 경우만** 결제 가능.
2. 시연 상품·AI 이미지·예상 시세에는 `시연` 표기를 유지. 실제 재고·시세 업데이트 시간과 상인 승인 상태를 분리.
3. 합배송은 시장·배송 슬롯·상품 온도조건·라이더 적재 가능여부를 모두 확인한 뒤에만 약속.
4. 실결제 출시 이전에는 버튼을 모의 주문으로 명확하게 표시하고 실 주문으로 취급하지 않는다.
5. 직접 구현할 기능에 기존 V4/V5 원장·기존 Android·공통 에셋을 우선 사용. 오픈소스는 UI 구조 참고이며 라이선스/서버 의존성 확인 후 부분 수입.

## 2. 전체 메뉴 구조 / 화면 정의

### A. 고객 Android/PWA — 28개 화면

하단 **홈 | 시장·상품 | 장바구니 | 주문내역 | 마이** 5탭. 검색은 모든 리스트의 상단 공통 진입. 쿠폰·혜택은 홈과 마이에서 접근.

| ID | 화면 | 필수 인터페이스/버튼 | API·상태 |
|---|---|---|---|
| C01 | 스플래시/버전 | 로고·업데이트·재시도 | 앱 정책/버전 |
| C02 | 온보딩 | 건너뛰기·서비스 안내 | 동의 분리 |
| C03 | 로그인/가입 | 구글/휴대폰 로그인·비회원 탐색 | Neon Auth/Google OAuth, 인증 실패 |
| C04 | 배송지 등록 | 주소검색·수동주소·현재위치·상세주소 | 지오코딩/권역 API, 거부 대안 |
| C05 | 홈 | 배송 주소·마감/가능여부·검색·오늘 시세·배너·카테고리·추천 | 캐시/빈 상태 |
| C06 | 시장 선택 | 가락/노량진/기타 시장·배송 모드 | 실제 운영 여부 명시 |
| C07 | 카테고리 | 수산·축산·농산·반찬·제철·한상세트 | 목록 필터 |
| C08 | 검색 | 자동완성·최근 검색·결과없음 | API 검색·취소/디바운스 |
| C09 | 검색 결과/필터 | 가격·원산지·중량·냉장·정렬 | 표시 가능한 상품 |
| C10 | 점포 목록 | 영업 중/배송가능/별점(실데이터) | 미승인 점포 숨김 |
| C11 | 점포 상세 | 찜·영업시간·최소주문·상품·후기 | merchant id |
| C12 | 상품 상세 | 사진·중량·가격/단위·원산지·시세 기준일·손질·알레르기 | 실제 데이터 검증 |
| C13 | 옵션 바텀시트 | 필수옵션·수량·가산금·담기 | 서버 카탈로그 버전 |
| C14 | 찜/최근본 | 저장·해제·재탐색 | 계정 동기화 |
| C15 | 공동장바구니 | 시장/점포별 구획·수량·삭제·예상 배송비 | quote 재계산 |
| C16 | 쿠폰·혜택 | 쿠폰 다운로드·적용·할인조건 확인 | 예산·유효기간 |
| C17 | 배송 방식/슬롯 | 배송/픽업·슬롯·도착 예상 | 서버 커버리지/캐파 |
| C18 | 주문서 | 배송지·연락처·요청사항·가격 재확인·필수 고지 | 서버 quote TTL |
| C19 | 결제수단 | 토스/카드/간편결제 선택·취소·복귀 | PG 웹훅 검증 |
| C20 | 주문완료 | 영수증·주문번호·상태보기 | 서버 실주문만 성공 표시 |
| C21 | 주문내역 | 진행중/완료/취소·재주문 | 주문 소유권 |
| C22 | 주문 상세 | 상인별 구성·실중량·영수증·문의 | 금액/상태 스냅샷 |
| C23 | 배달 추적 | 준비→집하→배차→이동→전달·지도(허용 시) | 이벤트 스트림/권한 |
| C24 | 주문취소·환불 | 정책·사유·신청·진행상태 | 원장/PG 대사 |
| C25 | 후기 작성 | 별점·사진·신선도·재구매 | 배송완료 1회성 |
| C26 | 알림함 | 주문·배달·시세·혜택 | FCM 옵트인 |
| C27 | 고객센터 | FAQ·1:1문의·오배송·품질클레임 | CS 티켓 |
| C28 | 내정보/설정 | 계정·주소·알림·약관·정보삭제·로그아웃 | 최소수집/보존 |

### B. 상인 앱/콘솔 — 14개 화면

M01 로그인·사업자 확인; M02 오늘의 주문 대시보드; M03 신규주문 상세/수락·거절; M04 준비시간 설정; M05 상품 등록·수정; M06 가격/시세 입력; M07 재고·품절; M08 손질/중량확정; M09 집하 인계 QR; M10 영업시간·휴무; M11 쿠폰/기획전; M12 정산·수수료·세금; M13 리뷰·CS; M14 직원/권한/매장설정.

각 상인은 **본인 merchant_id**만 조회·변경 가능. 주문 수락은 서버 트랜잭션으로 기록; 임의 배송완료 변경 금지.

### C. 공동집하·배달기사 — 11개 화면

R01 기사 인증/운송자격; R02 근무 ON/OFF·권역; R03 대기 배차 목록; R04 오더 묶음·요청 수락/거절; R05 픽업 상세·체크리스트; R06 집하센터 인수 QR; R07 운송 지도/네비 연결; R08 고객 전달 옵션·연락; R09 배송 완료 증빙; R10 사고/연착/반송; R11 배달실적·정산. 집하 담당자의 픽업/배차 화면은 초기 웹 콘솔로 분리. 기사 위치는 배정된 배송 건에 대해 필요한 시간에만 수집하고 보존기간 정책 준수.

### D. 본사·운영 관리자 — 14개 화면

A01 KPI/운영현황; A02 점포·사업자 승인; A03 상품·시세·원산지 검수; A04 주문 모니터링; A05 집하 대시보드; A06 배차·라이더 권한; A07 권역·슬롯·배송비 규칙; A08 PG 대사·미결제 처리; A09 부분취소·환불 승인; A10 판매자 정산·수수료; A11 쿠폰 예산·혜택 비용; A12 고객 문의/품질·신고; A13 배너·콘텐츠·권한; A14 감사로그·보안·운영환경.

## 3. 화면 UX/비주얼 상세

- **홈 상단:** 현재 배송 주소·배송 가능/불가 상태, 검색, 알림. 비활성 지역에는 배송 예상시각을 표시하지 않는다.
- **첫 접힘 영역:** '오늘의 가락 시세' 데이터 출처와 기준시각, 수산·축산·청과 진입, 시장 선택을 우선. 가짜 수치·가짜 후기·허위 판매량 금지.
- **카드:** 실사 1:1 이미지, 상품명 2줄, `원/중량`·원산지·온도·점포·배달조건, 담기 44dp 이상. AI 콘셉트 이미지에는 시연 라벨.
- **상품 상세:** 스크롤 시 가격·옵션 하단 고정 CTA; 손질/추가 비용·수량·원산지·실중량 차액 기준 표시.
- **장바구니:** 시장별/점포별 묶음, 동일 시장 합배송 가능 조건·절약액은 서버 검증된 값만. 결제 직전 quote 갱신, 값 변경 시 명시적 재동의.
- **주문상태:** 실시간 지도는 opt-in·배차 후에만. 준비상태는 텍스트 타임라인으로 항상 제공.
- **마이:** 진행 중 주문 우선, 자주 사는 상품, 찜, 쿠폰, 주소·연락·정보삭제.
- **상태 디자인:** 로딩 스켈레톤/0건/네트워크 오류/품절/오프라인/권한 거부/배달불가/결제 실패/취소 실패/이미 처리됨 각각 화면.
- **디자인 토큰:** PWA Red A `#B80C1D`를 배달 브랜드의 대표색, Android 기구현 `#CA1020`은 기존 버전 호환 계층으로 점진 통합. Cream `#FFF7EC`, Ink `#2D211F`, Green `#49753D`. 쇼핑몰의 딥오션 블루는 수산/품질 정보용 보조. 가락한상 로고·스쿠터 캐릭터 재사용.
- **접근성:** Android 360–600dp, 터치 44dp+, 폰트 200%, 스크린리더 순서·명확한 라벨·키보드 포커스·대비·시스템 안전영역. 팝업은 ESC/뒤로 종료·포커스 복구.
- **스크린샷/레퍼런스:** 공개 이미지의 정보구조(탭, 검색, 카드, 주문)만 분석; 리소스 원본 복제 금지. [쿠팡이츠 UX 공개 사례](https://brunch.co.kr/@haily1216/14), [쿠팡이츠 배달파트너 공식 가이드](https://ces.coupangeats.com/app-guide/), [Shita MIT 멀티벤더 오픈소스](https://github.com/ferasshita/Shita-Multivendor-Food-Delivery), [Enatega 화면 참고(백엔드 독점)](https://github.com/CodeZens/Marketplace-Food-Delivery-Solution).
- **오픈소스 판단:** Shita는 MIT이지만 전체 도입 시 React Native/GraphQL/MongoDB로 기존 Android Java + FastAPI/Neon을 중복 구축한다. **레이아웃/상태 화면 설계 참고 우선**. Enatega는 백엔드/서버 유료 독점이므로 서버 이식 금지.

## 4. 아키텍처

```text
[Android customer (Java baseline -> staged Kotlin/Compose)] --HTTPS--> [Mobile BFF]
[Responsive customer PWA existing storefront/order] ---------------> |
[Merchant / Rider / Hub / Admin clients] ---------------------------> |
                                                                    v
                                                        [FastAPI V5 domain API]
                                                         | Neon Managed Auth
                                                         | EdDSA/JWKS + issuer/aud
                                                         | DB role checks + RLS
                                                         v
                                                  [Neon DEV gho schema]
                                                         |
                                          [Orders / merchant / dispatch / audit]
                                                         |
                                       [PG adapter / delivery partner / FCM]
                                       (DISABLED until production approvals)
```

현재는 `services/order-v5`를 격리 개발 서비스로 활용. 운영 시 별도 Neon 운영 프로젝트/브랜치·최소권한 런타임 계정·비밀키 회전·배포 승인 필요. 기존 쇼핑몰 Next.js/Drizzle 주문 테이블과 V5 `gho.*`를 이중원장으로 운영하지 않고 상품 및 주문 식별자 매핑, 원장 책임 단일화 후 통합.

## 5. 데이터·상태 기계

**기존 `gho`**: `markets, merchants, merchant_members, products, checkouts, orders, order_lines, merchant_fulfillments, dispatch_jobs, payments, payment_webhooks, coupons, coupon_redemptions, audit_events`. 버전별 SQL 스키마의 실제 반영 상태가 다르므로 마이그레이션 선 실행 금지.

**계획 확장 (별도 이행·검수 후):** `customer_addresses`(복호화 접근 통제), `delivery_zones`, `delivery_slots`, `price_snapshots`, `weight_adjustments`, `cold_chain_events`, `merchant_settlements`, `ledger_entries`, `refunds`, `reviews`, `support_tickets`, `push_subscriptions`, `driver_location_events`. 필드 삭제·이름 변경 전 기존 테이블 중복 검증 필수.

- 고객 체크아웃 `CART → QUOTED → RESERVED → PAYMENT_PENDING → PAID`; 실패·만료·취소는 별도 경로.
- 각 점포 `PENDING → ACCEPTED → PREPARING → READY → HUB_RECEIVED`.
- 시장별 배송 묶음 `WAITING → ASSIGNED → PICKED_UP → IN_TRANSIT → DELIVERED`.
- 취소 `CANCEL_REQUESTED → CANCEL_APPROVED/DENIED → REFUND_PENDING → REFUNDED/REFUND_FAILED`.
- V5 현재 DB의 간소 상태 `created/authorized/paid/picking/hub_ready/assigned/picked_up/delivered/... `는 개발용 그대로 유지하고 도메인 매핑 테이블을 추가해 점진 전환. 자동 상태변경 금지.
- 실중량 변동: 주문 시 원/중량과 허용 범위 명시 → 상인 계량 실측/증빙 → 고객 추가결제 동의 또는 정책상 차액 환불 → PG 원장 재대사.
- 가격은 정수 KRW, 서버 재견적. `Idempotency-Key`/요청 digest/웹훅 서명+event_id 중복방지. 결제 완료는 서버·PG 대사 이후에만 표시.

## 6. 모바일 BFF API 계약

**개발 기존:** `/order/api/v5/health, /catalog, /checkouts, /orders, /merchants/{id}/orders, /dispatch/...` — demo only.

**이번 시작 구현:** `GET /order/api/v5/mobile/bootstrap`. 100% 읽기전용, `demo_mode=true`, `real_checkout_enabled=false`, `payments_enabled=false`, `live_tracking_enabled=false`, `delivery_zone_verification_enabled=false`. 모바일은 이 계약으로 실주문 버튼 차단.

**P1 이후 추가:**

| Method | 경로 | 기능/보호 |
|---|---|---|
| GET | `/mobile/markets` | 활성화된 시장만, 데모와 실매장 구별 |
| GET | `/mobile/stores`·`/mobile/stores/{id}` | 권역·승인·영업 상태 필터 |
| GET | `/mobile/products`·`/mobile/products/{id}` | 옵션·원산지·가격기준일 |
| POST | `/mobile/addresses/resolve` | 주소/지오코딩/권역/슬롯 |
| POST | `/mobile/cart/quote` | 실재고·온도·합배송·배송비·할인 |
| POST | `/mobile/checkouts` | 멱등 키, 서브주문 상태와 총액 반환 |
| POST | `/mobile/payments/prepare` | 계약된 PG 테스트/운영 계정 엄격 분리 |
| POST | `/mobile/payments/confirm` | PG 서버 검증·webhook 대사 |
| GET | `/mobile/orders`·`/mobile/orders/{id}` | 주문 소유권 검증 |
| GET | `/mobile/orders/{id}/events` | 배송 이벤트, 역할 필터 |
| POST | `/mobile/orders/{id}/cancel` | 취소 단계/기준 검증 |
| POST | `/mobile/reviews`, `/mobile/support/tickets` | 완료 주문·CS 권한 |
| POST | `/mobile/push-tokens` | 옵트인/폐기 |
| GET/POST | `/merchant/*`, `/dispatch/*`, `/admin/*` | 별도 role/API 키·DB 정책 |

오류 계약: `{request_id,data,error:{code,message,can_retry}}`; 인증 401, 권한 403, 소유하지 않은 리소스 404, 충돌 409, 검증 오류 422, 서비스 불가 503. 보안 이벤트 감사를 하고 PII/PG 비밀키를 로그에 기록하지 않는다.

## 7. 보안·품질·상용화 게이트

- Neon Auth Google 로그인 실제 콜백, JWT 발급/갱신/로그아웃/토큰 폐기; audience/issuer/JWKS 바인딩 고정.
- 고객은 자기 주문, 상인은 자기 매장, 라이더는 배정된 배송, 관리자는 승인된 업무 범위만 접근. DB 오너/슈퍼유저 런타임 금지.
- 고객 개인정보 최소 수집, 개인정보처리방침/입점계약/전자상거래 고지, 수산물 원산지·식품정보·환불/교환 기준 검수.
- 운영 전: PG 테스트 결제/취소/부분환불/중복 webhook/정산 대사, 배송 제휴 계약/배차/보험, 콜드체인 품질 증빙, 실상품/실재고 확인.
- Android CI assembleDebug, API unit/integration, 브라우저 360/390/430/600/768px 스크린샷·빈화면/모달/키보드/UI, 에뮬레이터 API26/35/36, 접근성. 실제 기기 설치·운영 OAuth·실 PG 미검증 시 **GO-LIVE NO**.
- CI 및 수용 테스트: 최소 ① 미인증 주문 거부 ② 다른 점포 주문 조회 403 ③ 재고 경쟁 ④ 0/99 경계 ⑤ 동일 키 중복처리 ⑥ 쿠폰 동시 소진 ⑦ 배송권 밖 ⑧ 타 시장 별도 배송 ⑨ 배달 상태 순서 ⑩ 실결제 게이트 ⑪ 취소 중복 ⑫ 오프라인·접근성.

## 8. 단계별 개발순서·수용기준

1. **P0 통합 기반 (이번 작업):** V5 기준 독립 개발 브랜치 생성; v1.3 + 쇼핑몰 PRD 통합; API 안전 부트스트랩 구현; 고객 PWA 주문내역을 5탭으로 승격; 기존 로고 유지. **수용:** demo flag·배포 차단·기존 주문/쿠폰/장바구니 흐름 보존.
2. **P1 데이터 연결:** Android 별도 브랜치의 앱 코드와 최신 47종 샘플 리소스를 증거/해시 확인 후 통합. Neon Auth·주소 권역·카탈로그·점포·재고 연동. **수용:** 데이터 정합/권한·OAuth 실제 통과.
3. **P2 실주문 파일럿:** 배송 슬롯, quote·상인 수락·집하·배차·상태 추적을 PG 없는 폐쇄 파일럿으로 연결. **수용:** 전체 상태 머신·취소·중복 방지.
4. **P3 PG/정산:** 토스 PG 계약/테스트, 웹훅 검증, 환불, 실중량 추가정산, 수수료 및 분리 정산. **수용:** 금액오류 0·멱등성·원장 균형.
5. **P4 라이더/운영/CS:** 배송 파트너, 운영 콘솔, 푸시, 리뷰, CS, 고급 시세와 신선도 증빙. **수용:** 기사 권한·알림·사고 처리.
6. **P5 고객 납품 QA:** 각 화면·버튼 E2E, 보안·접근성·실기기·도면 사용권·약관·상인 승인·마켓 등록 후 서명/배포. **수용:** 운영 승인 서명 전 외부 주문 비활성.

## 9. 변경 통제

- 기존 원본 브랜치·Drive ZIP·자산 불변, 원본 파일 삭제 금지.
- 기존 `storefront/order` 과 `android-order` 기능 중복 여부를 표로 관리하고, 화면 계약부터 점진 통합.
- 사용자 명시 승인 없이는 운영 DB SQL 실행, 결제 활성화, 개인정보 수집, 공개 도메인 배포, 외부 상인 통지 금지.
- Git 브랜치 `chatgpt/garakhansang-order-unified-v2-20261104`; 의미단위 커밋·읽기검증·테스트 결과·릴리스 차단조건 기록.

## 10. 공개 배달앱 UI 및 오픈소스 벤치마크 (2026-11-04 조회)

### 실화면 참고 근거(레퍼런스별 게시 시점 구분)

1. [요즘IT 쿠팡이츠 UX 분석: 주문·포장 선택 및 장바구니 화면](https://yozm.wishket.com/magazine/detail/1405/) — 배송/픽업 전환, 상품별 수량, 하단 고정 결제 CTA를 관찰. 게시된 **과거 화면**이며 2026년 현행 앱 레이아웃으로 단정 금지.
2. [뉴스1 요기요 앱 리디자인 체험 화면](https://www.news1.kr/industry/sb-founded/5319288) (2024-02) — 카테고리 탐색, 진행상태 타임라인, 주문내역/재주문 분리를 관찰. 현재 운영 상태와 다를 수 있음.
3. [배달의민족 공식 Google Play 앱 소개](https://play.google.com/store/apps/details?gl=kr&hl=ko&id=com.sampleapp) — 홈 탐색, 쿠폰·혜택 정보의 노출 위치와 공개 스토어 설명 참고. 화면 개편 가능성을 전제로 참고.

### 오픈소스 실제 재사용 판단

| 코드 후보 | 공개 라이선스·범위 | 이식 판단 |
|---|---|---|
| [Ashwinbicholiya/Food-delivery-app](https://github.com/Ashwinbicholiya/Food-delivery-app) | MIT, Flutter/Firebase 기반. 2022년 이후 핵심 업데이트가 오래됨 | **레이아웃·이동 흐름만 참고.** Android/Neon/Auth를 Flutter/Firebase로 교체 금지 |
| [mdossantosdev/food-delivery-app](https://github.com/mdossantosdev/food-delivery-app) | MIT, React Native/Expo, 인증·검색·주문·오퍼·추적 화면 구현 | **화면 상태/오류 UX 참고**, 재사용 시 소스 라이선스 고지와 코드 검토 필수 |
| [jssuthahar/food-delivery-app](https://github.com/jssuthahar/food-delivery-app) | MIT, Flutter+BLoC/GoRouter, 의존성 분리 및 Firebase 기본 비활성 | **테스트 가능 아키텍처 참고**, 즉시 포크·전체 도입 불필요 |
| [Enatega 공개 프런트엔드](https://github.com/hector-jewell/react-native-food-delivery-app-with-backend) | 프런트 MIT이나 API/백엔드는 **독점/유료**라고 명시 | 독점 백엔드·에셋·화면 복제 금지, 일반 UX 휴리스틱만 참고 |

**반영된 모바일 인터페이스 의사결정:** ① 상단 주소/검색 고정 ② 상인·상품 카테고리 카드 ③ 상품 옵션·수량 바텀시트 ④ 시장별 합배송과 총액 명시 ⑤ 하단 장바구니/주문내역 ⑥ 주문상태 타임라인 ⑦ 쿠폰은 홈/마이 진입 ⑧ 실제 주문·결제/배송 불가 시 즉시 차단.

**디자인 검수 기준:** 참조 스크린샷은 분석 링크로만 기록하고 앱의 이미지·아이콘·로고에 복제/재배포하지 않는다. 실제 가락한상 자체 화면 스크린샷은 새 브랜치 실행/테스트에서 별도로 획득하고, 모바일 360/390/430/600dp 와 다크모드/대형 폰트, 전체 클릭 동작을 검사한다. 이 단계의 실제 브라우저 렌더/스크린샷은 아직 확보되지 않았으므로 구현 완료로 표기하지 않는다.
