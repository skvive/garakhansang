# 가락한상 V8 — 고객 검수용 로컬 베타 패키지

이 패키지는 **2번 가락시장 스토리형** 디자인의 쇼핑몰 시연 사이트, Python·SQLite 관리자 백엔드, 주문·재고·콘텐츠·권한·통계 API, 실제 로컬 HTTP/브라우저 검수 도구와 증빙을 포함합니다.

**첫 문서:** `docs/QA_V8_CUSTOMER_HANDOFF_REPORT.md`.

## Windows 실행

1. Python 3.11 이상 설치.
2. `start_admin_windows.bat` 실행.
3. `http://127.0.0.1:8099/admin/` 접속.
4. 처음 실행시 생성된 `runtime/FIRST_LOGIN_LOCAL_ONLY.txt`의 로그인 정보를 사용하고, 바로 비밀번호 변경 후 파일을 삭제.
5. `http://127.0.0.1:8099/`에서 쇼핑몰 시연본 확인. **모의 주문만 실행 가능**.

## 테스트

- Windows 기본 테스트: `run_v8_qa_windows.bat`
- 전체 Python: `python -m unittest discover -s tests -p "test_*.py" -v`
- 연속 모의 업무 흐름: `python tests/v8_full_business_flow.py`
- 브라우저 추가 테스트: Playwright·Chromium이 설치된 환경에서 `python tests/e2e_browser_injected.py`, `python tests/e2e_storefront_v8.py`

## 원본/프로덕션 변경 없음

기존 운영 GitHub `skvive/garak`, Vercel `garakhs`, `garak.lexid.site`와 Neon DB를 **이번 테스트 과정에서 수정하지 않았습니다**. `integrations/` 폴더의 Next.js 스키마/패치는 참고 및 별도 통합 검증용이며, 완료된 Next.js 빌드가 아닙니다. 실제 식품 판매, 결제, 송금, 외부 상점 API가 연결된 소프트웨어라고 표시하면 안 됩니다.

**상태:** LOCAL BETA QA PASS / REAL COMMERCE NO-GO.
