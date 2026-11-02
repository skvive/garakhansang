# 가락한상 오더 V4 · 실제 Neon 개발 DB 검증 영수증

- **2026-11-02 KST**
- Neon 조직 `shinkangteam`, 프로젝트 `garakhansang`(`dawn-paper-21288363`)
- 검증 브랜치 `dev-garak-hansang-order-20261102`(`br-winter-flower-b5tvau07`), DB `neondb`
- 운영 `main` 브랜치와 운영 사이트에는 접근 변경·DDL·발송·배포 없음.

## 적용
- `001_neon_order_schema_DRAFT.sql`의 14개 기존 테이블이 개발 브랜치에 적용되어 있었음.
- V4 `002_demo_checkout.sql` 18개 구문 적용, `gho.actor_grants` 테이블 및 실제 PG 주문 생성·취소 함수 신설.
- `003_pilot_demo_seed.sql` 34개 INSERT/UPSERT 실행.
- DB 확인: 시장 5개, 시연 상품 17개. 상점 12개는 seed 정의 기준.

## 실제 SQL 실행 결과

1. 주문 장바구니: 가락시장 `g1×2 + g2×1`, 노량진 `n1×1(손질)` → **시장별 2건 주문 생성**. 총액 가락 **55,200원**(상품 49,700원+배송 5,500원), 노량진 **39,100원**(손질 포함 상품 32,900원+배송 6,200원). **실결제 없음**.
2. 상품 DB 재고: `g1:30→28`, `g2:30→29`, `n1:30→29` 확인.
3. 같은 주체+멱등키+장바구니 재요청 → 최초 checkout ID와 2개 order ID 그대로 재전송, 주문 2건 유지.
4. 두 주문을 `gho.cancel_demo_order` 실행 → 상태 `cancelled`, 재고 `g1:30`, `g2:30`, `n1:30`으로 복원.
5. 별도 거절 테스트: 같은 멱등키로 다른 장바구니, 보유 수량보다 많은 주문, 다른 사용자 주체의 취소, 중복 취소 모두 실패 응답 확인.
6. 첫 DB 실행 시 SQL의 `stock-q.qty` 오기 발견, `stock-q.q`로 수정 후 함수 재정의. 최종 소스 파일은 수정본임.

**제한**: Python psycopg 드라이버가 실행 컨테이너에 없어 Python FastAPI→원격 Neon 실제 네트워크 통합 E2E는 수행하지 못함. 함수와 SQL은 Neon 도구를 통해 PostgreSQL에서 직접 실행해 검증함. OIDC 실제 신원 공급자·웹훅·PG·실배송 미연결. JWT 인증은 별도 테스트에서 로컬 RSA 키로 검증했으며 실제 Neon Auth OAuth issuer/JWKS 설정은 미연결.
