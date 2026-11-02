# 가락한상 오더 v3 · 개발·보안·Neon 인수인계

날짜: 2026-11-02 (KST)  ·  브랜드: **가락한상 오더 / Garak Hansang Order**

## 1. 완료된 변경

- V2 시장별 5개 카테고리 및 공동배송/집하/모의 라이더 배차 엔진을 그대로 보존한다.
- PostgreSQL/Neon 개발 브랜치 `dev-garak-hansang-order-20261102`(ID `br-winter-flower-b5tvau07`)를 `shinkangteam` 조직의 `garakhansang` 프로젝트(`dawn-paper-21288363`) 안에 생성했다. 운영 기본 브랜치는 수정하지 않았다.
- **개발 DB `gho` 스키마의 14개 테이블, 33개 DDL 문장 성공, RLS 설정 검증 완료.** 실제 결제/주문 데이터는 DB에 입력하지 않았다.
- 로컬 API는 `X-Demo-Role` 헤더를 인증에 사용하지 않는다. 자체 생성한 **로컬 운영자 Bearer 토큰**을 검증한다. 자격증명은 코드·GitHub에 포함하지 않는다.
- 주문마다 별도 256비트 상당 랜덤 접근 토큰을 생성하고 해시로 저장한다. 고객은 해당 토큰을 가진 주문에 대해서만 모의 결제 및 모의 취소를 요청한다.
- 외부 Origin의 상태 변경 요청을 거절한다. `127.0.0.1` loopback 전용 운용을 유지한다.
- 운영 화면은 토큰 입력 후 대시보드/상인승인/재고/집하/배차 기능을 수행한다. 관리자 한 명으로 다섯 역할을 시연하며 **실상용 역할별 권한관리는 아직 구현하지 않았다.**

## 2. 개발 DB의 한계

**Neon에 DDL만 적용했고 현재 Python API의 주문 원장은 여전히 SQLite다.** PostgreSQL 주문 트랜잭션 어댑터, Neon Auth JWT issuer/audience 검증, 멀티테넌트 상인 계정, 고객/기사 가입은 다음 스프린트 작업이다. 로컬 DB와 Neon DB 동기화 및 쓰기 경로는 현재 존재하지 않는다. DDL의 RLS는 브라우저 직접 접근을 허용하는 정책이 아니라 안전한 기본 차단이며, DB owner는 RLS를 우회할 수 있다. 별도 런타임 전용 DB role/grant 설계가 필요하다.

## 3. API 변경

- 로컬 운영 콘솔: 서버 터미널에서 출력한 `LOCAL DEMO ADMIN TOKEN` 입력 → `Authorization: Bearer <token>` 전송.
- 주문 생성 응답: `checkout_id`, `orders` 외에 `customer_action_token`을 포함. 주문 처리 서버는 이를 **로그에 기록하지 않는다.**
- 고객 모의 결제: `POST /order/api/v1/orders/{id}/mock-pay` + 고객 주문 토큰. 실제 결제는 아니다.
- 고객 모의 취소: `POST /order/api/v1/orders/{id}/cancel` + 고객 주문 토큰.
- 서버에 `GHO_DEMO_ADMIN_TOKEN` 환경변수가 설정되면 해당 토큰 사용 (최소 24자); 없으면 시작 시 임의 생성.
- 모든 운영 관리자 API에는 로컬 관리자 토큰이 필요. `X-Demo-Role` 단독 요청은 고객 역할로 처리되어 운영 API 접근 불가.

## 4. 실행

```bash
python backend/server.py --port 8768
python -m unittest discover -s tests -p test_domain.py -v
python tests/http_api_qa.py
python tests/browser_qa.py
```

주소: `http://127.0.0.1:8768/order/` (고객) / `http://127.0.0.1:8768/order/ops.html` (운영 콘솔).

실제 개인정보, 실제 카드 결제, 실기사 GPS 전송, 실배송 데이터는 입력하지 않는다.

## 5. 상용화 이전 필수 개발

1. Neon Auth/IdP 검증, JWT/JWKS rotation 및 사용자-가맹점-시장 관계 최소권한 검사. 이 로컬 토큰을 운영 인증으로 쓰지 않는다.
2. PostgreSQL 트랜잭션 기반 주문 생성과 재고 잠금, PG 웹훅 검증, 고객별 쿠폰 발행 한도, 재고 예약·만료, 실패 보상/환불 대사.
3. 픽업 QR·배송증빙·기사 실명 확인, 시장별 합배송·신선도 SLA 및 알레르겐 표시, 주소 보존·삭제 정책.
4. 상용 접근성 QA(텍스트 대비·탭 이동·스크린리더), 안드로이드 앱 번들/APK, 실제 실기기 테스트.
5. 가맹점 실제 계약 이후에만 가격·재고·사업자명·배송비를 실제값으로 표시. 쿠폰·가격·상품은 시연 예시임을 유지.
