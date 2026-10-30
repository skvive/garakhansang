# 가락한상 V6 REST API 명세 (로컬 베타)

모든 경로는 `http://127.0.0.1:8099` 기준. `GET`은 상태 조회, 데이터 변경은 JSON POST/PATCH이며 관리자 세션 쿠키 + `X-Garak-CSRF`가 필요하다. 액세스 권한은 `RBAC_AND_SECURITY.md`의 역할별 차등 적용.

| Method / Path | 기능 | 동작 및 중요한 제한 |
|---|---|---|
| GET `/api/health` | 헬스 체크 | LOCAL_BETA/실결제 비활성 반환 |
| POST `/api/auth/login` | 관리자 로그인 | 초기 랜덤 비밀번호 사용, 로그인 제한 |
| GET `/api/auth/me` | 세션 확인 | 역할과 CSRF 반환 |
| POST `/api/auth/logout` | 세션 무효화 | 서버 세션 해시 삭제 |
| POST `/api/auth/password` | 비밀번호 변경 | 이전 비밀번호 검사, 14~200자 |
| GET `/api/admin/overview` | KPI/미처리 상태 | 매 호출 시 DB 집계, 샘플 수치 명시 |
| GET `/api/admin/reports` | 분석 데이터 | 일별 주문/상태/카테고리/상품/캠페인 이벤트 |
| GET `/api/admin/{module}` | 목록/검색 | 고정 허용 테이블만, `?q=` 최대 100자/상위 300건 |
| GET `/api/admin/{module}/{id}` | 상세 조회 | 일부 개인정보/세션 제외 |
| PATCH `/api/admin/{module}/{id}` | 허용된 필드 수정 | 상태 검증, 감사 로그 기록 |
| POST `/api/admin/products` | 상품 신규 | 원가/판매가, 상인 ID, 재고, 초안 생성 |
| POST `/api/admin/recipes` | 레시피 신규 | 초안 + 미검수 상태만 생성 |
| POST `/api/admin/inventory/adjust` | 재고 입출고 | `{product_id,delta,reason}` 원자적 갱신 |
| POST `/api/admin/orders/create` | 테스트 주문 | `{items:[{slug,qty}]}` 재고 예약 후 `payment_mode=simulation` |
| GET `/api/admin/orders/{id}/details` | 주문 품목/배송 상세 | 주문·품목·배송 상태 읽기 |
| POST `/api/admin/orders/{id}/transition` | 주문 상태 변경 | 상태 머신 및 배송·취소 조건 검증 |
| POST `/api/admin/settlements/generate` | 베타 정산 계산 | 배송 완료 주문에 한함, 중복 생성 차단 |
| POST `/api/admin/users/create` | 관리자 초대(베타) | 최고관리자만, 임시 비밀번호 일회 표시 |
| POST `/api/admin/{posts,merchants,creators,campaigns,tickets}` | 초안·승인대기 등록 | 자동 광고 게시 안 함 |
| GET `/api/public/products` | 베타 공개 상품 | 이름·가격·테스트 재고, 100개 제한 |
| GET `/api/public/product/{slug}` | 공개 상품 재고 | 상태 `published` 제품만 제공 |
| GET `/api/public/recipes` | 검수된 레시피 | `published` + `reviewed=1`만 공개 |
| GET `/api/public/posts` | 승인 홍보 | `approved` + `verified=1`만 공개 |
| POST `/api/public/events` | 익명 페이지 이벤트 | 허용된 이벤트 이름·경로만, PII 금지, IP별 분당 제한 |

실제 PG/배송/외부 서비스 인증은 **존재하지 않는 API를 구현된 것처럼 표시하지 않는다**. `integrations` 테이블은 현재 연결 상태를 투명하게 관리하는 용도다. OAuth 토큰이나 실입점 자격정보를 브라우저에 입력하면 안 된다.

### 대표 요청 예시
```bash
# 데모에서만 동작하는 공개 API
curl http://127.0.0.1:8099/api/health
curl http://127.0.0.1:8099/api/public/products
```
관리자 변경 API는 첫 로그인 후 브라우저의 세션으로 실행하거나 자동 API 테스트 `tests/test_beta_api.py`를 사용한다. 초기 비밀번호를 명령줄이나 저장소에 기록하지 않는다.

### 에러 표준
`400` 유효성/업무 상태 오류, `401` 로그인 필요, `403` 권한/CSRF 위반, `404` 존재하지 않는 리소스, `429` 호출 제한. 성공 JSON은 `{ok:true}` 또는 `{items:[...]}`, 오류는 `{error:"..."}` 형식이다.
