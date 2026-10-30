# 가락한상 V8 — 실제 실행·실패 재현·교정·재검증 보고서

- 기준: 2026-10-30 (로컬 검수)
- 구성: 가락시장 쇼핑몰(수산·축산·농산) 정적 시연본 + 레시피 132종 + 관리자 Python/SQLite 로컬 서버
- 디자인: 선택된 **2번 가락시장 스토리형** 유지
- **검수 판정: LOCAL BETA QA PASS (테스트된 기능 범위). 실거래/운영 배포 GO 판정 아님.**

## 1. 실검증 환경과 근거

| 대상 | 실행 방법 | 실제로 검증한 범위 |
|---|---|---|
| 백엔드 | `python -m admin_core.server` + 독립 임시 SQLite DB | 로그인, API, 권한, 재고, 주문, 배송, 정산, 게시물, 레시피, 보고서 |
| 테스트 | `python -m unittest discover -s tests -p 'test_*.py'` | HTTP 정상·오류/보안/백업 시나리오 |
| 관리자 UI | Playwright Chromium + 실제 HTTP API 브리지 | PC 1440px, 모바일 390px, 관리자 16개 모듈×2 화면 및 가격수정/주문/보고서 |
| 쇼핑몰 UI | Playwright Chromium 정적 DOM 시뮬레이션 | 비공개/품절/재고초과 차단 및 상품 상태 갱신·장바구니 재계산 |
| 기능 연결 | 별도 HTTP 전과정 시연 | 상인 승인→상품 등록/공개→재고→모의 주문→출고→모의 정산→콘텐츠 승인→통계 |
| 부하 | ThreadingHTTPServer + SQLite WAL | 50개 동시 주문, 공개 조회 100건 |
| 콘텐츠·자산 | 로컬 전체 정적 검사 | 쇼핑몰 217 + 관리자 1 HTML, 이미지와 내부 링크, 문법·UTF-8 |

**주의:** Playwright는 샌드박스 정책으로 `localhost`의 실제 URL 탐색이 막혀 페이지 HTML/JS를 주입하고 HTTP 요청을 실행 중인 서버에 전달했습니다. 일반 웹 배포·DNS·브라우저 보안 정책·실제 PG 접속을 통과한 E2E 결과는 아닙니다.

## 2. 실패 재현 → 교정 → 재시험 기록

| ID | 원본 v7 실패 재현 | V8 개선 | 검수 증거 |
|---|---|---|---|
| F-01 | 재고 `delta=1.9`를 전달하면 `int()` 변환으로 재고 1 증가 | 소수·문자열·bool 재고 값 거절 | `QA_V8_EVIDENCE/api_69.log`; `test_v8_fixes.py` |
| F-02 | 상인 정지 뒤 상품이 계속 공개되고 신규 주문도 수락됨 | 정지/승인거절 시 해당 상품 자동 비공개, 공개 목록·주문 단계에서 중복 차단, 재활성화 시 자동 재공개 금지 | `test_v8_fixes.py` 03~06 |
| F-03 | 사용자 변경 감사 로그에 PBKDF2 비밀번호 해시가 기록됨 | 감사 로그에서 비밀번호·토큰·CSRF·연락처 등 민감 항목 마스킹 | `test_v8_fixes.py` 07~08·11 |
| F-04 | SQLite `with connect()` 사용 뒤 닫히지 않은 연결 경고 | 컨텍스트 종료시 커밋/롤백 후 연결 종료 | Python 69건 재검증, ResourceWarning 미검출 |
| F-05 | 숨김/품절 상품을 시연 장바구니에 계속 담을 수 있음 | 공개 상태·수량 유효성 검사, 품절/수량 초과 거부 | `QA_V8_CART.json` 10건 |
| F-06 | 관리자 데이터가 갱신돼도 장바구니 합계가 옛값으로 남음 | `garak:catalog-updated` 이벤트로 카트 재렌더, 구매 불가 상품은 소계 제외 | PC·모바일 Chromium 브라우저 10건 |
| F-07 | 서비스 워커의 캐시가 오래된 JS를 오프라인에서 다시 제공할 수 있음 | 캐시 네임스페이스를 `garak-public-v8`로 변경 | `node --check`, 정적 218개 검사 |

**수정 전 F-01~F-03의 실제 응답:** `../FAILURE_REPRO_BEFORE.txt`(패키지 내 `QA_V8_EVIDENCE/FAILURE_REPRO_BEFORE.txt`) 참조. 수정 후에는 별도의 신규 임시 DB에서 수행했으며 운영 DB는 수정하지 않았습니다.

## 3. 자동 테스트 결과

