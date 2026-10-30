# 가락한상 통합 운영센터 V6 — 실행 안내

**기준 디자인:** 사용자가 선택한 2번 '가락시장 스토리형' · 수산 중심, 축산·농산 확장 쇼핑몰.
**패키지 성격:** 기능을 실제 실행·수정·테스트할 수 있는 **로컬 베타 운영센터** + v5 쇼핑몰 정적 시연본 + Next.js 통합 패치 자료.
**배포 상태:** **GitHub `skvive/garak`, Vercel `garakhs`, 운영 도메인 `garak.lexid.site`는 이 패키지 제작 과정에서 수정하지 않았습니다.**

## 1분 실행 (Windows)
1. 압축을 풉니다. 작업 위치에 공백/한글이 있어도 가능합니다.
2. Python 3.11 이상 설치 후 `start_admin_windows.bat`을 실행합니다. 별도 pip 설치 불필요.
3. 브라우저에서 `http://127.0.0.1:8099/admin/`을 엽니다.
4. 처음 실행할 때 **`runtime/FIRST_LOGIN_LOCAL_ONLY.txt`**에 생성된 랜덤 비밀번호로 `admin` 계정에 로그인합니다.
5. 비밀번호를 안전하게 변경하고 이 최초 로그인 파일을 삭제합니다. 관리자는 비밀번호 변경 API(`/api/auth/password`)를 제공합니다.
6. `http://127.0.0.1:8099/`에서 기존 쇼핑몰 화면을 엽니다. 본 시연본은 **실결제가 불가**합니다.

Linux/macOS: `sh start_admin_mac_linux.sh`. 테스트: `python -m unittest discover -s tests -p 'test_*.py' -v`.

## 운영센터 메뉴
- **홈·통계:** KPIs, 주문금액/상태, 카테고리별 매출, 광고 조회/클릭/전환, 페이지 이벤트, CSV 다운로드.
- **판매:** 상품 가격/노출, 신규 상품(초안), 재고 조정과 감사 이력, 테스트 주문/상태전환, 운송장/배송, 점포 승인, 정산 생성.
- **콘텐츠:** 레시피 132개 검수/공개, 신규 레시피(초안), 요리사/블로거, 상인/유통업체/협회 게시물 승인, 광고 캠페인.
- **고객·운영:** 문의, 고객 목록(샘플), 관리자 계정 생성 및 역할 제어, API 연동 상태, 감사 로그.
- **상점 연결:** 217개 쇼핑몰 HTML 화면에 같은 출처의 `commerce-bridge-v6.js` 추가. 관리자 상품가격/재고/공개 상태 및 승인 콘텐츠를 로컬 API에서 읽습니다.

## 실제로 작동하는 동작
- 인증 세션(서버 해시 저장, `HttpOnly; SameSite=Strict`), CSRF 검증, 역할별 접근, 로그인 제한, 감사 로그.
- SQLite WAL/트랜잭션으로 동시 주문·재고 예약. 재고 부족 주문 거부, 취소 시 재고 복귀, 중복 정산 방지.
- 승인되지 않은 상인·홍보 게시글·레시피를 공개 API에서 노출하지 않음.
- 44개 상품/132개 레시피를 이전 v5 예시 원장으로 임포트. 기존 사진은 AI 연출 시안이며 실상품 사진으로 인증된 것이 아님.
- 실제 DB를 기반으로 계산한 **베타 통계**, CSV 내보내기, 상품 상태에 따라 화면을 변경하는 공개 API.

## 아직 연결되지 않은 실제 운영 요소
- `garak.lexid.site` 도메인/운영 Neon DB에는 쓰기 작업을 하지 않았습니다.
- Toss 실결제/결제 취소/환불, 실배송 송장, 은행 송금, 세금계산서, 사업자 신원 확인은 실행되지 않습니다.
- Google Blogger/YouTube OAuth, 쿠팡 WING, 쿠팡이츠, 배민 API/제휴 계약은 **연동 가이드와 관리 상태만 제공**합니다.
- 로컬 SQLite는 Neon 운영 스키마를 대체하지 않습니다. DB 양방향 동기화와 SSO, 전자상거래 실매출 정산은 추가 개발이 필요합니다.
- Python stdlib HTTP 서버는 **공개 인터넷 서비스로 배포하면 안 됩니다**. 기본 주소 `127.0.0.1`의 로컬 베타에만 사용하세요.

