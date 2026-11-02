# V3 검증 보고

- 환경: Linux/Python 3, loopback-only HTTP 서버, Chromium 렌더링 모의 브리지, Neon 개발 브랜치 (별도)
- 엔진 단위 테스트: 14/14 PASS (시장별 주문 분리, 서버 재고·가격, 취소 복구, 쿠폰, 집하·배차 순서 등)
- HTTP API 검사: 10/10 PASS (기존 8 + 고객 주문토큰 소유 검증 + 외부 Origin 방어)
- Chromium UI 검사: 13/13 PASS, JS 페이지 오류 0, 390px 및 1280px 가로 넘침 0
- Neon 개발 DB 마이그레이션: 33 statements succeeded, 14 tables, 민감 테이블 13개 RLS 활성 (markets 테이블은 공개 참조정보)
- 미검증: 실제 PostgreSQL 주문 쓰기, Neon Auth, 실결제/환불, SMS·푸시, Android APK 실기기, 운영 배포, 실제 상인 계약과 재고 연동
- 주의: Chromium 검사는 인라인 DOM + Python 도메인 브리지이며 브라우저→HTTP 실제 통합 E2E는 아님. HTTP API는 독립 urllib으로 검증.
