# 가락한상 — Cursor 원팩 V9 (선택 디자인 2번, 시장 스토리형)

**이 ZIP은 이번 대화에서 만든 전체 로컬 프로그램 소스의 단일 패키지입니다.** 쇼핑몰 시연 웹사이트, 관리자 백엔드, 데이터 샘플, 132개 레시피와 로컬 WebP 연출 이미지, 2번 브랜드 디자인, GitHub Next.js 이식용 패치를 포함합니다. 예전 패키지들을 각각 설치할 필요가 없습니다.

> **중요한 범위:** 현재 파일은 `skvive/garak` 저장소의 약 3,800개 전체 원본 코드 복사본이 아닙니다. 외부 GitHub 다운로드를 이 환경에서 완료하지 못하므로 Next.js 기존 원본은 별도로 clone해야 합니다. 이 패키지 자체의 쇼핑몰+운영센터 **로컬 베타는 바로 실행**되지만 운영 `garak.lexid.site` 완제품/배포본이나 결제 연결 소프트웨어는 아닙니다.

## Cursor 1분 실행 — Windows

1. ZIP 전체 압축 해제 → `GARAK_HANSANG_CURSOR.code-workspace`를 Cursor로 엽니다.
2. **Python 3.11 이상** 설치되어 있는지 확인합니다. 로컬 서버는 Python 표준 라이브러리만 사용하며 추가 `pip install`이 필요하지 않습니다.
3. 폴더 최상위 **`INSTALL_AND_RUN_WINDOWS.bat`** 실행. 또는 Cursor 명령 팔레트 → `Tasks: Run Task` → `가락한상: 로컬 쇼핑몰 + 관리자 실행`.
4. 쇼핑몰: `http://127.0.0.1:8099/` · 관리자: `http://127.0.0.1:8099/admin/`
5. 첫 실행 후 `runtime/FIRST_LOGIN_LOCAL_ONLY.txt`의 임시 비밀번호로 `admin` 로그인. 로그인 후 즉시 비밀번호 변경하고 해당 파일 삭제.
6. 검수: `VERIFY_ALL_WINDOWS.bat` 또는 Cursor `가락한상: 전체 검수` 작업. 세부 결과 `QA_V9_RESULTS/`.

Python/Node 확인: `python tools/onepack.py doctor`. **Node.js 22+**는 금액 검증 스크립트를 포함한 *전체* 자동 테스트 실행에 필요하지만 로컬 서비스 실행에 필요하지 않습니다.

macOS/Linux: `./start_mac_linux.sh`; 별도 실행은 `python3 tools/onepack.py run`.

## 디렉터리 — 중복 설치·포트 충돌 방지

| 경로 | 용도 |
|---|---|
| `storefront/` | 시장 스토리형 쇼핑몰, 217개 정적 페이지(상품·레시피·상인·쿠팡/배민 안내) + 관리자 UI 1개 |
| `admin_core/` | Python·SQLite, 계정·권한·재고·모의주문·배송·정산·콘텐츠·통계 REST API |
| `tests/` | API/보안/통화/재고/브라우저/기능 테스트 |
| `tools/` | 단일 실행/진단/테스트, 안전한 GitHub 이식 스크립트, SQLite 로컬 백업 |
| `integrations/` | 실제 `skvive/garak` Next.js 원본에 적용할 레시피/디자인/관리자 패치와 DB 설계 SQL (자동 배포 없음) |
| `design_reference/` | 사용자가 선택한 2번 시장 스토리형 홈페이지 이미지 |
| `docs/` 및 `QA_*_EVIDENCE/` | 이전 로컬 검수 및 설계 문서 |
| `runtime/` | **처음 실행 때 새로 생성**되는 사용자 전용 테스트 DB와 최초 로그인 정보 (ZIP 미포함) |

`start_admin_windows.bat`, `run_v8_qa_windows.bat`는 버전 이력 호환용입니다. **상위 폴더의 V9 실행 파일만** 사용하세요. 여러 서버를 동시에 시작하면 동일한 포트(8099)를 점유하므로 재실행이 차단됩니다.

## 기존 GitHub 저장소로 통합하는 순서

먼저 로컬 베타를 확인하고, 새 기능이 실제 Next.js 원본에 충돌 없이 적용되는지를 **별도로** 검증합니다. 원본 저장소를 이 ZIP이 임의로 수정하지 않습니다.

```powershell
git clone https://github.com/skvive/garak.git
git -C garak switch -c feature/garak-onepack-v9
python tools/merge_into_github.py garak --dry-run
python tools/merge_into_github.py garak --apply
cd garak/lexistyle
npm ci
npm run build
```

`--dry-run`은 임시 소스에 전체 패치를 먼저 실행하고 기존 코드와 파일 차이를 보여 줍니다. `--apply`는 **변경사항 없는 전용 feature 브랜치에서만** 허용하고 기존 파일은 `.git/garak_onepack_backups/`에 백업합니다. 대상 구조가 바뀌었거나 동일 파일의 내용이 충돌하면 중단하며, 운영 DB나 실결제 시스템은 건드리지 않습니다. `npm run build`는 해당 환경에서 실제 수행해야 하며, 이 ZIP 제작 환경에서는 GitHub 전체 clone이 불가능해 통과했다고 주장하지 않습니다.

## 테스트/출시 판정

- 로컬 베타 서버 인증·데모 상품/API·관리자·재고·환불 아닌 **모의 취소**·배송·정산 통계 테스트를 자동화했습니다.
- V9에는 Cursor 실행 및 패키지 자체 검사, 안전한 Git 이식 드라이런·실행·중복 적용 검사, 오류 복원 테스트를 추가했습니다.
- **실판매 NO-GO:** Google OAuth·YouTube·쿠팡·배민 실제 API, Neon 운영 DB 완전 동기화, Toss 실결제/환불/송금, 실배송, 개인정보·상인 서류 검증, 실사용자 E2E, 원본 Next.js 전체 빌드/배포가 아직 검증되지 않았습니다.
- 132개의 요리별 WebP는 **연출 시안**이며, 메뉴별 독립 AI 완성 사진 132개로 검증된 결과가 아닙니다. 실상품 이미지와 임의 시세·후기를 영업용으로 사용하면 안 됩니다.
- 운영 DB 스키마와 로컬 DB는 통화 필드가 다릅니다. SQL 자동 적용이나 운영 데이터 가져오기는 의도적으로 금지했습니다.

세부 증빙과 남은 작업: `docs/V9_INTEGRATION_AND_QA_REPORT.md`, `docs/PRODUCTION_RELEASE_GATES.md`.