## 파일 구조
```
admin_core/database.py    SQLite 스키마, 랜덤 초기 계정, 초기 콘텐츠 44+132
admin_core/server.py      관리자 인증, 권한, CRUD, 주문·재고·배송·정산, 공개 API, 통계
storefront/               v5 쇼핑몰 217개 HTML + admin/index.html + 연결 스크립트
integrations/             Next.js 운영센터 연결 페이지, 안전 적용 스크립트, Neon 설계 SQL
integrations/story_v5_patch/  기존 Next.js 상품·레시피·시장스토리 통합 패치
specs/ 또는 docs/        백엔드 설계·ERD·테스트·위험/운영 점검
runtime/                  첫 실행 시 로컬 DB 생성; 배포 ZIP에는 **미포함**
tests/                    API, 브라우저, 정적 검사 스크립트
```

## GitHub 원본에 이식할 때
1. `git clone https://github.com/skvive/garak.git` 또는 로컬에 이미 있는 실제 Git 저장소를 사용합니다.
2. 원본 백업 및 **전용 신규 브랜치**를 생성합니다. 반드시 기존 `garakhs` 운영 커밋과 HEAD 차이를 비교하세요.
3. 기존 v5 기능과 테마 적용이 필요하면 `python integrations/story_v5_patch/apply_story_v5.py <garak 경로>`를 별도 테스트 복제본에 실행합니다. 원본이 이미 반영된 경우 중복 적용하지 마세요.
4. 관리센터 진입 경로는 `python integrations/apply_ops_next_overlay.py <garak 경로>`로 생성할 수 있습니다. **이 스크립트는 실제 DB 통합이 아니라 운영센터 연결 페이지 생성**입니다.
5. `lexistyle`에서 `npm ci`, `npm run build`, Vercel PREVIEW 배포와 결제 SANDBOX 테스트 후 운영 배포 여부를 결정합니다.
6. Neon 스키마 적용 전 `integrations/neon_postgres_operations_schema.sql`과 실제 `src/db/schema`를 대조하세요. SQL은 절대 자동 실행되지 않습니다.

## 테스트 결과
- API 자동 테스트 46건 통과.
- PC·모바일 각 16개, 관리자 화면 32개 레이아웃 검사. 상품 가격 수정·주문·베타 통계 동작 확인.
- 218개 HTML, 내부 링크 누락 0, WebP 형식 오류 0, JS 문법 오류 0, 한국어 대체문자 오류 0.
- 브라우저 샌드박스가 localhost URL 직접 접속을 제한해, **HTML/CSS/JS를 브라우저에 주입하고 별도 실행되는 진짜 HTTP 백엔드에 호출을 전달하는 방식**으로 UI 테스트했습니다. 실제 배포 E2E는 아님.

자세한 판정과 추가 운영 검수 작업: `docs/BETA_TEST_REPORT.md`, `docs/PRODUCTION_RELEASE_GATES.md`.

---
## V7 (2026-10-30) 추가사항
- 새 마스터 보고서 `docs/MASTER_RESCUE_PLAN_V7_20261030.md`를 먼저 읽으세요. 실판매 출시 판정은 **NO-GO**입니다.
- v7 안전 개선: 주문 중복 상품 합산·원자적 재고 차감·세션 일괄 폐기·미인증 상인 상품 공개 제한·배송 전환 검사.
- 로컬 베타 DB만을 위한 안전 백업: `python tools/db_snapshot.py snapshot runtime/garak_beta.sqlite3 ./my_backup.sqlite3`; 검증: `python tools/db_snapshot.py verify ./my_backup.sqlite3`; 별도 복원: `python tools/db_snapshot.py restore ./my_backup.sqlite3 ./recovered.sqlite3`.
- 통화·금액 검증 모듈 `integrations/currency_contract.mjs`: USD 값을 KRW인 것처럼 넘기면 거부. 실제 PG API 호출은 제공하지 않습니다.
- 테스트: `python -m unittest discover -s tests -p 'test_*.py' -v`; `node --test tests/currency_contract.test.mjs`; `python tests/release_audit.py`; `python tests/concurrency_beta.py`.
- 주의: ZIP 내 코드는 운영 GitHub 전체 clone이 아니고, 운영 Vercel/Neon에 배포·연동하지 않았습니다. API와 시연 상품은 로컬 테스트 전용입니다.
