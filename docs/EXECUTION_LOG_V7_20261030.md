# V7 실행 기록 (2026-10-30)

| 실행 순번 | 수행 결과 | 실검증 근거 |
|---|---|---|
| 1 | v6 ZIP 추출·원본 코드·기존 운영 게이트 확인 | 기존 `README_먼저읽기.md`, `docs/BETA_TEST_REPORT.md` |
| 2 | 기존 자동 테스트를 독립 환경에서 재실행, 통과 | `QA_EVIDENCE/v6_baseline_tests.log` |
| 3 | GitHub main vs Vercel 커밋 차이 확인 | `docs/MASTER_RESCUE_PLAN_V7_20261030.md` |
| 4 | Neon `garakhansang`/`garakland` 테이블·집계(읽기 전용) 조사 | `docs/NEON_SCHEMA_READONLY_AUDIT_20261030.md` |
| 5 | 중복 SKU 합산, 조건부 재고 차감·에러 개선 | `admin_core/server.py`, `tests/test_v7_regressions.py` |
| 6 | 비밀번호 변경 후 세션 무효화, 상인 공개·배송 전환 보호 | 같은 파일, 회귀 테스트 |
| 7 | SQLite 백업·검증·안전복원·훼손 거부 | `tools/db_snapshot.py`, `tests/test_v7_backup.py` |
| 8 | KRW 강제·결제 견적 불일치 방어 로직 | `integrations/currency_contract.mjs`, `tests/currency_contract.test.mjs` |
| 9 | Python 57건, Node 3건 테스트 통과 | `QA_EVIDENCE/v7_all_tests.log`, `QA_EVIDENCE/v7_currency_tests.log` |
| 10 | 동시주문 50건, HTTP 공개 API 조회 100건 | `docs/QA_CONCURRENCY.json` 및 로그 |
| 11 | HTML 218개 링크·JS·인코딩 및 이미지 132개 검사 통과 | `docs/QA_STATIC_RELEASE.json`, `QA_EVIDENCE/v7_static_qa.log` |
| 12 | 패키지에서 최초 비밀번호와 실DB 파일 제외, 전체 ZIP 무결성 검사 | 패키징 결과 |

**비실행/제한:** 실제 사용자/상인·PG 계정, Vercel 운영 배포, Neon 데이터 조작, GitHub main 코드 수정, 전체 Next.js 빌드, 모든 217페이지 실브라우저 육안 재검수는 이번 패키지에 포함되지 않음.
