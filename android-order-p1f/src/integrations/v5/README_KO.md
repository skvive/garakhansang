# V5 백엔드 확장 파일 — P1b 읽기 전용 시장·상인·상품 탐색

기존 V5 `backend/api_v5.py`, RLS, Neon 연결을 복제하지 않습니다.

1. `integrations/v5/mobile_api_p1.py`를 **기존 V5 작업 브랜치**의 `backend/mobile_api_p1.py`로 복사합니다.
2. 기존 V5 `backend/api_v5.py`에 아래 두 줄을 추가합니다.

```python
from .mobile_api_p1 import router as mobile_p1_router
app.include_router(mobile_p1_router)
```

3. `GHO_CATALOG_READ_DSN`/`GHO_V4_MODE=isolated-dev`는 V5의 기존 **제한적 DB 역할**을 따릅니다. 새 DB 마이그레이션, 자격증명 생성, Neon 실환경 접근 없음.
4. 모바일 엔드포인트: `GET /api/v1/mobile/{bootstrap,auth/status,markets,merchants,products,serviceability}`. 미연결: 503. 실제 배송권역과 주문/결제는 미구현이며 항상 차단.
5. 공개 라우팅 시 **개발용 인증 게이트** 및 접근 제어를 별도로 설정하세요. 인증 없는 개발 데모 데이터를 운영 URL로 공개하지 않습니다.

`python -m pytest tests/test_mobile_p1.py`로 계약 검증. 가락한상오더 고객 앱에서도 설정을 수동으로 승인하기 전에는 모든 네트워크 연결을 차단합니다.

## v1.6 추가 규약

- `GET /api/v1/mobile/merchants?market_id=garak`: 서버 검증된 시장 ID에 속한 **데모 상품 목록에서 유도한 상호명**만 반환. 실제 사업자 인증과 별개.
- `GET /api/v1/mobile/products?market_id=garak&merchant_name=...`: UTF-8 URL 인코딩된 매장명 정확 일치 필터. 타 시장/상인 목록 혼입을 제한합니다.
- ID는 V5 `repo.catalog`의 기존 제한적 조회 결과를 사용하고 별도 DB 스키마와 권한을 추가하지 않습니다.
- API 응답에는 `orderable:false`/`checkout_enabled:false` 유지. 앱의 오프라인 장바구니에 서버 상품을 넣지 않습니다.

개발 서버에 배포 전 API 게이트·허용 호스트·TLS·운영 DB 스코프·실제 Neon 연결을 별도로 검증하십시오.

## v1.7 P1C 추가: 인증 세션 검증

`GET /api/v1/mobile/auth/session`은 Bearer 토큰이 반드시 있어야 하고, 기존 V5 `backend.auth_v5.verify_oidc()`를 통해 검증합니다. 익명·형식 오류·서명 실패는 401이며 원문 토큰/PII를 반환하지 않습니다. 메서드는 GET 전용입니다.

**주의:** Neon Auth의 새로운 OAuth 2.1 access token을 구형 V5 EdDSA JWT로 가정하지 마십시오. 별도 테스트 브랜치에서 서명 알고리즘·issuer·audience·resource 및 서버 라이브러리 호환성을 확인해야 합니다. 현재 모바일 Google 로그인을 활성화하지 않습니다.