| Suite | 기대 결과 | 확인 항목 |
|---|---|---|
| API/보안 | **69/69 PASS** | 기존 57건 + 신규 12건, 정상·권한 차단·재고/주문/정산·백업 복원 |
| 통화 | **3/3 PASS** | USD/KRW 정수와 예상 결제 금액 계약 |
| 연속 업무 흐름 | **50/50 PASS** | 독립 임시 DB+실제 HTTP로 핵심 모듈 순차 검증 |
| 관리자 화면 | **32/32 PASS** | PC·모바일 각 16개 모듈, 레이아웃 넘침/JS 오류 0 |
| 쇼핑몰 장바구니 | **10/10 PASS** | PC·모바일의 숨김/품절/수량초과/재고변경 정책 |
| 동시성 | **PASS** | 50건 중 20건만 예약(재고 20), 나머지 30건 거부, 재고 0 |
| 공개 API | **100 조회 PASS** | 단일 머신 p95 수치는 `concurrency_50.log` 참고, 서비스 수준 약속 아님 |
| 정적 파일 | **218/218 PASS** | 쇼핑몰 217 + 관리자 1, 깨진 링크/JS/UTF-8 오류 0 |

테스트 종류가 중복될 수 있으므로 위 수치를 모두 합산해 **서로 다른 기능 264개가 검증됐다고 해석해서는 안 됩니다.** 각각 별도 검수 게이트입니다.

## 4. 프로그램 모듈별 결과

| 모듈 | HTTP 기능 | UI/동작 | 운영 시스템 연결 |
|---|---|---|---|
| 관리자 로그인·권한 | PASS (로컬 해시 세션) | PASS | Neon Auth/SSO 미완료 |
| 상품·가격 | PASS (테스트 상품) | PASS | 실상품 DB 정본 연결 미완료 |
| 재고·입출고 | PASS | PASS | 외부 판매채널 재고 미연결 |
| 장바구니 | PASS (정적 시연) | PASS | 실주문 전환 미완료 |
| 모의 주문·취소 | PASS | PASS | Toss 실결제/환불 미연결 |
| 출고·배송 | PASS (상태 머신) | PASS | 실송장/물류사 미연결 |
| 정산 | PASS (모의 계산·멱등) | PASS | 은행 이체·세무 미연결 |
| 상인·사업자 승인 | PASS (로컬 수동 상태) | PASS | 실제 사업자 신원 미검증 |
| 레시피 132개 | PASS (등록·검수/공개) | PASS | 사진·조리 전문 검수 미완료 |
| 게시판/광고/요리사 | PASS (승인·검수 상태) | PASS | Blogger/YouTube OAuth 미연결 |
| 통계·고객·문의 | PASS (로컬 샘플) | PASS | 운영 매출/PII 정책 미완료 |
| 연동 상태 | PASS (허위 연결 상태 차단) | PASS | 쿠팡·배민·이츠 외부 API 미완료 |

## 5. 로컬 고객 검수 판정

**로컬 기능 테스트 범위는 통과**했습니다. 정상 업무와 대표적인 실패 사례를 실제 HTTP/브라우저에서 검증했고, 재현된 결함을 수정했습니다. 다만 **전체 218개 페이지를 1장씩 사람 눈으로 심층 검수한 것이 아니며**, 자동 링크/문법 검사와 핵심 모듈 화면 검수만 통과한 것입니다. 상품 사진은 예시이며, 132장 이미지가 각각 해당 레시피의 정확한 완성 요리 사진이라는 증빙은 없습니다.

**상용 출시 판정은 `NO-GO`**입니다. 실제 `skvive/garak` Next.js 전체 저장소 빌드, `garak.lexid.site` 프리뷰/프로덕션 배포, Neon의 운영 DB 연결 검증, 실결제·부분 환불·배송·정산·OAuth 승인·실상품 확인은 이번 로컬 패키지에 포함되지 않았습니다.

## 6. 재검수 및 배포 경계

1. Windows: `start_admin_windows.bat` 실행. 새 랜덤 초기 비밀번호는 `runtime/FIRST_LOGIN_LOCAL_ONLY.txt`에서 확인하고 변경/삭제.
2. 로컬 API: `python -m unittest discover -s tests -p "test_*.py" -v`.
3. `python tests/v8_full_business_flow.py` — **실행 중인 외부 서버가 아닌 별도 임시 로컬 서버와 DB 사용**.
4. `python tests/release_audit.py`, `python tests/concurrency_beta.py`.
5. Node.js 설치시 `node --test tests/currency_contract.test.mjs`.
6. Linux 검수 이미지 재생성: Chromium·Playwright 준비 후 `python tests/e2e_browser_injected.py` 및 `python tests/e2e_storefront_v8.py`.
7. 실데이터/실결제는 실행하지 마세요. 운영 이식 전에 `docs/PRODUCTION_RELEASE_GATES.md`의 P0 전항목을 승인받아야 합니다.
