# Neon / Vercel 데이터 정본 충돌 리포트 (2026-10-30)

- Vercel `garakhs` 배포 alias `garak.lexid.site`, Ready, 참조 커밋 `0ebeb50a...`; GitHub 최신 확인 `4552fdc...`.
- Vercel Production에 `DATABASE_URL`, `NEON_AUTH_BASE_URL`, `NEON_AUTH_COOKIE_SECRET` 키 존재. **실제 값 미열람**. 특정 Neon 프로젝트와 자동 연결되었다고 주장할 수 없음.
- Neon `garakhansang` 프로젝트 ID `mute-darkness-67529424`의 읽기 전용 검사에서 `products=0, orders=5, categories=0, content_documents=0, settlements=0`.
- Neon `garakland` 프로젝트 ID `ancient-grass-26115554`는 **별개**이며 상점, 상품, 캠페인, 지갑 등 다른 스키마 구조.
- `garakhansang.public.products.price_usd`는 numeric USD, `orders.total_usd` 및 `amount_krw` 혼합 구조, `settlements`는 `revenue_usd` 기반. 로컬 SQLite 모형의 `products.price`/`orders.subtotal`/`settlements.gross`는 KRW 정수.
- **보호 규칙:** 공개 데이터에 임의 환율 곱하기 금지, 통화 혼합 금지, Neon 테이블 DROP/ALTER/UPDATE 금지, 기존 `products/orders` 덮어쓰기 금지. `garak_ops` 별도 확장을 사전 검토.
- 실제 Vercel DB를 확인한 후에도 데이터 운영 승인이 없으면 마이그레이션은 스테이징 전용. 라이브 데이터 연결 검증은 인증된 담당자가 비밀값 노출 없이 수행해야 함.
