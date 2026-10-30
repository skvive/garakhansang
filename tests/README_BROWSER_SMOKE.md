# 추가 브라우저 시연 (선택 사항)

`python tests/v9_browser_smoke.py`는 Chromium·Playwright를 설치한 **개발자 PC**에서만 사용합니다.

- `pip install playwright` 와 Chromium/Chrome 설치가 필요합니다. 기본 프로그램 실행 및 API 테스트에는 이 라이브러리가 필요하지 않습니다.
- 브라우저 실행 정책이 로컬 URL (`127.0.0.1`, `file://`)을 차단하는 환경에서는 자동화 테스트가 실패할 수 있습니다. 이때 성공으로 기록하지 마세요.
- 모든 요청은 임시 SQLite 데모 DB에만 보내며 운영 사이트·실결제 시스템을 호출하지 않습니다.
- 브라우저 시연은 Windows/PC에서 다시 수행해야 하며 이 패키지의 필수 자동 테스트 합격을 대체하지 않습니다.
