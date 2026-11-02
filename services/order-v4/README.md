# 가락한상 오더 V4 · Neon 실제 주문 원장 개발 패키지

**상태: 격리 개발 브랜치에서 PostgreSQL 주문 생성·취소 실검증. 상용 서비스가 아닙니다.**

브랜드명: **가락한상 오더 / Garak Hansang Order**  
GitHub 원본: `skvive/garakhansang` · 작업 브랜치 `chatgpt/garakhansang-order-20261102`  
Neon 대상: `dawn-paper-21288363` · **DEV** `br-winter-flower-b5tvau07` (`neondb`)

## 주요 구현
- `db/002_demo_checkout.sql`: PostgreSQL 트랜잭션 한 건으로 **시장별 주문 분할, 잠금, 재고 차감, 멱등키 재요청 방어, 집하 단위 구성, 이벤트 로그 기록** 수행. 실제 결제 없음.
- `db/003_pilot_demo_seed.sql`: 5개 시장, 12개 샘플 상점, 17개 샘플 상품. 상인 확인된 실재고나 실제 판매가가 아님.
- `backend/auth_v4.py`: 서명된 OIDC RS256 JWT만 허용. issuer·audience·만료·발급 시각·JWKS 확인; 미설정 시 거절.
- `backend/repository_v4.py`: DB의 `merchant_members` 및 `actor_grants` 조회로 상인·집하·라이더 권한 확인. 주문 취소 재고 복구, 상태 전환 순서 강제.
- `backend/api_v4.py`: FastAPI `/order/api/v4/` 개발 API. 활성화 전에 개발용 Neon DSN 및 OIDC 설정 필요.

## 로컬 테스트

```bash
python -m pip install -r requirements-v4.txt
python -m unittest discover -s tests -v
```

실행 예시(인증과 개발 DB 변수를 먼저 설정했을 때만):

```bash
GHO_V4_MODE=isolated-dev \
GHO_NEON_DSN='postgresql://...@ep-gentle-wind-b5ir41pn.c-7.us-east-2.aws.neon.tech/neondb?sslmode=verify-full' \
GHO_OIDC_ISSUER='https://<your-approved-oidc-issuer>' \
GHO_OIDC_JWKS_URL='https://<your-approved-oidc-jwks-url>' \
GHO_OIDC_AUDIENCE='gho-order-v4' \
uvicorn backend.api_v4:app --host 127.0.0.1 --port 8780
```

Neon 접속은 개발 브랜치의 직접 연결 호스트로 고정되어 있으며 다른 Neon 브랜치 호스트는 거부합니다. 설정값은 서버 환경에만 저장하고, 커밋하거나 브라우저에 전달하지 않습니다. `GHO_NEON_DSN`이 없거나 `GHO_V4_MODE`가 `isolated-dev`가 아니면 DB 접근을 막습니다. **현재 실행 환경에는 psycopg 드라이버와 외부 Neon 연결이 없어, Python→Neon HTTP end-to-end는 별도로 검증해야 합니다.** Neon connector로 실행한 SQL의 실제 저장·취소는 `docs/NEON_V4_QA.md`에 기록했습니다.

## API

| Method | API | 권한 | 주의 |
|---|---|---|---|
| GET | `/order/api/v4/health` | 공개 | 개발 모드만 표시, 비밀값 미출력 |
| GET | `/order/api/v4/catalog` | 공개 | 시연 상품 |
| POST | `/order/api/v4/checkouts` | 고객 OIDC JWT | `Idempotency-Key` 필수, 실결제 아님 |
| GET | `/order/api/v4/orders` | 고객 JWT | 본인 주문만 조회 |
| POST | `/order/api/v4/orders/{id}/demo-authorize` | 고객 JWT | 돈이 이동하지 않는 모의 승인 |
| POST | `/order/api/v4/orders/{id}/cancel` | 고객 JWT | 배송 전 본인 주문 취소 |
| GET | `/order/api/v4/merchants/{id}/orders` | DB 상인 회원 | 소속 점포 한정 |
| POST | `/order/api/v4/merchants/{id}/orders/{id}/status` | DB 상인 회원 | `accepted→ready` |
| POST | `/order/api/v4/markets/{id}/orders/{id}/hub-collect` | 시장 집하 담당 | 상인 준비완료 검증 |
| POST | `/order/api/v4/dispatch/jobs/{id}/assign` | 시장 집하 담당 | 해당 시장 등록 기사만 배정 |
| POST | `/order/api/v4/dispatch/jobs/{id}/pick-up`, `/deliver` | 해당 배정 기사 | 순서 강제 |

## 상용화 차단 조건
1. 운영 DB에 V4 스키마·시드 적용 금지. DEV branch only.
2. 런타임 전용 제한 DB role 및 RLS 정책 검수 전 인터넷 공개 금지. DB owner는 RLS를 우회할 수 있음.
3. 모바일 토큰 보관 방식, 가입·탈퇴·개인정보 정책, PG 계약·웹훅·환불·정산, 쿠폰 예산 통제, 실제 배송기사 GPS·보험 검증 전 실서비스 불가.
4. 이미지의 제품 가격·배송비·캐릭터 쿠폰은 모두 예시이며, 실제 상인 가격을 대변하지 않음.
5. 가락한상 운영 사이트 `main`을 변경하거나 자동 배포하지 않음.
